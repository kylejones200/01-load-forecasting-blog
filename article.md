---
canonical_link: "https://medium.com/@kyle-t-jones/01-load-forecasting-blog-887ac9422b7b"
date_exported_from_medium: "November 10, 2025"
companion_app: "LEAP (Load Estimation and Planning) — see README.md"
---

# Why Electric Load Forecasting Still Runs the Grid (and How One System Puts Theory to Work)

Power grids do not store electricity at scale the way a warehouse stores boxes. Supply and demand must stay in close balance every second. Operators plan hours and days ahead so generators, imports, and demand response can meet the shape of tomorrow's load. That planning rests on load forecasts: estimates of how many megawatts customers will draw at each hour.

This article explains what load forecasting is, why it is hard, and how teams build systems that stay useful in production. The companion code in this repository is **LEAP** (Load Estimation and Planning): a local Flask application with hourly load series, weather-aware features, ERCOT 4CP scoring, and multi-model forecasting hooks. The point is the loop: data, models, metrics, and human review.

## The job in plain terms

A load forecast answers a simple question: how much power will we need, and when?

The answer feeds unit commitment, market bids, reserve margins, and maintenance windows. A forecast that is too high ties up fuel and capacity. A forecast that is too low risks tight reserves or emergency measures. Small errors at off-peak hours matter less than errors at the peak hour of a hot summer day.

## What actually moves the needle

Electric load repeats with the clock and the calendar. Weather is the largest external driver for short horizons. The grid itself is changing: rooftop solar, storage, and flexible loads all shift the shape operators must predict.

## Models in LEAP

LEAP compares classical and machine-learning families on held-out hours per balancing authority:

1. **ARIMA** — fast seasonal baseline (`app/services/models/arima_model.py`)
2. **LightGBM** — gradient boosting on lags, calendar features, and weather
3. **LSTM** — optional PyTorch sequence model (`pip install -e ".[ml]"`)

The live API uses trend extrapolation from recent load when history is available, then falls back to a seasonal pattern by balancing authority.

## Data work is most of the project

Forecasts fail in the warehouse more often than in the equation. LEAP keeps a simple local layout:

- `data/cache/load_hourly.parquet` — synthetic or seeded hourly load for seven US balancing authorities
- `data/samples/ELEC_article_sample.parquet` — normalized EIA plant series for pandas (~5 MB)
- `data/samples/article_data_bundle.zip` — zip (~10 MB) with normalized + raw excerpt
- `data/ELEC.parquet` — 50k-series excerpt of the full ~350 MB EIA bulk file

Regenerate ELEC samples:

```bash
python scripts/build_elec_article_sample.py
```

Regenerate load cache:

```bash
python scripts/seed/seed_synthetic.py
```

## Short-term forecasting as a pipeline

Industry ST-ELF-style pipelines ingest history, build features, score models, monitor drift, and visualize results. LEAP implements that shape for a laptop demo: ingestion scripts under `scripts/`, feature construction in `app/services/local_data.py`, forecasting in `app/services/forecast_service.py`, and charts on the dashboard.

## Run the companion app

```bash
pip install -r requirements.txt
python run.py
```

Open `http://localhost:3000`. Example APIs:

- `GET /api/leap/areas`
- `GET /api/leap/load/TEX-ALL?limit=168`
- `GET /api/leap/forecast/TEX-ALL?horizon=24`

Full API reference and dataset notes are in [README.md](README.md). The long-form essay is in [docs/MEDIUM_ARTICLE.md](docs/MEDIUM_ARTICLE.md).

---

*Educational/demo code only. Not financial, safety, or engineering advice.*
