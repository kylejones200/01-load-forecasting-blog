"""EIA reliability benchmarks: optional local parquet or scrape national table."""

import os
import io
from pathlib import Path

import pandas as pd
import requests

EIA_TABLE_URL = "https://www.eia.gov/electricity/annual/html/epa_11_01.html"

# Optional: set EIA_BENCHMARKS_PATH to a parquet file (e.g. /path/to/ELEC.parquet) to use it instead of scraping
EIA_BENCHMARKS_PATH_ENV = "EIA_BENCHMARKS_PATH"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip column names."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def load_eia_from_parquet(path: str | Path) -> pd.DataFrame:
    """Load EIA-style benchmark table from a local parquet file."""
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"EIA parquet not found: {path}")
    df = pd.read_parquet(path)
    return _normalize_columns(df)


def scrape_eia_table() -> pd.DataFrame:
    """Scrape the EIA national reliability table into a DataFrame.
    May fail if the page structure changes or network/SSL issues.
    """
    r = requests.get(EIA_TABLE_URL, timeout=60)
    r.raise_for_status()
    html = r.text
    tables = pd.read_html(io.StringIO(html))
    if not tables:
        raise ValueError("No tables found at EIA URL")
    # Find a table that looks like the metrics (has year and saidi/saifi-like columns)
    for t in tables:
        cols_lower = [str(c).lower() for c in t.columns]
    if "year" in cols_lower or any("saidi" in c for c in cols_lower):
        return _normalize_columns(t)
    # Fallback: first table
    return _normalize_columns(tables[0])


def get_eia_benchmarks() -> pd.DataFrame:
    """Load EIA benchmarks: from local parquet if EIA_BENCHMARKS_PATH is set and exists, else scrape."""
    path = os.environ.get(EIA_BENCHMARKS_PATH_ENV, "").strip()
    if path:
        p = Path(path).expanduser().resolve()
    if p.exists():
        return load_eia_from_parquet(p)
    return scrape_eia_table()
