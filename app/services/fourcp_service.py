"""
ERCOT 4CP risk scoring service for LEAP.

Bridges the FourCPEngine (pure business logic) with LEAP's local
load and weather data. Provides:
  - Historical 4CP date lookup
  - Daily risk scoring for upcoming summer days
  - Summer season risk timeline
"""

import csv
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .fourcp.engine import FourCPEngine, RuleConfig, build_daily_table

logger = logging.getLogger(__name__)

# Historical 4CP dates shipped with the app
_DATES_CSV = Path(__file__).parent / "fourcp" / "4CP_dates.csv"


def _load_historical_dates() -> pd.DataFrame:
    """Load historical 4CP dates CSV."""
    return pd.read_csv(_DATES_CSV)


def _dates_to_set(cp_df: pd.DataFrame) -> set:
    """Convert 4CP dates DataFrame to set of (year, month, day) tuples."""
    from datetime import datetime as dt
    out = set()
    for _, row in cp_df.iterrows():
        y = row.get("Year")
        if pd.isna(y):
            continue
        year = int(y)
        for col in ["June", "July", "August", "September"]:
            val = str(row.get(col, "")).strip()
            if not val or val == "nan":
                continue
            try:
                parsed = dt.strptime(val, "%m/%d/%Y %H:%M")
                out.add((year, parsed.month, parsed.day))
            except ValueError:
                continue
    return out


