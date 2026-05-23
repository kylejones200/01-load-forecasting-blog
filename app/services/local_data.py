"""Local in-process and parquet-backed data for LEAP demos."""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("LEAP_DATA_DIR", "data/cache"))
LOAD_CACHE_FILE = DATA_DIR / "load_hourly.parquet"
WEATHER_CACHE_FILE = DATA_DIR / "weather_hourly.parquet"
SYNTHETIC_DAYS = 90
RANDOM_SEED = 42

BA_PROFILES: list[tuple[str, str, str, float, float, int, float]] = [
    ("CAL-ALL", "CISO", "California ISO", 28000, 8000, 16, 1.20),
    ("TEX-ALL", "ERCO", "ERCOT", 45000, 12000, 16, 1.35),
    ("PJM-ALL", "PJM", "PJM Interconnection", 85000, 20000, 15, 1.15),
    ("MISO-ALL", "MISO", "Midcontinent ISO", 65000, 15000, 15, 1.20),
    ("NYIS-ALL", "NYIS", "New York ISO", 18000, 5000, 15, 1.15),
    ("ISNE-ALL", "ISNE", "ISO New England", 14000, 4000, 15, 1.10),
    ("SWPP-ALL", "SWPP", "Southwest Power Pool", 25000, 7000, 16, 1.25),
]

_load_frames: dict[str, pd.DataFrame] = {}


def list_balancing_authorities() -> list[dict[str, str]]:
    """Return static BA metadata for the demo."""
    return [
        {"ba": code, "name": name, "region": _region_for(code)}
        for code, _eia, name, *_rest in BA_PROFILES
    ]


def _region_for(ba: str) -> str:
    regions = {
        "CAL-ALL": "WECC",
        "TEX-ALL": "ERCOT",
        "PJM-ALL": "RFC",
        "MISO-ALL": "MRO",
        "NYIS-ALL": "NPCC",
        "ISNE-ALL": "NPCC",
        "SWPP-ALL": "MRO",
    }
    return regions.get(ba, "US")


def generate_load_series(
    ba_code: str,
    avg_mw: float,
    std_mw: float,
    peak_hour: int,
    summer_factor: float,
    days: int,
) -> list[dict[str, Any]]:
    """Generate realistic hourly load rows for one balancing authority."""
    rng = random.Random(hash((RANDOM_SEED, ba_code)))
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)
    rows: list[dict[str, Any]] = []

    for day_offset in range(days):
        dt = start + timedelta(days=day_offset)
        dow = dt.weekday()
        month = dt.month
        is_weekend = dow >= 5
        seasonal = (
            summer_factor
            if month in (6, 7, 8)
            else 1.05
            if month in (12, 1, 2)
            else 0.90
        )

        for hour in range(24):
            ts = dt + timedelta(hours=hour)
            hour_offset = (hour - peak_hour) / 12.0
            daily_shape = 1.0 - 0.25 * (hour_offset**2)
            weekend_factor = 0.88 if is_weekend else 1.0
            morning_ramp = 0.05 * (hour - 5) if 6 <= hour <= 9 else 0.0
            noise = rng.gauss(0, 0.03)
            mw = avg_mw * daily_shape * seasonal * weekend_factor * (
                1 + morning_ramp * 0.02 + noise
            )
            mw = max(mw * 0.5, mw)
            rows.append({"ba": ba_code, "ts_utc": ts.isoformat(), "mw": round(mw, 1)})

    return rows


def _load_frame_from_parquet() -> pd.DataFrame | None:
    if not LOAD_CACHE_FILE.is_file():
        return None
    try:
        frame = pd.read_parquet(LOAD_CACHE_FILE)
        if "ts_utc" in frame.columns:
            frame["ts_utc"] = pd.to_datetime(frame["ts_utc"], utc=True)
        return frame
    except Exception as exc:
        logger.warning("Could not read %s: %s", LOAD_CACHE_FILE, exc)
        return None


def _synthetic_frame(ba: str) -> pd.DataFrame:
    profile = next((p for p in BA_PROFILES if p[0] == ba), None)
    if profile is None:
        return pd.DataFrame(columns=["ba", "ts_utc", "mw"])
    _code, _eia, _name, avg_mw, std_mw, peak_hour, summer_factor = profile
    rows = generate_load_series(ba, avg_mw, std_mw, peak_hour, summer_factor, SYNTHETIC_DAYS)
    frame = pd.DataFrame(rows)
    frame["ts_utc"] = pd.to_datetime(frame["ts_utc"], utc=True)
    return frame.sort_values("ts_utc")


