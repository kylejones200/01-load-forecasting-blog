"""
Data ingestion: Open-Meteo weather (historical + forecast).
Other sources (EIA, Census, OSM) are handled by setup scripts, not the app runtime.
"""

import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

# BA locations for weather queries
BA_LOCATIONS = [
    ("CAL-ALL", 38.58, -121.49),
    ("TEX-ALL", 32.78, -96.80),
    ("PJM-ALL", 39.95, -75.17),
    ("MISO-ALL", 41.88, -87.63),
    ("NYIS-ALL", 40.71, -74.01),
    ("ISNE-ALL", 42.36, -71.06),
    ("SWPP-ALL", 39.10, -94.58),
]


def fetch_open_meteo_historical(ba: str, lat: float, lon: float,
                                 start_date: str, end_date: str) -> List[Dict]:
    """Fetch historical hourly weather from Open-Meteo Archive API."""
    resp = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "timezone": "UTC",
    }, timeout=120)
    resp.raise_for_status()
    hourly = resp.json().get("hourly", {})
    times = hourly.get("time", [])
    return [
        {"ba": ba, "lat": lat, "lon": lon, "ts_utc": times[i],
         "temperature": hourly.get("temperature_2m", [None] * len(times))[i],
         "relative_humidity": hourly.get("relative_humidity_2m", [None] * len(times))[i],
         "wind_speed_mph": hourly.get("wind_speed_10m", [None] * len(times))[i],
         "weather_code": hourly.get("weather_code", [None] * len(times))[i]}
        for i in range(len(times))
    ]


def fetch_open_meteo_forecast(ba: str, lat: float, lon: float,
                               forecast_days: int = 7) -> List[Dict]:
    """Fetch hourly weather forecast from Open-Meteo Forecast API."""
    resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "timezone": "UTC",
        "forecast_days": forecast_days,
    }, timeout=60)
    resp.raise_for_status()
    hourly = resp.json().get("hourly", {})
    times = hourly.get("time", [])
    return [
        {"ba": ba, "lat": lat, "lon": lon, "ts_utc": times[i],
         "temperature": hourly.get("temperature_2m", [None] * len(times))[i],
         "relative_humidity": hourly.get("relative_humidity_2m", [None] * len(times))[i],
         "wind_speed_mph": hourly.get("wind_speed_10m", [None] * len(times))[i],
         "weather_code": hourly.get("weather_code", [None] * len(times))[i]}
        for i in range(len(times))
    ]
