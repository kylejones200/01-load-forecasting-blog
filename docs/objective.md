# LEAP objectives (local app)

LEAP estimates load and plans capacity with public data. The runtime is a Flask app with parquet-backed hourly series, optional model training modules, and a dashboard. The map sits on the left. Insights sit on the right. A drag handle resizes the two panes.

# Scope

LEAP covers service areas in the United States. LEAP builds short term and long term load forecasts. LEAP runs scenario plans for weather, growth, and demand response. LEAP tracks error, drift, and model health. LEAP exports schedules for planners.

# Data

LEAP relies on public sources. EIA Form 930 gives hourly grid load by BA. EIA 861 and 860 give sales, customers, and asset counts. EIA 923 gives plant outputs. NOAA GHCN and NDFD give weather. US Census ACS gives people and households. TIGER shapes give boundaries. OpenStreetMap gives POI counts. FERC Form 714 gives planning area hourly load where available. All sources require no payment. Some sources throttle. Workflows handle rate limits.

# Lakehouse layout

One catalog holds LEAP. One schema holds bronze. One schema holds silver. One schema holds gold. All tables use Delta. All tables sit in Unity Catalog. One volume holds raw files when needed.

# Ingest

Auto Loader pulls CSV and JSON into bronze. Each batch appends a source tag and a load timestamp. Expectations catch bad rows and quarantine them. Normalizers set time to UTC and align daylight time. Simple code follows.

```python
from pyspark.sql import functions as F

catalog = "leap"
spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"USE CATALOG {catalog}")
for s in ["bronze","silver","gold"]:
 spark.sql(f"CREATE SCHEMA IF NOT EXISTS {s}")

spark.sql("CREATE VOLUME IF NOT EXISTS bronze.raw")

eia930_path = "abfss://.../eia930" # or s3 path
eia_df = (spark.readStream.format("cloudFiles")
 .option("cloudFiles.format","csv")
 .option("cloudFiles.inferColumnTypes","true")
 .load(eia930_path)
 .withColumn("ingest_ts", F.current_timestamp())
 .withColumn("source", F.lit("eia930")))
(eia_df.writeStream
 .option("checkpointLocation", "abfss://.../chk/eia930")
 .trigger(once=True)
 .toTable("leap.bronze.eia930"))
```

# Standardize

Silver tables hold clean time series. Keys stay simple. One table holds hourly load per area. One table holds hourly weather per county or grid. One table maps service area to counties and zip codes. One table holds events and holidays. A short pass builds them.

```python
bronze = "leap.bronze"
silver = "leap.silver"

raw = spark.table(f"{bronze}.eia930")
load = (raw
 .withColumnRenamed("Balancing Authority","ba")
 .withColumn("ts_utc", F.to_timestamp("DATETIME_UTC"))
 .select("ba","ts_utc",F.col("VALUE").alias("mw"))
 .filter(F.col("mw").isNotNull()))
load.write.mode("overwrite").saveAsTable(f"{silver}.load_hourly")
```

Weather follows the same shape. Columns use ts_utc, fips, t2m, rh, wspd, ghi. Join by nearest station or grid. Cache a station crosswalk to cut cost.

# Features

Gold tables hold features. Window ops build lags and stats. Calendar fields add season, hour, and holiday. POI density and ACS mix shift the level. Simple code sets the pattern.

```python
from pyspark.sql.window import Window

silver = "leap.silver"
gold = "leap.gold"

ld = spark.table(f"{silver}.load_hourly")
cal = (ld.select("ts_utc")
 .withColumn("dow", F.dayofweek("ts_utc"))
 .withColumn("hour", F.hour("ts_utc"))
 .withColumn("month", F.month("ts_utc"))
 .dropDuplicates())

w = Window.partitionBy("ba").orderBy("ts_utc")
feat = (ld.join(cal, "ts_utc")
 .withColumn("mw_lag1", F.lag("mw",1).over(w))
 .withColumn("mw_lag24", F.lag("mw",24).over(w))
 .withColumn("mw_ma24", F.avg("mw").over(w.rowsBetween(-24,0)))
 .withColumn("is_holiday", F.lit(0))) # swap with real holiday table
feat.write.mode("overwrite").saveAsTable(f"{gold}.features_hourly")
```

# Models

Two tiers cover most needs. A baseline handles every area. A boosted model wins when data allows.

Tier one uses SARIMAX or Prophet or Databricks AutoML Forecaster. Tier two uses LightGBM with lags, weather, and calendar. MLflow tracks each run and stage. The registry holds the best per area and horizon. Code stays short.

```python
import mlflow
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_percentage_error as mape

df = spark.table("leap.gold.features_hourly").toPandas()
areas = sorted(df["ba"].unique())
mlflow.set_experiment("/leap/forecast")

for ba in areas:
 d = df[df.ba==ba].dropna()
 X = d[["mw_lag1","mw_lag24","mw_ma24","hour","dow","month"]]
 y = d["mw"]
 split = TimeSeriesSplit(n_splits=5)
 best = None
 with mlflow.start_run(run_name=f"lgbm_{ba}"):
 model = LGBMRegressor(n_estimators=500)
 preds = y.copy()
 preds[:] = pd.NA
 for tr, te in split.split(X):
 model.fit(X.iloc[tr], y.iloc[tr])
 preds.iloc[te] = model.predict(X.iloc[te])
 score = float(mape(y.dropna(), preds.dropna()))
 mlflow.log_metric("mape", score)
 mlflow.sklearn.log_model(model, "model",
 registered_model_name=f"leap_{ba}_hourly")
```

