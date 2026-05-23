"""LEAP data access — local synthetic and parquet-backed series."""

from __future__ import annotations

import logging
from typing import Any

from . import local_data

logger = logging.getLogger(__name__)


class LEAPDatabaseService:
    """Query service for hourly load, weather, and derived features."""

    def __init__(self, app):
        self.app = app

    def get_balancing_authorities(self) -> list[dict[str, Any]]:
        return local_data.list_balancing_authorities()

    def get_load_data(
        self,
        ba: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return local_data.query_load(ba, start_date, end_date, limit)

    def get_weather_data(
        self,
        ba: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return local_data.query_weather(ba, start_date, end_date, limit)

    def get_features(self, ba: str, limit: int = 1000) -> list[dict[str, Any]]:
        return local_data.build_features(ba, limit)

    def get_forecast_data(
        self,
        ba: str,
        horizon_hours: int = 24,
        scenario_id: str = "baseline",
    ) -> list[dict[str, Any]]:
        return []

    def get_model_metrics(self, ba: str, model_name: str = "lightgbm") -> list[dict[str, Any]]:
        return [
            {
                "ba": ba,
                "model_name": model_name,
                "metric_name": "mape",
                "metric_value": 2.8,
                "evaluation_date": "demo",
            },
            {
                "ba": ba,
                "model_name": model_name,
                "metric_name": "mae_mw",
                "metric_value": 450.0,
                "evaluation_date": "demo",
            },
        ]

    def get_outage_correlation(
        self,
        ba: str | None = None,
        severity: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        return []

    def get_outage_correlation_summary(self) -> dict[str, Any]:
        return {"by_cause": [], "by_severity": [], "by_ba": []}

    def get_outage_correlation_timeline(self, ba: str, limit: int = 1000) -> list[dict[str, Any]]:
        return []
