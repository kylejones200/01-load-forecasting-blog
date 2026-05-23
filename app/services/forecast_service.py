"""Forecast service: pattern and trend extrapolation from local load history."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

BA_BASELINES: dict[str, tuple[float, float]] = {
    "TEX-ALL": (45000, 12000),
    "CAL-ALL": (28000, 8000),
    "PJM-ALL": (85000, 20000),
    "MISO-ALL": (65000, 15000),
    "NYIS-ALL": (18000, 5000),
    "ISNE-ALL": (14000, 4000),
    "SWPP-ALL": (25000, 7000),
}

SCENARIO_ADJUSTMENTS: dict[str, Any] = {
    "baseline": lambda mw, hour: mw,
    "high_growth": lambda mw, hour: mw * 1.05,
    "hot_weather": lambda mw, hour: mw * 1.15 if 12 <= hour <= 18 else mw,
    "demand_response": lambda mw, hour: mw * 0.90 if 16 <= hour <= 20 else mw,
}


class ForecastService:
    """Generate load forecasts for balancing authorities."""

    def __init__(self, db_service):
        self.db = db_service

    def generate_forecast(
        self,
        ba: str,
        horizon_hours: int = 24,
        model_type: str = "lightgbm",
        scenario_id: str = "baseline",
    ) -> list[dict[str, Any]]:
        """Generate a multi-hour forecast from recent load or a seasonal pattern."""
        del model_type  # reserved for future on-disk model artifacts
        result = self._trend_forecast(ba, horizon_hours)
        if result:
            return self._apply_scenario(result, scenario_id)
        return self._pattern_forecast(ba, horizon_hours, scenario_id)

    def _trend_forecast(self, ba: str, horizon_hours: int) -> list[dict[str, Any]] | None:
        """Extrapolate from recent local load data."""
        try:
            load_data = self.db.get_load_data(ba, limit=48)
            if len(load_data) < 2:
                return None

            values = [float(row["mw"]) for row in reversed(load_data) if row.get("mw")]
            if len(values) < 2:
                return None

            last = values[-1]
            trend = np.polyfit(range(len(values)), values, 1)[0]
            base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            results: list[dict[str, Any]] = []

            for i in range(horizon_hours):
                ft = base_time + timedelta(hours=i + 1)
                seasonal = 1 + 0.15 * np.sin(2 * np.pi * ft.hour / 24)
                yhat = max(0, (last + trend * (i + 1)) * seasonal)
                results.append(
                    self._format_point(ba, ft, yhat, "trend", "baseline", horizon_hours)
                )
            return results
        except Exception:
            return None

    def _pattern_forecast(
        self, ba: str, horizon_hours: int, scenario_id: str
    ) -> list[dict[str, Any]]:
        """Seasonal pattern forecast from BA baselines."""
        avg, std = BA_BASELINES.get(ba, (15000, 5000))
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        adjust = SCENARIO_ADJUSTMENTS.get(scenario_id, SCENARIO_ADJUSTMENTS["baseline"])
        results: list[dict[str, Any]] = []

        for i in range(horizon_hours):
            ft = base_time + timedelta(hours=i + 1)
            daily_shape = 1 - 0.25 * ((ft.hour - 16) / 12) ** 2
            weekend = 0.88 if ft.weekday() >= 5 else 1.0
            base = avg * daily_shape * weekend
            base = adjust(base, ft.hour)
            noise = np.random.normal(0, std * 0.03)
            results.append(
                self._format_point(ba, ft, base + noise, "pattern", scenario_id, horizon_hours)
            )
        return results

    def _apply_scenario(
        self, results: list[dict[str, Any]], scenario_id: str
    ) -> list[dict[str, Any]]:
        if scenario_id == "baseline":
            return results
        adjust = SCENARIO_ADJUSTMENTS.get(scenario_id)
        if not adjust:
            return results
        for row in results:
            ft = datetime.fromisoformat(row["ts_utc"])
            row["mw_forecast"] = round(adjust(row["mw_forecast"], ft.hour), 2)
            row["scenario_id"] = scenario_id
        return results

    @staticmethod
    def _format_point(ba, ts, mw, model_name, scenario_id, horizon_hours):
        return {
            "ba": ba,
            "ts_utc": ts.isoformat(),
            "horizon_hours": horizon_hours,
            "mw_forecast": round(float(mw), 2),
            "model_name": model_name,
            "model_version": "1.0",
            "scenario_id": scenario_id,
            "created_at": datetime.now().isoformat(),
        }