# Forecast flows

Workflows drive jobs. One job ingests. One job builds features. One job trains. One job scores. One job backfills and recalculates error. Each job writes to Delta. Each job logs to MLflow. A small driver handles horizons for day ahead and week ahead. A shadow job runs champion and challenger. A monitor job tests drift with PSI and KS tests.

# Scenarios

Scenarios shift inputs and rerun the scorer. Weather up ten percent. Weather down ten percent. Growth up two percent per year. EV load adds a block by zip. Databricks Apps pass a payload to a scorer route. The route writes a scenario id and runs a forecast view. Delta holds the traces. Users compare traces in the UI.

# Optimization

A simple planner converts load to a plan. The planner uses a unit table or a resource table. The table holds ramp, cost, and min up. A greedy pass gives a first plan. A MILP pass with OR-Tools or pulp gives a better plan. The solver reads the same gold tables. The planner writes a schedule table and a cost table. A policy switch can add demand response blocks before units.

# App

The app runs in Databricks Apps. The backend uses Flask. The frontend uses plain HTML plus htmx. The left pane shows a Kepler.gl map. The right pane shows charts and tables. A handle resizes the panes. Users pick area, horizon, and scenario. Users click Export to produce CSV and Parquet.

```python
# app.py
from flask import Flask, request, jsonify, send_file
from pyspark.sql import functions as F

app = Flask(__name__)

@app.get("/areas")
def areas():
 df = spark.table("leap.silver.load_hourly").select("ba").distinct()
 return jsonify([r.ba for r in df.collect()])

@app.get("/forecast")
def forecast():
 ba = request.args.get("ba")
 h = int(request.args.get("h", 24))
 feat = spark.table("leap.gold.features_hourly").filter(F.col("ba")==ba)
 last = feat.agg(F.max("ts_utc").alias("t")).collect()[0].t
 # simple drift safe walk forward
 pdf = feat.filter(F.col("ts_utc")<=last).toPandas().dropna()
 X = pdf[["mw_lag1","mw_lag24","mw_ma24","hour","dow","month"]]
 import mlflow
 model = mlflow.pyfunc.load_model(f"models:/leap_{ba}_hourly/Production")
 # roll future with naive lags seeded from last row
 out = []
 row = pdf.iloc[-1].copy()
 for i in range(h):
 x = row[["mw_lag1","mw_lag24","mw_ma24","hour","dow","month"]].to_frame().T
 yhat = float(model.predict(x)[0])
 out.append({"t": str(row.ts_utc + pd.Timedelta(hours=1)),
 "ba": ba, "mw_hat": yhat})
 row.ts_utc = row.ts_utc + pd.Timedelta(hours=1)
 row.mw_lag24 = row.mw_lag23 if "mw_lag23" in row else row.mw_lag24
 row.mw_lag1 = yhat
 row.mw_ma24 = 0.95*row.mw_ma24 + 0.05*yhat
 row.hour = int((row.hour + 1) % 24)
 row.dow = int(1 + ((row.dow) % 7))
 return jsonify(out)
```

# Maps

The map draws service areas and substations. TIGER shapes supply counties and places. A small tile service serves vector tiles from Delta. The app overlays heat for forecast load per county. The right pane shows time series. The user can pull the split bar to favor the map or the charts.

# Quality

Unit tests cover data contracts. Expectations check schema and ranges. A daily job computes MAPE, MASE, sMAPE, and bias. Results land in a gold.metrics table. A dashboard reads that table. Alerts fire on rule breaks.

# Security

Unity Catalog controls data. Catalog grants keep teams in bounds. The app reads through a service principal. Secrets live in the Databricks secret scope. No keys live in code. All tables sit in the same metastore.

# Deploy

Use Repos for code. Use a single repo with src, jobs, and app. Use a simple makefile to build the wheel. Use a single Workflow with tasks for each job. Pin the cluster policy. Pin the runtime. Use the MLflow registry for model routes. Promote on green tests only.

# Outputs

LEAP produces four forms. Delta tables hold truth. CSV supports exports. Parquet supports data science. PDF reports support execs. A job writes a weekly pack with error and model notes.

# Roadmap

Add feeder level forecasts with AMI where public files exist. Add probabilistic forecasts with Quantile GBM. Add extremes with EVT. Add price side with ISO LMP where valid. Add a small API to accept private AMI in the same app. Keep the split of public and private clear.

# What you run next

Create the catalog and schemas. Set up Auto Loader paths. Backfill EIA 930 and NOAA for one BA. Build features. Train one model. Wire the app. Prove a day ahead forecast. Add scenarios. Expand across areas once the loop holds.
