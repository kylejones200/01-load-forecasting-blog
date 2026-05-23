# LEAP APIs

LEAP favors public APIs first. Files fill the gaps. Local parquet caches back the Flask app.

# Core pattern

You pull from REST. You land JSON to a Volume. You load to bronze with Auto Loader. You standardize in silver. You build features in gold. You track state with a high-water mark.

```python
# /Workspace/Repos/leap/src/rest_to_delta.py
import os, json, time, requests
from datetime import datetime, timedelta
from pyspark.sql import functions as F

CAT = "leap"; BRZ = f"{CAT}.bronze"; VOL = f"/Volumes/{CAT}/bronze/raw"
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CAT}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {BRZ.split('.')[1]}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CAT}.bronze.raw")

def save_jsonl(objs, path):
 os.makedirs(os.path.dirname(path), exist_ok=True)
 with open(path, "a") as f:
 for o in objs:
 f.write(json.dumps(o) + "\n")

def get_mark(table):
 path = f"/dbfs{VOL}/_marks/{table}.txt"
 try:
 with open(path) as f: return f.read().strip()
 except: return None

def set_mark(table, mark):
 path = f"/dbfs{VOL}/_marks/{table}.txt"
 os.makedirs(os.path.dirname(path), exist_ok=True)
 with open(path,"w") as f: f.write(str(mark))

def upsert_jsonl_to_delta(path_glob, table, source):
 df = (spark.read.json(path_glob)
 .withColumn("_ingest_ts", F.current_timestamp())
 .withColumn("_source", F.lit(source)))
 spark.sql(f"CREATE TABLE IF NOT EXISTS {table} USING DELTA AS SELECT * FROM VALUES(1) t(dummy)")
 df.write.mode("append").saveAsTable(table)

# Example: EIA Open Data (Form 930 series)
def load_eia_series(series_ids, api_key, table="leap.bronze.eia930_series"):
 base = "https://api.eia.gov/series/"
 for sid in series_ids:
 r = requests.get(base, params={"api_key": api_key, "series_id": sid}, timeout=60)
 r.raise_for_status()
 payload = r.json()
 meta = payload["series"][0]
 rows = []
 for d, v in meta["data"]:
 rows.append({"series_id": sid, "period": d, "value": v, "name": meta.get("name")})
 day = datetime.utcnow().strftime("%Y-%m-%d")
 path = f"/dbfs{VOL}/eia930/{sid}/{day}.jsonl"
 save_jsonl(rows, path)
 upsert_jsonl_to_delta(f"{VOL}/eia930/{sid}/*.jsonl", table, "eia_api")

# Example: NOAA NWS (api.weather.gov) gridpoints
def load_nws_grid(lat, lon, table="leap.bronze.nws_grid"):
 # 1) point -> office/grid
 p = requests.get("https://api.weather.gov/points/{},{}".format(lat,lon), timeout=30).json()
 grid = p["properties"]
 office = grid["gridId"]; x = grid["gridX"]; y = grid["gridY"]
 # 2) hourly forecast
 f = requests.get(f"https://api.weather.gov/gridpoints/{office}/{x},{y}/forecast/hourly", timeout=60).json()
 rows = []
 for p in f["properties"]["periods"]:
 rows.append({
 "office": office, "x": x, "y": y,
 "startTime": p["startTime"], "temperature": p["temperature"],
 "windSpeed": p["windSpeed"], "shortForecast": p["shortForecast"]
 })
 day = datetime.utcnow().strftime("%Y-%m-%d")
 path = f"/dbfs{VOL}/nws/{office}/{x}_{y}/{day}.jsonl"
 save_jsonl(rows, path)
 upsert_jsonl_to_delta(f"{VOL}/nws/{office}/{x}_{y}/*.jsonl", table, "nws_api")

# Example: NOAA NCEI GHCN Daily (token in header)
def load_ghcn(token, dataset="GHCND", start="2020-01-01", end=None, station=None,
 table="leap.bronze.ghcn_daily"):
 end = end or datetime.utcnow().strftime("%Y-%m-%d")
 url = "https://www.ncdc.noaa.gov/cdo-web/api/v2/data"
 params = {"datasetid": dataset, "startdate": start, "enddate": end, "limit": 1000}
 if station: params["stationid"] = station
 headers = {"token": token}
 offset = 1
 collected = 0
 while True:
 rp = dict(params); rp["offset"] = offset
 r = requests.get(url, headers=headers, params=rp, timeout=60); r.raise_for_status()
 js = r.json(); results = js.get("results", [])
 if not results: break
 day = datetime.utcnow().strftime("%Y-%m-%d")
 path = f"/dbfs{VOL}/ghcn/{day}_{offset}.jsonl"
 save_jsonl(results, path); collected += len(results)
 offset += 1000; time.sleep(0.2)
 if collected:
 upsert_jsonl_to_delta(f"{VOL}/ghcn/*.jsonl", table, "noaa_ncei_api")

# Example: Census ACS 5-year
def load_acs(year=2023, vars=("NAME","B01003_001E"), geo="state:*",
 table="leap.bronze.acs5"):
 url = f"https://api.census.gov/data/{year}/acs/acs5"
 params = {"get": ",".join(vars), "for": geo}
 r = requests.get(url, params=params, timeout=60); r.raise_for_status()
 data = r.json(); hdr = data[0]; body = data[1:]
 rows = [dict(zip(hdr, row)) for row in body]
 day = datetime.utcnow().strftime("%Y-%m-%d")
 path = f"/dbfs{VOL}/census/acs5/{year}_{geo.replace(':','-')}_{day}.jsonl"
 save_jsonl(rows, path)
 upsert_jsonl_to_delta(f"{VOL}/census/acs5/*.jsonl", table, "census_api")

# Example: OSM POI via Overpass
def load_osm_bbox(minx, miny, maxx, maxy, key="amenity", val="fuel",
 table="leap.bronze.osm_poi"):
 url = "https://overpass-api.de/api/interpreter"
 q = f'[out:json][timeout:30];node["{key}"="{val}"]({miny},{minx},{maxy},{maxx});out;'
 r = requests.post(url, data=q, timeout=60); r.raise_for_status()
 js = r.json()
 rows = []
 for e in js.get("elements", []):
 rows.append({"id": e["id"], "lat": e.get("lat"), "lon": e.get("lon"),
 "tags": e.get("tags", {}), "type": e.get("type")})
 day = datetime.utcnow().strftime("%Y-%m-%d")
 path = f"/dbfs{VOL}/osm/{key}_{val}_{day}.jsonl"
 save_jsonl(rows, path)
 upsert_jsonl_to_delta(f"{VOL}/osm/*.jsonl", table, "overpass_api")

# Example: CAISO OASIS hourly demand (CSV over HTTP)
def load_caiso_demand(start, end, table="leap.bronze.caiso_demand"):
 base = "http://oasis.caiso.com/mrtu-oasis/Service"
 params = {
 "queryname":"SLD_FCST",
 "resultformat":"6",
 "startdatetime": start, # e.g., 20250101T00:00-0000
 "enddatetime": end,
 "market_run_id":"DAM"
 }
 r = requests.get(base, params=params, timeout=120); r.raise_for_status()
 day = datetime.utcnow().strftime("%Y-%m-%d")
 path = f"/dbfs{VOL}/caiso/{day}.csv"
 open(path, "wb").write(r.content)
 (spark.read.option("header", True).csv(f"{VOL}/caiso/*.csv")
 .withColumn("_ingest_ts", F.current_timestamp())
 .withColumn("_source", F.lit("caiso_oasis"))
 .write.mode("append").saveAsTable(table))
```

