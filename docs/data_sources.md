You can get most of the public data for a LEAP app through APIs. Here’s the landscape:

**Load and Demand Data**
EIA (Energy Information Administration) offers APIs:

* **Form 930**: Balancing Authority (BA) hourly load and interchange.
* **Form 861**: Sales and customers (annual).
* **Form 860**: Generator unit attributes.
* **Form 923**: Monthly generation and fuel.

FERC Form 714 has load forecasts and actuals, but it is in filings, not an API. You can fetch it as bulk data and stage it into Databricks.

**Weather Data**

* **NOAA GHCN Daily**: Station-level weather via API.
* **NOAA NDFD**: Forecast grids via REST API.
* **NOMADS**: Model forecasts (GFS, HRRR) via API endpoints.

**Population and Boundaries**

* **US Census Bureau API**: ACS population, households, income.
* **TIGER/Line Shapefiles**: Boundaries via FTP or Census API for GIS.
* **OpenStreetMap (OSM)**: Points of interest and land use via Overpass API.

**ISO / RTO**
Some ISOs have public APIs:

* CAISO OASIS.
* NYISO real-time and day-ahead load.
* PJM Data Miner 2.
* MISO public reports (CSV, but programmatically retrievable).

**Other Sources**

* NREL has APIs for PV and renewable potential.
* EIA’s Open Data API covers fuel prices, electricity, and more.

**Gaps**

* Some planning data (capacity expansion, interconnection queues) come as Excel/CSV, not APIs.
* FERC data often comes in bulk download, not real-time.

So in short: yes, most of LEAP can be fed from APIs (EIA, NOAA, Census, ISO feeds). You will still need to ingest bulk files for FERC and some ISO planning datasets.

Would you like me to draft the API endpoints and sample Databricks Auto Loader configs for each of these sources so you can plug them into the LEAP bronze layer?
