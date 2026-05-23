#!/usr/bin/env python3
"""Build normalized EIA ELEC samples for the Medium article (~10 MB bundle)."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

DEFAULT_SOURCE = Path("data/ELEC.parquet")
DEFAULT_OUTPUT = Path("data/samples/ELEC_article_sample.parquet")
RAW_EXCERPT_NAME = "ELEC_bulk_excerpt.parquet"
BUNDLE_NAME = "article_data_bundle.zip"
TARGET_BYTES = 10 * 1024 * 1024
PRIORITY_STATES = ("TX", "CA", "PA", "NY", "IL", "FL", "GA", "NC", "OH", "MN")

SERIES_ID_FUEL = re.compile(
    r"ELEC\.(?:PLANT\.)?(?:GEN|CONS|PROD)[^.]*\.([A-Z0-9]+)-",
    re.IGNORECASE,
)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_series_records(source: Path) -> list[dict]:
    """Parse JSON blobs stored one-per-row in the bulk ELEC parquet export."""
    frame = pd.read_parquet(source)
    column = frame.columns[0]
    records: list[dict] = []
    for raw in frame[column].astype(str):
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    logger.info("Parsed %s series from %s", len(records), source)
    return records


def infer_fuel(series_id: str, name: str) -> str:
    match = SERIES_ID_FUEL.search(series_id)
    if match:
        return match.group(1)
    lowered = name.lower()
    for token in ("natural gas", "wind", "solar", "nuclear", "coal", "hydro"):
        if token in lowered:
            return token.split()[0][:3].upper()
    return "UNK"


def infer_state(iso3166: str) -> str:
    if not iso3166 or "-" not in iso3166:
        return ""
    return iso3166.split("-", 1)[-1]


def series_priority(rec: dict) -> int:
    state = infer_state(str(rec.get("iso3166", "")))
    if state in PRIORITY_STATES:
        return 0
    if rec.get("lat") and rec.get("lon"):
        return 1
    return 2


def flatten_records(records: list[dict], *, max_series: int | None) -> pd.DataFrame:
    """Long-format readings with series metadata on each row."""
    ordered = sorted(records, key=series_priority)
    if max_series is not None:
        ordered = ordered[:max_series]

    rows: list[dict] = []
    for rec in ordered:
        series_id = rec.get("series_id", "")
        base = {
            "series_id": series_id,
            "series_name": rec.get("name", ""),
            "units": rec.get("units", ""),
            "frequency": rec.get("f", ""),
            "state": infer_state(str(rec.get("iso3166", ""))),
            "lat": _to_float(rec.get("lat")),
            "lon": _to_float(rec.get("lon")),
            "fuel_code": infer_fuel(series_id, str(rec.get("name", ""))),
            "series_start": rec.get("start", ""),
            "series_end": rec.get("end", ""),
        }
        for period, value in rec.get("data") or []:
            rows.append({**base, "period": str(period), "value": _to_float(value)})

    return pd.DataFrame(rows)


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def write_parquet(frame: pd.DataFrame, output: Path, compression: str) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, output, compression=compression)
    return output.stat().st_size


def write_readme(
    output_dir: Path,
    frame: pd.DataFrame,
    source: Path,
    normalized_path: Path,
    normalized_bytes: int,
    raw_path: Path | None,
    bundle_path: Path | None,
) -> None:
    readme = output_dir / "README.md"
    n_series = frame["series_id"].nunique()
    period_min = frame["period"].min() if len(frame) else ""
    period_max = frame["period"].max() if len(frame) else ""
    raw_line = (
        f"| Raw excerpt | `{raw_path.name}` ({raw_path.stat().st_size / (1024 * 1024):.1f} MB) |\n"
        if raw_path and raw_path.is_file()
        else ""
    )
    bundle_line = (
        f"| Download bundle | `{bundle_path.name}` ({bundle_path.stat().st_size / (1024 * 1024):.1f} MB zip) |\n"
        if bundle_path and bundle_path.is_file()
        else ""
    )
    readme.write_text(
        f"""# EIA ELEC article sample

Normalized slice of the [EIA Electricity Data Browser](https://www.eia.gov/electricity/data/browser/) bulk export for readers of the load forecasting article.

| | |
|---|---|
| Source file | `{source}` |
| Normalized parquet | `{normalized_path.name}` ({normalized_bytes / (1024 * 1024):.2f} MB) |
{raw_line}{bundle_line}| Series | {n_series:,} |
| Reading rows | {len(frame):,} |
| Period range | {period_min} – {period_max} |

The full EIA bulk download is ~350 MB and ~593k series. This repo excerpt holds **50,000** series (~8 MB raw). The normalized file is the easiest starting point for pandas; the raw excerpt keeps the original JSON-per-row layout.

## Columns (normalized)

- `series_id`, `series_name`, `units`, `frequency`, `state`, `lat`, `lon`, `fuel_code`
- `period` (YYYYMM), `value`

## Regenerate

```bash
python scripts/build_elec_article_sample.py
```

## Load in Python

```python
import pandas as pd

readings = pd.read_parquet("data/samples/ELEC_article_sample.parquet")
print(readings.groupby("state")["series_id"].nunique().head())
print(readings.query("fuel_code == 'WND'").head())
```
""",
        encoding="utf-8",
    )


def copy_raw_excerpt(source: Path, output_dir: Path) -> Path:
    dest = output_dir / RAW_EXCERPT_NAME
    if source.resolve() == dest.resolve():
        return dest
    shutil.copy2(source, dest)
    logger.info("Copied raw excerpt to %s (%.2f MB)", dest, dest.stat().st_size / 1e6)
    return dest


def write_bundle(output_dir: Path, members: list[Path]) -> Path:
    bundle = output_dir / BUNDLE_NAME
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in members:
            if path.is_file():
                zf.write(path, arcname=path.name)
    logger.info("Wrote bundle %s (%.2f MB)", bundle, bundle.stat().st_size / 1e6)
    return bundle


def build_sample(
    source: Path,
    output: Path,
    *,
    include_raw: bool,
    include_bundle: bool,
    compression: str,
) -> Path:
    records = parse_series_records(source)
    if not records:
        raise ValueError(f"No JSON series found in {source}")

    frame = flatten_records(records, max_series=None)
    size = write_parquet(frame, output, compression)
    logger.info("Normalized sample: %s rows, %.2f MB", len(frame), size / 1e6)

    output_dir = output.parent
    raw_path = copy_raw_excerpt(source, output_dir) if include_raw else None
    bundle_path = None
    if include_bundle:
        members = [output, output_dir / "README.md"]
        if raw_path:
            members.insert(1, raw_path)
        bundle_path = write_bundle(output_dir, members)

    write_readme(output_dir, frame, source, output, size, raw_path, bundle_path)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--compression",
        default="snappy",
        choices=("snappy", "zstd", "gzip", "none"),
    )
    parser.add_argument(
        "--no-raw-excerpt",
        action="store_true",
        help="Do not copy the raw ELEC.parquet excerpt into data/samples/",
    )
    parser.add_argument(
        "--no-bundle",
        action="store_true",
        help="Do not create article_data_bundle.zip",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    build_sample(
        args.source,
        args.output,
        include_raw=not args.no_raw_excerpt,
        include_bundle=not args.no_bundle,
        compression=args.compression,
    )


if __name__ == "__main__":
    main()
