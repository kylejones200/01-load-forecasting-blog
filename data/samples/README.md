# EIA ELEC article sample

Normalized slice of the [EIA Electricity Data Browser](https://www.eia.gov/electricity/data/browser/) bulk export for readers of the load forecasting article.

| | |
|---|---|
| Source file | `data/ELEC.parquet` |
| Normalized parquet | `ELEC_article_sample.parquet` (5.11 MB) |
| Raw excerpt | `ELEC_bulk_excerpt.parquet` (8.0 MB) |
| Download bundle | `article_data_bundle.zip` (10.6 MB zip) |
| Series | 50,000 |
| Reading rows | 221,951 |
| Period range | 202501 – 2025Q2 |

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
