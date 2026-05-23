"""Outage data processing: resample, window, and slot duration."""

import pandas as pd


def resample_outages(df: pd.DataFrame, freq: str = "15min") -> pd.DataFrame:
    """Resample outage records to a regular time grid and forward-fill."""
    keys = [c for c in ["utility_name", "county_fips"] if c in df.columns]
    df = df.sort_values("timestamp")
    indexed = df.set_index("timestamp")
    if keys:
        out = (
            indexed.groupby(keys, group_keys=False)
            .apply(lambda g: g.resample(freq).ffill())
            .reset_index()
        )
    else:
        out = indexed.resample(freq).ffill().reset_index()
        return out


def window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Slice a DataFrame to the inclusive time window [start, end]."""
    ts = pd.to_datetime(df["timestamp"], utc=True)
    start_utc = pd.to_datetime(start, utc=True)
    end_utc = pd.to_datetime(end, utc=True)
    mask = (ts >= start_utc) & (ts <= end_utc)
    return df.loc[mask].copy()


def with_duration_minutes(df: pd.DataFrame) -> pd.DataFrame:
    """Attach a `slot_minutes` column representing per-row duration."""
    keys = [c for c in ["utility_name", "county_fips"] if c in df.columns]
    sort_cols = keys + ["timestamp"]
    df = df.sort_values(sort_cols).copy()
    if keys:
        dt = df.groupby(keys)["timestamp"].diff().dt.total_seconds().div(60).fillna(15)
    else:
        dt = df["timestamp"].diff().dt.total_seconds().div(60).fillna(15)
    df["slot_minutes"] = dt.clip(lower=1, upper=60)
    return df