def get_load_frame(ba: str) -> pd.DataFrame:
    """Cached hourly load for a BA (parquet if present, else synthetic)."""
    if ba in _load_frames:
        return _load_frames[ba]

    combined = _load_frame_from_parquet()
    if combined is not None and not combined.empty and "ba" in combined.columns:
        subset = combined.loc[combined["ba"] == ba].copy()
        if not subset.empty:
            _load_frames[ba] = subset.sort_values("ts_utc")
            return _load_frames[ba]

    _load_frames[ba] = _synthetic_frame(ba)
    return _load_frames[ba]


def persist_synthetic_cache() -> Path:
    """Write all BA synthetic load series to data/cache/load_hourly.parquet."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frames = [_synthetic_frame(profile[0]) for profile in BA_PROFILES]
    combined = pd.concat(frames, ignore_index=True)
    combined.to_parquet(LOAD_CACHE_FILE, index=False)
    logger.info("Wrote %s rows to %s", len(combined), LOAD_CACHE_FILE)
    _load_frames.clear()
    return LOAD_CACHE_FILE


def query_load(
    ba: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Return load records newest-first."""
    frame = get_load_frame(ba)
    if frame.empty:
        return []

    filtered = frame
    if start_date:
        filtered = filtered.loc[filtered["ts_utc"] >= pd.Timestamp(start_date, tz="UTC")]
    if end_date:
        filtered = filtered.loc[filtered["ts_utc"] <= pd.Timestamp(end_date, tz="UTC")]

    filtered = filtered.sort_values("ts_utc", ascending=False).head(limit)
    return [
        {"ba": ba, "ts_utc": row.ts_utc.isoformat(), "mw": float(row.mw)}
        for row in filtered.itertuples(index=False)
    ]


def query_weather(
    ba: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Return synthetic weather aligned to load timestamps when no cache exists."""
    if WEATHER_CACHE_FILE.is_file():
        try:
            frame = pd.read_parquet(WEATHER_CACHE_FILE)
            frame = frame.loc[frame["ba"] == ba]
            if not frame.empty:
                if start_date:
                    frame = frame.loc[frame["ts_utc"] >= pd.Timestamp(start_date, tz="UTC")]
                if end_date:
                    frame = frame.loc[frame["ts_utc"] <= pd.Timestamp(end_date, tz="UTC")]
                frame = frame.sort_values("ts_utc", ascending=False).head(limit)
                return frame.to_dict(orient="records")
        except Exception as exc:
            logger.warning("Weather cache read failed: %s", exc)

    load_rows = query_load(ba, start_date, end_date, limit)
    weather: list[dict[str, Any]] = []
    for row in load_rows:
        hour = pd.Timestamp(row["ts_utc"]).hour
        temp = 72 + 12 * ((hour - 14) / 12) ** 2
        weather.append(
            {
                "ba": ba,
                "ts_utc": row["ts_utc"],
                "temperature": round(temp, 1),
                "wind_speed_mph": 8.0,
                "shortForecast": "Partly cloudy",
            }
        )
    return weather


def build_features(ba: str, limit: int = 1000) -> list[dict[str, Any]]:
    """Engineered features from local load series."""
    frame = get_load_frame(ba).sort_values("ts_utc").tail(limit + 48)
    if frame.empty:
        return []

    frame = frame.copy()
    frame["mw_lag1"] = frame["mw"].shift(1)
    frame["mw_lag24"] = frame["mw"].shift(24)
    frame["mw_ma24"] = frame["mw"].rolling(24, min_periods=1).mean()
    frame["hour"] = frame["ts_utc"].dt.hour
    frame["dow"] = frame["ts_utc"].dt.dayofweek
    frame["month"] = frame["ts_utc"].dt.month
    frame["is_holiday"] = 0
    frame["temperature"] = 75.0
    frame["wind_speed_mph"] = 8.0
    frame = frame.dropna()
    return frame.sort_values("ts_utc", ascending=False).head(limit).to_dict(orient="records")