# EIA Form 930 map

You need series ids for BA load. EIA exposes hourly load as series. You define a list. You call the loader.

```python
# common BA load series. expand as needed.
EIA_SERIES = [
 "EBA.TEX-ALL.D.H", # ERCOT demand hourly
 "EBA.CAL-ALL.D.H", # CAISO demand hourly
 "EBA.PJM-ALL.D.H", # PJM demand hourly
]
load_eia_series(EIA_SERIES, api_key=dbutils.secrets.get("leap","eia"))
```

# NOAA weather map

You cover each service area with a point grid. You call the NWS endpoint per point. You stage the hourly forecast.

```python
points = [(38.58,-121.49), (34.05,-118.24)]
for lat, lon in points:
 load_nws_grid(lat, lon)
```

GHCN covers history. You pull with a token.

```python
load_ghcn(token=dbutils.secrets.get("leap","noaa"), start="2018-01-01")
```

# Census and OSM map

You pull ACS for states or counties. You pull POI for EVs, fuel, or large retail.

```python
load_acs(year=2023, vars=("NAME","B01003_001E","B25035_001E"), geo="county:*")
load_osm_bbox(-122.8,37.0,-121.5,38.3,key="amenity",val="charging_station")
```

# Silver shape

You convert each bronze feed to a tidy table. You align time to UTC. You keep one key per table. You keep a clean schema.

```python
from pyspark.sql import functions as F
spark.sql("CREATE SCHEMA IF NOT EXISTS leap.silver")

e930 = spark.table("leap.bronze.eia930_series")
load_hourly = (e930
 .withColumn("ts_utc", F.to_timestamp(F.col("period")))
 .withColumn("ba", F.split(F.col("series_id"), "\\.")[1]) # e.g., TEX-ALL
 .select("ba","ts_utc", F.col("value").cast("double").alias("mw"))
 .filter(F.col("mw").isNotNull()))
load_hourly.write.mode("overwrite").saveAsTable("leap.silver.load_hourly")

nws = spark.table("leap.bronze.nws_grid")
weather_hourly = (nws.select(
 F.to_timestamp("startTime").alias("ts_utc"),
 "office","x","y",
 F.col("temperature").cast("double").alias("t_c"),
 "windSpeed","shortForecast"))
weather_hourly.write.mode("overwrite").saveAsTable("leap.silver.weather_hourly")

acs = spark.table("leap.bronze.acs5")
pop = (acs.select(F.col("NAME").alias("name"),
 F.col("B01003_001E").cast("int").alias("population"),
 "state","county"))
pop.write.mode("overwrite").saveAsTable("leap.silver.acs_population")

osm = spark.table("leap.bronze.osm_poi")
poi = (osm.select("id","lat","lon",F.col("tags")["amenity"].alias("amenity")))
poi.write.mode("overwrite").saveAsTable("leap.silver.poi")
```

# ISO add-ons

CAISO OASIS serves CSV. NYISO and PJM serve JSON with keys. You add those as needed. You keep the same pattern. You land to Volume. You append to bronze. You standardize to silver.

# Workflows

You set four tasks. You pull EIA. You pull NOAA. You pull Census and OSM. You build silver. You set daily times for slow feeds. You set hourly times for load and weather.

# Security

You store keys in a Secret Scope. You pass them to the loaders. You never print them.

```python
eia_key = dbutils.secrets.get("leap","eia")
noaa_key = dbutils.secrets.get("leap","noaa") # for NCEI
```

# Gaps and files

FERC 714 stays bulk. ISO queues and many plans stay bulk. TIGER shapes ship as files. Auto Loader covers those. The app still works.

# What you run next

You create the catalog, schemas, and volume. You add secrets. You run the loaders for one BA and two weather points. You build silver. You wire the LEAP feature job on top. You train a first model.
