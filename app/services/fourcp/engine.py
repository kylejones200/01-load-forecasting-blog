"""
4CP engine: build daily table from load+weather DataFrames, fit peak model, score a day.
Pure business logic; no file I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RuleConfig:
    season_months: Tuple[int, ...] = (6, 7, 8, 9)
    max_events_per_year: int = 4
    min_gap_days: int = 2
    exceed_margin_mw: float = 0.0
    heat_temp_max_c: float = 30.8
    heat_apparent_max_c: float = 35.0


def build_daily_table(ercot_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """Build daily-aggregated table from hourly load and daily weather DataFrames."""
    ercot = ercot_df.copy()
    ercot["timestamp"] = pd.to_datetime(ercot["timestamp"])
    ercot["date"] = ercot["timestamp"].dt.floor("D")
    daily_load = (
        ercot.groupby("date", as_index=False)
        .agg(
            load_peak=("ERCOT", "max"),
            load_mean=("ERCOT", "mean"),
            is_4cp=("4CP_event", "max"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    daily_load["is_4cp"] = daily_load["is_4cp"].astype(bool)
    w = weather_df.copy()
    w["date"] = pd.to_datetime(w["date"])
    w = w.drop(columns=["is_4cp"], errors="ignore")
    daily = daily_load.merge(w, on="date", how="inner").sort_values("date").reset_index(drop=True)
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month
    daily["dow"] = daily["date"].dt.dayofweek
    daily["is_weekday"] = daily["dow"] < 5
    return daily


class FourCPEngine:
    """
    Operational 4CP day scorer. Uses daily DataFrame (load + weather); no I/O.
    """

    def __init__(self, daily: pd.DataFrame, config: RuleConfig = RuleConfig()) -> None:
        self.cfg = config
        self.daily = daily
        self.model = self._fit_peak_from_weather_model(self.daily)

    @staticmethod
    def _fit_peak_from_weather_model(daily: pd.DataFrame) -> Dict[str, Any]:
        df = daily.copy()
        df = df.dropna(subset=["load_peak", "temp_max_c", "temp_min_c", "apparent_max_c", "precip_mm"])
        df = df[(df["load_peak"] > 0) & (df["load_peak"] < 5_000_000)]
        X = np.column_stack(
            [
                np.ones(len(df)),
                df["temp_max_c"].to_numpy(),
                df["temp_min_c"].to_numpy(),
                df["apparent_max_c"].to_numpy(),
                df["precip_mm"].to_numpy(),
            ]
        )
        y = df["load_peak"].to_numpy()
        lam = 50.0
        XtX = X.T @ X
        I = np.eye(XtX.shape[0])
        b = np.linalg.solve(XtX + lam * I, X.T @ y)
        yhat = X @ b
        sigma = float(np.std(y - yhat))
        return {"coef": b, "sigma": sigma, "features": ["1", "temp_max_c", "temp_min_c", "apparent_max_c", "precip_mm"]}

    def _predict_peak_from_weather(self, weather_row: Dict[str, float]) -> float:
        b = self.model["coef"]
        X = np.array([
            1.0,
            float(weather_row["temp_max_c"]),
            float(weather_row["temp_min_c"]),
            float(weather_row["apparent_max_c"]),
            float(weather_row.get("precip_mm", 0.0)),
        ])
        return float(X @ b)

    def _season_threshold(self, year: int, up_to_date: pd.Timestamp) -> Optional[float]:
        s = self.daily[
            (self.daily["year"] == year)
            & (self.daily["month"].isin(self.cfg.season_months))
            & (self.daily["date"] < up_to_date)
        ].copy()
        s = s[(s["load_peak"] > 0) & (s["load_peak"] < 5_000_000)]
        if s.empty:
            return None
        peaks = np.sort(s["load_peak"].to_numpy())[::-1]
        if len(peaks) < self.cfg.max_events_per_year:
            return None
        return float(peaks[self.cfg.max_events_per_year - 1])

    def _events_so_far(self, year: int, up_to_date: pd.Timestamp) -> int:
        s = self.daily[(self.daily["year"] == year) & (self.daily["date"] < up_to_date)]
        return int(s["is_4cp"].sum())

    def _days_since_last_event(self, year: int, up_to_date: pd.Timestamp) -> Optional[int]:
        s = self.daily[(self.daily["year"] == year) & (self.daily["date"] < up_to_date) & (self.daily["is_4cp"])]
        if s.empty:
            return None
        return int((up_to_date - s["date"].max()).days)

    def score_day(
        self,
        target_date: str | pd.Timestamp,
        weather_row: Dict[str, float],
        known_actual_peak_mw: Optional[float] = None,
    ) -> Dict[str, Any]:
        dt = pd.to_datetime(target_date).floor("D")
        year = int(dt.year)
        is_weekday = int(dt.dayofweek) < 5
        events_used = self._events_so_far(year, dt)
        if events_used >= self.cfg.max_events_per_year:
            return {"date": dt.date().isoformat(), "risk": 0.0, "decision": False, "reasons": "year quota reached"}
        gap = self._days_since_last_event(year, dt)
        if gap is not None and gap < self.cfg.min_gap_days:
            return {"date": dt.date().isoformat(), "risk": 0.01, "decision": False, "reasons": f"gap {gap}d below min_gap_days"}
        if not is_weekday:
            return {"date": dt.date().isoformat(), "risk": 0.0, "decision": False, "reasons": "weekend"}
        peak_pred = float(known_actual_peak_mw) if known_actual_peak_mw is not None else self._predict_peak_from_weather(weather_row)
        thr = self._season_threshold(year, dt)
        heat_ok = (float(weather_row["temp_max_c"]) >= self.cfg.heat_temp_max_c) or (
            float(weather_row["apparent_max_c"]) >= self.cfg.heat_apparent_max_c
        )
        if thr is None:
            base = 0.35 + (0.25 if heat_ok else -0.10) + (0.10 if (gap is not None and gap >= 10) else 0.0)
            risk = float(np.clip(base, 0.0, 1.0))
            return {
                "date": dt.date().isoformat(),
                "risk": risk,
                "decision": risk >= 0.6,
                "peak_pred_mw": peak_pred,
                "season_threshold_mw": None,
                "events_used": events_used,
                "days_since_last_4cp": gap,
                "reasons": "early season threshold unavailable",
            }
        exceed = peak_pred - thr
        exceed_ok = exceed >= self.cfg.exceed_margin_mw
        risk = 0.05 + (0.70 if exceed_ok else 0.0) + (0.20 if heat_ok else -0.05)
        if gap is not None:
            risk += 0.08 if gap >= 7 else -0.08
        if events_used == 0:
            risk += 0.05
        if events_used == 3:
            risk += 0.05
        risk = float(np.clip(risk, 0.0, 1.0))
        reasons = ["weekday", f"events_used={events_used}", f"peak_pred-thr={exceed:.0f} MW", "heat_ok" if heat_ok else "heat_low"]
        if gap is not None:
            reasons.append(f"gap={gap}d")
        return {
            "date": dt.date().isoformat(),
            "risk": risk,
            "decision": risk >= 0.65,
            "peak_pred_mw": peak_pred,
            "season_threshold_mw": thr,
            "events_used": events_used,
            "days_since_last_4cp": gap,
            "reasons": ", ".join(reasons),
        }
