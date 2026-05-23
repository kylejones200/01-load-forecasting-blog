# 01 Load Forecasting Blog

Published: draft  
Medium: [https://medium.com/@kyle-t-jones/01-load-forecasting-blog-887ac9422b7b](https://medium.com/@kyle-t-jones/01-load-forecasting-blog-887ac9422b7b)

## Business context

Power markets operate on razor-thin margins where a single miscalculation can cost millions. When Texas faced its historic winter storm in February 2021, load forecasting errors contributed to widespread blackouts and electricity prices that spiked to $9,000 per megawatt-hour — nearly 180 times the normal rate.

Load forecasting is not only predicting tomorrow's megawatts. It is joining weather, calendar effects, and grid physics so operators and traders can position ahead of peaks, price risk, and keep supply and demand balanced in real time.

## Companion application: LEAP

This repository is the **full implementation** behind the article. **LEAP** (Load Estimation and Planning) is a local Flask application: synthetic and parquet-backed hourly load, weather-aware features, ERCOT 4CP scoring, trend and pattern forecasting, and engineering analysis APIs.

- Essay draft: [article.md](article.md) and [docs/MEDIUM_ARTICLE.md](docs/MEDIUM_ARTICLE.md)
- Run locally: `python run.py` (dashboard at port 3000)
- Tests: `pytest tests/ -q`

---

# LEAP — Load Estimation and Planning

A grid intelligence demo that runs entirely on your machine. LEAP combines public energy datasets (bundled under `data/`), synthetic hourly load shaped like real balancing-authority curves, and REST APIs plus a dashboard for forecasting and engineering what-if analysis.

## What it does

- **Hourly load forecasting** for 7 US balancing authorities (LightGBM + ARIMA + LSTM)
- **ERCOT 4CP risk scoring** — predicts the 4 summer peak hours that drive transmission charges
- **Outage-weather correlation** — joins real EAGLE-I outage events with weather to show what caused them
- **Power flow analysis** — Newton-Raphson AC power flow with N-1 contingency testing
- **Grid stability analysis** — frequency response, inertia, voltage stability, renewable integration impact
- **Load characterization** — power factor, diversity factor, load duration curves, engineering constraints
- **Storm warning impact** — severe weather alerts mapped to demand impact on load forecasts
- **Generation fleet analysis** — fuel mix, capacity, emissions, and renewable penetration by BA
- **Scenario planning** — hot weather, high growth, demand response what-if analysis

## Datasets

All data is public or freely available. No proprietary utility data is required.

### EIA Hourly Load (Form 930 / Electricity Data Browser)

Hourly electricity demand by balancing authority from the US Energy Information Administration. This is the core time series that powers load forecasting.

| | |
|---|---|
| **Source** | US Energy Information Administration (EIA) |
| **Dataset** | Hourly Electric Grid Monitor (Form 930) |
| **URL** | https://www.eia.gov/electricity/gridmonitor/ |
| **API** | https://api.eia.gov/v2/electricity/rto/region-data/data/ |
| **API docs** | https://www.eia.gov/opendata/documentation.php |
| **API key** | Free registration at https://www.eia.gov/opendata/register.php |
| **Format** | JSON via REST API, hourly frequency |
| **Coverage** | All US balancing authorities, hourly since 2015 |
| **Local store** | `leap.bronze.eia_rto_load` → `leap.silver.load_hourly` |
| **Fields used** | `respondent` (BA code), `period` (hour), `value` (demand MW), `type` (D=demand) |
| **Update frequency** | Hourly, ~1 hour lag |

### EIA Plant-Level Series (ELEC.parquet)

The full EIA electricity dataset as a parquet file — 593K time series covering plant-level generation, consumption, and fuel data.

| | |
|---|---|
| **Source** | US Energy Information Administration (EIA) |
| **Dataset** | Electricity Data Browser bulk download |
| **URL** | https://www.eia.gov/opendata/bulk-downloads.php |
| **Format** | Parquet (593K rows, each a JSON blob with metadata + time series) |
| **Coverage** | All US power plants, monthly data back to 2001 |
| **Local store** | `leap.bronze.eia_plant_series` |
| **Fields** | series_id, plant name, fuel type, state, lat/lon, monthly values |

### Open-Meteo Weather

Hourly weather observations and 7-day forecasts. Free, no API key, no rate limits.

| | |
|---|---|
| **Source** | Open-Meteo GmbH |
| **Historical API** | https://archive-api.open-meteo.com/v1/archive |
| **Forecast API** | https://api.open-meteo.com/v1/forecast |
| **Docs** | https://open-meteo.com/en/docs |
| **API key** | None required (free tier: 10,000 requests/day) |
| **Format** | JSON, hourly resolution |
| **Coverage** | Global, 1940–present (historical), 16-day ahead (forecast) |
| **Local store** | `leap.silver.weather_hourly` |
| **Fields used** | `temperature_2m` (°F), `relative_humidity_2m` (%), `wind_speed_10m` (mph), `weather_code` (WMO) |
| **Weather codes** | WMO standard: 0=Clear, 1-3=Cloudy, 51-55=Drizzle, 61-65=Rain, 71-75=Snow, 95-99=Thunderstorm |

### EAGLE-I Power Outages

County-level power outage data from the DOE's EAGLE-I system. Tracks customers without power across the US.

| | |
|---|---|
| **Source** | US Department of Energy, Office of Electricity |
| **System** | EAGLE-I (Environment for Analysis of Geo-Located Energy Information) |
| **URL** | https://eagle-i.doe.gov/ |
| **Data access** | https://eagle-i.doe.gov/dataset/power-outages-hourly-county |
| **Format** | Parquet, 15-minute intervals aggregated to hourly |
| **Coverage** | All US counties, 2014–present |
| **Local store** | `leap.silver.outages` |
| **Fields used** | `fips_code`, `county`, `state`, `sum` (customers out), `run_start_time` |
| **Volume** | ~13M records/year |
| **Notes** | The `sum` column is a snapshot of customers currently without power, not a count of events. |

### EPA eGRID (Emissions & Generation Resource Integrated Database)

Plant-level data for the entire US power generation fleet.

| | |
|---|---|
| **Source** | US Environmental Protection Agency (EPA) |
| **Dataset** | eGRID — Emissions & Generation Resource Integrated Database |
| **URL** | https://www.epa.gov/egrid |
| **Download** | https://www.epa.gov/egrid/download-data |
| **Format** | Excel (published), converted to Parquet |
| **Coverage** | All US power plants, biennial 1996–2023 |
| **Local store** | `leap.silver.plants` |
| **Fields used** | Plant name, ORIS code, state, county, lat/lon, BA code, primary fuel, nameplate capacity (MW), annual net generation (MWh), CO2 emissions (tons), CO2 rate (lb/MWh), utility name |
| **Plant count** | ~36K rows loaded (3 most recent years) |
| **Fuel codes** | NG=Natural Gas, WND=Wind, SUN=Solar, SUB=Subbituminous Coal, NUC=Nuclear, WAT=Water, DFO=Distillate Fuel Oil |

### ERCOT 4CP Historical Dates

The four hours each summer when ERCOT system-wide demand peaked. Texas utilities pay transmission charges based on their load during these hours.

| | |
|---|---|
| **Source** | Electric Reliability Council of Texas (ERCOT) |
| **Dataset** | Four Coincident Peak (4CP) Calculation Filings |
| **URL** | https://www.ercot.com/mktinfo/data_agg/4cp |
| **Data product** | https://www.ercot.com/mp/data-products/data-product-details?id=NP9-83-M |
| **Format** | Excel (published), extracted to CSV |
| **Coverage** | 1996–2025 (116 peak events) |
| **Local store** | `leap.gold.fourcp_dates` |
| **Notes** | One event per month (June–September) per year. Peaks typically occur 4:00–5:45 PM CDT on weekdays. |

### HIFLD Transmission Lines

High-voltage transmission line segments from the Homeland Infrastructure Foundation-Level Data program.

| | |
|---|---|
| **Source** | Department of Homeland Security, HIFLD |
| **URL** | https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-power-transmission-lines |
| **Format** | Parquet (converted from Shapefile) |
| **Coverage** | All US transmission lines, 74K segments |
| **Local store** | `leap.silver.transmission_lines` |
| **Fields used** | ID, type (overhead/underground), owner, voltage (kV), voltage class, substations, lat/lon endpoints |

## Local data layout

```
data/
├── cache/                    # Generated by scripts/seed/seed_synthetic.py
│   └── load_hourly.parquet   # 90 days hourly load x 7 BAs
├── ELEC.parquet              # 50k-series excerpt of EIA bulk export (~8 MB)
├── samples/
│   ├── ELEC_article_sample.parquet   # Normalized for pandas (regenerate via script)
│   ├── ELEC_bulk_excerpt.parquet     # Raw JSON-per-row excerpt (copy of above)
│   └── article_data_bundle.zip       # ~10 MB zip for article readers
└── HIFLD_*.parquet           # Optional transmission lines
```

## Balancing Authorities

| Code | Name | Region | Weather Station |
|---|---|---|---|
| CAL-ALL | California ISO (CISO) | WECC | Sacramento, CA |
| TEX-ALL | ERCOT | ERCOT | Dallas, TX |
| PJM-ALL | PJM Interconnection | RFC | Philadelphia, PA |
| MISO-ALL | Midcontinent ISO | MRO | Chicago, IL |
| NYIS-ALL | New York ISO | NPCC | New York, NY |
| ISNE-ALL | ISO New England | NPCC | Boston, MA |
| SWPP-ALL | Southwest Power Pool | MRO | Kansas City, MO |

## Quick Start

### Local development

```bash
pip install -r requirements.txt
bash scripts/setup/setup.sh   # optional: writes data/cache/load_hourly.parquet
python run.py                 # http://localhost:3000
```

Or use the Makefile: `make setup && make run`.

Install optional ML extras (PyTorch, MLflow file tracking): `pip install -e ".[ml]"`.

## API Endpoints

### Load & Forecasting
| Endpoint | Description |
|---|---|
| `GET /api/leap/areas` | List balancing authorities |
| `GET /api/leap/load/{ba}` | Historical hourly load |
| `GET /api/leap/forecast/{ba}?horizon=24&model=lightgbm` | Generate forecast |
| `GET /api/leap/scenarios/{ba}` | Compare scenarios (baseline, hot_weather, etc.) |
| `GET /api/leap/features/{ba}` | Engineered feature data |
| `GET /api/leap/metrics/{ba}` | Model performance metrics |
| `POST /api/leap/train/{ba}` | Trigger model training |
| `GET /api/leap/export/{ba}?format=csv` | Export forecast data |

### Weather
| Endpoint | Description |
|---|---|
| `GET /api/leap/weather?ba=TEX-ALL` | Hourly weather for a BA |

### Outage-Weather Correlation
| Endpoint | Description |
|---|---|
| `GET /api/leap/outage-correlation?ba=TEX-ALL&severity=Major` | Outage events with weather |
| `GET /api/leap/outage-correlation/summary` | Aggregated stats by cause, severity, BA |
| `GET /api/leap/outage-correlation/timeline/{ba}` | Time series for charting |

### ERCOT 4CP
| Endpoint | Description |
|---|---|
| `GET /api/leap/4cp/summary` | Capability overview and business context |
| `GET /api/leap/4cp/dates` | All 116 historical peak events (1996-2025) |
| `GET /api/leap/4cp/score/2025-07-15` | Score a specific day for 4CP risk |
| `GET /api/leap/4cp/summer/2025` | Full summer season risk timeline |

### Engineering Analysis
| Endpoint | Description |
|---|---|
| `GET /api/leap/engineering/storm-warnings?ba=TEX-ALL` | Severe weather alerts + demand impact |
| `POST /api/leap/engineering/powerflow` | Newton-Raphson AC power flow analysis |
| `GET /api/leap/engineering/load-characterization/{ba}` | Power factor, diversity, LDC from real data |
| `POST /api/leap/engineering/stability-analysis` | Frequency, inertia, voltage, transient stability |
| `POST /api/leap/engineering/contingency-analysis` | N-1 contingency testing |
| `POST /api/leap/engineering/renewable-integration` | Renewable impact on grid stability |

### Generation Fleet & Infrastructure
| Endpoint | Description |
|---|---|
| `GET /api/leap/eia/stats` | EIA dataset statistics |
| `GET /api/leap/eia/plants?state=TX` | Plant-level EIA data |
| `GET /api/leap/transmission/stats` | Transmission line statistics |
| `GET /api/leap/config` | Application configuration |
| `GET /health` | Health check |

## Models

### Tier 1: Auto ARIMA Baseline
Automated ARIMA with 24-hour seasonal component. Handles all BAs with minimal data. Trains in seconds. Configurable (p, d, q) order with confidence intervals.

### Tier 2: LightGBM Advanced
Gradient boosting with features: lag-1h, lag-24h, 24h moving average, hour, day-of-week, month, temperature, wind speed. Typically 30-40% lower MAPE than ARIMA. TimeSeriesSplit cross-validation.

### Tier 3: LSTM Neural Network
PyTorch 2-layer LSTM (64 units, dropout 0.2) with MinMax scaling. Captures nonlinear weather-to-load relationships that tree models miss. Best for regions with complex seasonal patterns.

### ERCOT 4CP Engine
Ridge regression on daily weather (temp max/min, apparent temp, precipitation) to predict peak load, combined with rule-based scoring (season threshold, event gap, heat index, weekday check). Outputs a 0-1 risk score and go/no-go decision for demand response activation.

Train with the modules under `app/services/models/` (ARIMA, LSTM). Metrics returned by the API are demo values until you wire your own evaluation loop.

## Engineering Analysis

LEAP includes full electrical engineering analysis capabilities that validate forecasts against grid constraints.

### Power Flow
Newton-Raphson AC power flow solver with Y-bus matrix construction. Computes bus voltages, line power flows, system losses, and convergence diagnostics. Supports sensitivity analysis for parameter variations.

### N-1 Contingency
Tests generator and line outages against the base case. Detects voltage violations (±5% limits), classifies severity, and identifies critical contingencies.

### Load Characterization
Maps forecast MW to electrical engineering terms: power factor by load type (residential 0.85, commercial 0.90, industrial 0.95), diversity factors (0.6–0.9), load duration curves with percentiles, coincidence factors, and growth trend analysis.

### System Stability
Five-component analysis:
1. **Inertia** — system inertia constant, generator type mix, adequacy assessment
2. **Frequency response** — ramping rates, df/dt calculations, reserve requirements
3. **Voltage stability** — margin analysis, sensitivity to load changes, critical load levels
4. **Transient stability** — critical clearing time, fault tolerance margin
5. **Small signal stability** — damping ratios for local, inter-area, and torsional modes

### Renewable Integration Impact
Quantifies how increasing renewable penetration affects grid stability: net load profiling, inertia reduction (50% per unit for renewables), frequency response degradation, voltage fluctuation, and ramping requirements. Recommends mitigations (synchronous condensers, SVCs, STATCOMs, grid-forming inverters).

### Storm Warning Impact
Integrates NOAA/NWS severe weather alerts into demand impact assessment. Maps 12 alert types (tornado, severe thunderstorm, flood, winter storm, heat, wind, etc.) to demand multipliers (1.0–2.0x) adjusted by severity. Returns impact level (HIGH/MEDIUM/LOW) with confidence.

## Project structure

```
├── app/                    # Flask app, services, templates
├── data/                   # Bundled parquet + generated cache
├── docs/                   # Article and architecture notes
├── scripts/
│   ├── setup/setup.sh      # Local cache bootstrap
│   └── seed/seed_synthetic.py
├── tests/
├── run.py
└── pyproject.toml
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `LEAP_DATA_DIR` | Parquet cache directory | `data/cache` |
| `FLASK_PORT` | Local server port | `3000` |
| `SECRET_KEY` | Flask session secret | change in production |
| `EIA_API_KEY` | Optional EIA API key for live ingestion scripts | — |

## Disclaimer

Educational/demo code only. Not financial, safety, or engineering advice. Use at your own risk. Verify results independently before any production or operational use.

## License

MIT — see [LICENSE](LICENSE).