class FourCPService:
    """Service for 4CP risk scoring, backed by LEAP database."""

    def __init__(self, leap_db_service):
        self.db = leap_db_service
        self.offline_mode = leap_db_service.offline_mode
        self.catalog = leap_db_service.catalog
        self.historical_dates_df = _load_historical_dates()
        self.historical_dates_set = _dates_to_set(self.historical_dates_df)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_historical_dates(self) -> List[Dict[str, Any]]:
        """Return all historical 4CP dates as a list of records."""
        rows = []
        for _, row in self.historical_dates_df.iterrows():
            year = int(row["Year"])
            for month_name in ["June", "July", "August", "September"]:
                val = str(row.get(month_name, "")).strip()
                if not val or val == "nan":
                    continue
                rows.append({
                    "year": year,
                    "month": month_name,
                    "datetime": val,
                })
        return rows

    def score_day(self, target_date: str) -> Dict[str, Any]:
        """Score a single day for 4CP risk.

        Args:
            target_date: Date string YYYY-MM-DD.

        Returns:
            Dict with risk score, decision, peak prediction, and reasoning.
        """
        daily_df = self._build_daily_dataframe()
        if daily_df is None or daily_df.empty:
            return self._mock_score(target_date)

        engine = FourCPEngine(daily_df, config=RuleConfig(
            min_gap_days=2,
            exceed_margin_mw=0.0,
            heat_temp_max_c=30.8,
            heat_apparent_max_c=35.0,
        ))

        # Get weather for target date
        weather_row = self._get_weather_for_date(target_date)
        if weather_row is None:
            return self._mock_score(target_date)

        result = engine.score_day(target_date, weather_row)
        return result

    def score_summer_range(self, year: int) -> List[Dict[str, Any]]:
        """Score all weekdays in the summer season (Jun 1 – Sep 30) for a year.

        Args:
            year: Year to score.

        Returns:
            List of daily risk scores.
        """
        daily_df = self._build_daily_dataframe()
        if daily_df is None or daily_df.empty:
            return self._mock_summer_scores(year)

        engine = FourCPEngine(daily_df, config=RuleConfig())
        results = []

        for month in [6, 7, 8, 9]:
            days_in_month = {6: 30, 7: 31, 8: 31, 9: 30}[month]
            for day in range(1, days_in_month + 1):
                try:
                    d = datetime(year, month, day)
                except ValueError:
                    continue
                date_str = d.strftime("%Y-%m-%d")
                weather_row = self._get_weather_for_date(date_str)
                if weather_row is None:
                    # Use seasonal defaults
                    weather_row = {
                        "temp_max_c": 35.0 + np.random.normal(0, 3),
                        "temp_min_c": 24.0 + np.random.normal(0, 2),
                        "apparent_max_c": 38.0 + np.random.normal(0, 3),
                        "precip_mm": max(0, np.random.exponential(2)),
                    }
                result = engine.score_day(date_str, weather_row)
                result["is_historical_4cp"] = (year, month, day) in self.historical_dates_set
                results.append(result)

        return results

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of 4CP analysis capability."""
        years = sorted(self.historical_dates_df["Year"].dropna().astype(int).tolist())
        return {
            "description": "ERCOT Four Coincident Peak (4CP) risk scoring",
            "years_covered": f"{min(years)}-{max(years)}",
            "total_historical_events": len(self.historical_dates_set),
            "peak_months": ["June", "July", "August", "September"],
            "typical_peak_hour": "16:00-17:00 CDT",
            "business_context": (
                "Transmission costs are allocated based on load during the 4 highest "
                "system-wide demand hours each summer. Predicting these peaks enables "
                "demand response to reduce transmission charges."
            ),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_daily_dataframe(self) -> Optional[pd.DataFrame]:
        """Build the daily table the engine needs from LEAP data."""
        if self.offline_mode:
            return None

        try:
            # Pull hourly load for TEX-ALL (ERCOT)
            load_data = self.db.get_load_data("TEX-ALL", limit=90 * 24)
            if not load_data:
                return None

            load_df = pd.DataFrame(load_data)
            load_df["ts_utc"] = pd.to_datetime(load_df["ts_utc"])
            load_df = load_df.rename(columns={"ts_utc": "timestamp", "mw": "ERCOT"})
            load_df["4CP_event"] = 0
            # Mark historical 4CP days
            for y, m, d in self.historical_dates_set:
                mask = (
                    (load_df["timestamp"].dt.year == y)
                    & (load_df["timestamp"].dt.month == m)
                    & (load_df["timestamp"].dt.day == d)
                )
                load_df.loc[mask, "4CP_event"] = 1

            # Pull weather for TEX-ALL
            weather_data = self.db.get_weather_data("TEX-ALL", limit=90 * 24)
            if not weather_data:
                return None

            weather_df = pd.DataFrame(weather_data)
            weather_df["ts_utc"] = pd.to_datetime(weather_df["ts_utc"])
            weather_df["date"] = weather_df["ts_utc"].dt.floor("D")

            # Aggregate to daily weather
            daily_weather = weather_df.groupby("date", as_index=False).agg(
                temp_max_c=("temperature", "max"),
                temp_min_c=("temperature", "min"),
                apparent_max_c=("temperature", "max"),  # approx
                precip_mm=("relative_humidity", lambda x: 0),  # placeholder
            )
            # Convert °F to °C for the engine
            daily_weather["temp_max_c"] = (daily_weather["temp_max_c"] - 32) * 5 / 9
            daily_weather["temp_min_c"] = (daily_weather["temp_min_c"] - 32) * 5 / 9
            daily_weather["apparent_max_c"] = (daily_weather["apparent_max_c"] - 32) * 5 / 9
            daily_weather["precip_mm"] = 0.0  # not available from Open-Meteo hourly

            daily = build_daily_table(load_df, daily_weather)
            return daily

        except Exception as e:
            logger.error(f"Failed to build daily DataFrame for 4CP: {e}")
            return None

    def _get_weather_for_date(self, date_str: str) -> Optional[Dict[str, float]]:
        """Get daily weather summary for a specific date."""
        try:
            weather_data = self.db.get_weather_data(
                "TEX-ALL",
                start_date=date_str,
                end_date=date_str,
                limit=24
            )
            if not weather_data:
                return None

            temps = [float(w.get("temperature", 70)) for w in weather_data if w.get("temperature")]
            winds = [float(w.get("windSpeed", 0)) for w in weather_data if w.get("windSpeed")]

            if not temps:
                return None

            temp_max_f = max(temps)
            temp_min_f = min(temps)

            return {
                "temp_max_c": (temp_max_f - 32) * 5 / 9,
                "temp_min_c": (temp_min_f - 32) * 5 / 9,
                "apparent_max_c": (temp_max_f - 32) * 5 / 9 + 2,  # heat index approx
                "precip_mm": 0.0,
            }
        except Exception as e:
            logger.error(f"Failed to get weather for {date_str}: {e}")
            return None

    def _mock_score(self, target_date: str) -> Dict[str, Any]:
        """Generate a mock 4CP risk score for offline mode."""
        dt = pd.to_datetime(target_date)
        is_summer = dt.month in (6, 7, 8, 9)
        is_weekday = dt.dayofweek < 5
        base_risk = 0.0

        if is_summer and is_weekday:
            # Higher risk in July/August peak
            month_weight = {6: 0.3, 7: 0.5, 8: 0.45, 9: 0.25}.get(dt.month, 0)
            # Afternoon hours more likely
            base_risk = month_weight + np.random.uniform(-0.15, 0.15)
            base_risk = float(np.clip(base_risk, 0.0, 1.0))

        return {
            "date": target_date,
            "risk": round(base_risk, 3),
            "decision": base_risk >= 0.65,
            "peak_pred_mw": round(45000 + np.random.normal(0, 5000), 0),
            "season_threshold_mw": 42000,
            "events_used": np.random.randint(0, 4),
            "days_since_last_4cp": np.random.randint(5, 30),
            "reasons": "demo scoring from bundled 4CP history and synthetic weather",
        }

    def _mock_summer_scores(self, year: int) -> List[Dict[str, Any]]:
        """Generate mock summer risk timeline."""
        results = []
        for month in [6, 7, 8, 9]:
            days = {6: 30, 7: 31, 8: 31, 9: 30}[month]
            for day in range(1, days + 1):
                try:
                    d = datetime(year, month, day)
                except ValueError:
                    continue
                result = self._mock_score(d.strftime("%Y-%m-%d"))
                result["is_historical_4cp"] = (year, month, day) in self.historical_dates_set
                results.append(result)
        return results
