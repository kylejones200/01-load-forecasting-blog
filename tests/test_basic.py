"""Smoke tests for the LEAP Flask application."""

from __future__ import annotations

import pytest
from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config.update({"TESTING": True})
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_api_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "data_dir" in data


def test_leap_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"LEAP" in response.data


def test_leap_areas_endpoint(client):
    response = client.get("/api/leap/areas")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0


def test_leap_load_endpoint(client):
    response = client.get("/api/leap/load/CAL-ALL?limit=48")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] > 0


def test_leap_forecast_endpoint(client):
    response = client.get("/api/leap/forecast/CAL-ALL?horizon=24")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["forecast"]) == 24
