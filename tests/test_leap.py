"""LEAP API and service tests."""

from __future__ import annotations

import pytest
from app import create_app
from app.services.data_ingestion import BA_LOCATIONS
from app.services.forecast_service import ForecastService
from app.services.leap_db import LEAPDatabaseService


@pytest.fixture
def app():
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_leap_scenarios_endpoint(client):
    response = client.get("/api/leap/scenarios/CAL-ALL?horizon=24")
    assert response.status_code == 200
    assert isinstance(response.get_json()["scenarios"], dict)


def test_leap_metrics_endpoint(client):
    response = client.get("/api/leap/metrics/CAL-ALL")
    assert response.status_code == 200
    assert len(response.get_json()["metrics"]) > 0


def test_weather_endpoint(client):
    response = client.get("/api/leap/weather?ba=CAL-ALL&limit=24")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0


def test_forecast_service_trend_or_pattern(app):
    with app.app_context():
        db = LEAPDatabaseService(app)
        service = ForecastService(db)
        forecast = service.generate_forecast("TEX-ALL", 12, "lightgbm", "baseline")
    assert len(forecast) == 12
    assert forecast[0]["ba"] == "TEX-ALL"


def test_ba_locations_cover_configured_bas(app):
    with app.app_context():
        db = LEAPDatabaseService(app)
        offline_bas = {row["ba"] for row in db.get_balancing_authorities()}
    configured = {ba for ba, _lat, _lon in BA_LOCATIONS}
    assert offline_bas == configured
