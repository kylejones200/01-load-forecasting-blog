# Deployment Guide

LEAP runs as a standard Flask application on your laptop or any host that can install Python dependencies.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup/setup.sh   # optional parquet cache
python run.py
```

Open `http://localhost:3000`.

## Production (single host)

```bash
pip install -r requirements.txt gunicorn
export LEAP_DATA_DIR=/var/leap/cache
export SECRET_KEY=<random-secret>
gunicorn -w 2 -b 0.0.0.0:8000 run:app
```

Place `load_hourly.parquet` under `LEAP_DATA_DIR` or let the app generate synthetic series on first request.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `LEAP_DATA_DIR` | Parquet cache path | `data/cache` |
| `SECRET_KEY` | Flask secret | required in production |
| `PORT` / `FLASK_PORT` | Listen port | `3000` |
| `EIA_API_KEY` | Optional live EIA pulls in ingestion scripts | unset |

## Optional ML stack

```bash
pip install -e ".[ml]"
```

Installs PyTorch and MLflow for local experiment tracking when training ARIMA/LSTM modules under `app/services/models/`.

## Disclaimer

Educational/demo deployment only. Harden authentication, TLS, and data governance before any operational use.
