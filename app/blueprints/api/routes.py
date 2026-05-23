"""
API blueprint routes for REST endpoints.
"""

from flask import jsonify, request, current_app
from . import bp
from ...services.leap_db import LEAPDatabaseService

from ...services.forecast_service import ForecastService


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@bp.route("/health")
def api_health():
    """Detailed health check."""
    from pathlib import Path

    data_dir = Path(current_app.config.get("LEAP_DATA_DIR", "data/cache"))
    return jsonify({
        "status": "healthy",
        "data_dir": str(data_dir),
        "load_cache_present": (data_dir / "load_hourly.parquet").is_file(),
    })


# ---------------------------------------------------------------------------
# Load & Forecasting
# ---------------------------------------------------------------------------

@bp.route("/leap/areas")
def leap_areas():
    """List available balancing authorities."""
    try:
        leap_db = LEAPDatabaseService(current_app)
        areas = leap_db.get_balancing_authorities()
        return jsonify({"areas": areas, "count": len(areas)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/load/<ba>")
def leap_load_data(ba: str):
    """Historical hourly load for a BA."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        limit = int(request.args.get("limit", 1000))

        leap_db = LEAPDatabaseService(current_app)
        load_data = leap_db.get_load_data(ba, start_date, end_date, limit)

        return jsonify({"ba": ba, "data": load_data, "count": len(load_data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/forecast/<ba>")
def leap_forecast(ba: str):
    """Generate load forecast for a BA."""
    try:
        horizon = int(request.args.get("horizon", 24))
        model_type = request.args.get("model", "lightgbm")
        scenario_id = request.args.get("scenario", "baseline")

        leap_db = LEAPDatabaseService(current_app)
        forecast_service = ForecastService(leap_db)

        forecast_data = forecast_service.generate_forecast(
            ba=ba, horizon_hours=horizon,
            model_type=model_type, scenario_id=scenario_id
        )
        return jsonify({
            "ba": ba, "horizon_hours": horizon,
            "model_type": model_type, "scenario_id": scenario_id,
            "forecast": forecast_data, "count": len(forecast_data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/scenarios/<ba>")
def leap_scenarios(ba: str):
    """Compare scenario forecasts for a BA."""
    try:
        horizon = int(request.args.get("horizon", 24))
        scenario_list = request.args.get("scenarios", "baseline,high_growth,hot_weather,demand_response").split(",")

        leap_db = LEAPDatabaseService(current_app)
        forecast_service = ForecastService(leap_db)

        results = {}
        for sid in scenario_list:
            sid = sid.strip()
            results[sid] = forecast_service.generate_forecast(
                ba=ba, horizon_hours=horizon,
                model_type="lightgbm", scenario_id=sid
            )
        return jsonify({"ba": ba, "horizon_hours": horizon, "scenarios": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/features/<ba>")
def leap_features(ba: str):
    """Engineered features for a BA."""
    try:
        limit = int(request.args.get("limit", 1000))
        leap_db = LEAPDatabaseService(current_app)
        features = leap_db.get_features(ba, limit)
        return jsonify({"ba": ba, "features": features, "count": len(features)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/metrics/<ba>")
def leap_metrics(ba: str):
    """Model performance metrics for a BA."""
    try:
        model_name = request.args.get("model", "lightgbm")
        leap_db = LEAPDatabaseService(current_app)
        metrics = leap_db.get_model_metrics(ba, model_name)
        return jsonify({"ba": ba, "model_name": model_name, "metrics": metrics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/export/<ba>")
def leap_export_data(ba: str):
    """Export forecast as CSV."""
    try:
        import pandas as pd
        import io
        from flask import Response

        horizon = int(request.args.get("horizon", 24))
        scenario_id = request.args.get("scenario", "baseline")

        leap_db = LEAPDatabaseService(current_app)
        forecast_service = ForecastService(leap_db)

        forecast_data = forecast_service.generate_forecast(
            ba=ba, horizon_hours=horizon,
            model_type="lightgbm", scenario_id=scenario_id
        )

        df = pd.DataFrame(forecast_data)
        output = io.StringIO()
        df.to_csv(output, index=False)

        return Response(
            output.getvalue(), mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=leap_forecast_{ba}_{scenario_id}.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

@bp.route("/leap/weather")
def leap_weather():
    """Hourly weather for a BA."""
    try:
        ba = request.args.get("ba", "CAL-ALL")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        limit = int(request.args.get("limit", 1000))

        leap_db = LEAPDatabaseService(current_app)
        weather_data = leap_db.get_weather_data(ba, start_date, end_date, limit)

        return jsonify({"ba": ba, "data": weather_data, "count": len(weather_data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Outage-Weather Correlation
# ---------------------------------------------------------------------------

@bp.route("/leap/outage-correlation")
def outage_weather_correlation():
    """Outage events with weather context."""
    try:
        ba = request.args.get("ba")
        severity = request.args.get("severity")
        limit = int(request.args.get("limit", 500))

        leap_db = LEAPDatabaseService(current_app)
        data = leap_db.get_outage_correlation(ba, severity, limit)

        return jsonify({"data": data, "count": len(data),
                        "filters": {"ba": ba, "severity": severity, "limit": limit}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/outage-correlation/summary")
def outage_correlation_summary():
    """Aggregated outage stats by cause, severity, and BA."""
    try:
        leap_db = LEAPDatabaseService(current_app)
        summary = leap_db.get_outage_correlation_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/outage-correlation/timeline/<ba>")
def outage_correlation_timeline(ba: str):
    """Time series of outages + weather for charting."""
    try:
        limit = int(request.args.get("limit", 1000))
        leap_db = LEAPDatabaseService(current_app)
        timeline = leap_db.get_outage_correlation_timeline(ba, limit)
        return jsonify({"ba": ba, "data": timeline, "count": len(timeline)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# ERCOT 4CP
# ---------------------------------------------------------------------------

@bp.route("/leap/4cp/summary")
def fourcp_summary():
    """4CP analysis capability overview."""
    try:
        from ...services.fourcp_service import FourCPService
        leap_db = LEAPDatabaseService(current_app)
        svc = FourCPService(leap_db)
        return jsonify(svc.get_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/4cp/dates")
def fourcp_historical_dates():
    """All historical 4CP dates (1996-2025)."""
    try:
        from ...services.fourcp_service import FourCPService
        leap_db = LEAPDatabaseService(current_app)
        svc = FourCPService(leap_db)
        dates = svc.get_historical_dates()
        return jsonify({"dates": dates, "count": len(dates)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/4cp/score/<date>")
def fourcp_score_day(date: str):
    """Score a specific day for 4CP risk."""
    try:
        from ...services.fourcp_service import FourCPService
        leap_db = LEAPDatabaseService(current_app)
        svc = FourCPService(leap_db)
        result = svc.score_day(date)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/4cp/summer/<int:year>")
def fourcp_summer_scores(year: int):
    """Full summer season risk timeline."""
    try:
        from ...services.fourcp_service import FourCPService
        leap_db = LEAPDatabaseService(current_app)
        svc = FourCPService(leap_db)
        scores = svc.score_summer_range(year)
        return jsonify({
            "year": year, "scores": scores, "count": len(scores),
            "high_risk_days": len([s for s in scores if s.get("risk", 0) >= 0.65]),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Engineering Analysis
# ---------------------------------------------------------------------------

@bp.route("/leap/engineering/storm-warnings")
def storm_warnings():
    """Severe weather alerts + demand impact for a BA."""
    try:
        from ...services.storm_warning_service import StormWarningService

        ba = request.args.get("ba", "TEX-ALL")
        ba_coords = {
            "CAL-ALL": (37.0, -120.0), "TEX-ALL": (31.0, -99.0),
            "PJM-ALL": (40.0, -78.0), "MISO-ALL": (42.0, -89.0),
            "NYIS-ALL": (43.0, -75.0), "ISNE-ALL": (42.4, -71.1),
            "SWPP-ALL": (37.0, -97.0),
        }
        lat = float(request.args.get("lat", ba_coords.get(ba, (39.8, -98.6))[0]))
        lon = float(request.args.get("lon", ba_coords.get(ba, (39.8, -98.6))[1]))

        svc = StormWarningService()
        alerts = svc.get_active_alerts(lat, lon, radius_miles=50)
        summary = svc.get_alert_summary(alerts)
        demand_impact = svc.calculate_demand_impact(alerts)

        return jsonify({"ba": ba, "coordinates": {"lat": lat, "lon": lon},
                        "alerts": alerts, "summary": summary, "demand_impact": demand_impact})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/engineering/powerflow", methods=["POST"])
def powerflow_analysis():
    """Newton-Raphson AC power flow analysis."""
    try:
        from ...services.powerflow_service import PowerFlowService
        import pandas as pd

        data = request.get_json() or {}
        bus_data = data.get("bus_data")
        line_data = data.get("line_data")
        load_forecast = data.get("load_forecast")

        if not all([bus_data, line_data, load_forecast]):
            return jsonify({"error": "bus_data, line_data, and load_forecast required"}), 400

        pf = PowerFlowService()
        result = pf.newton_raphson_powerflow(bus_data, line_data, pd.DataFrame(load_forecast))
        return jsonify({"powerflow_analysis": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/engineering/load-characterization/<ba>")
def load_characterization(ba: str):
    """Load profile characterization (power factor, diversity, LDC)."""
    try:
        from ...services.load_modeling_service import LoadModelingService
        import pandas as pd

        load_type = request.args.get("load_type", "mixed")

        leap_db = LEAPDatabaseService(current_app)
        load_data = leap_db.get_load_data(ba, limit=2160)

        if not load_data:
            return jsonify({"error": f"No load data for {ba}"}), 404

        df = pd.DataFrame(load_data)
        df["consumption_value"] = df["mw"]
        df.index = pd.to_datetime(df["ts_utc"])

        svc = LoadModelingService()
        result = svc.characterize_load_profile(df, load_type)

        return jsonify({"ba": ba, "load_type": load_type, "characterization": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/engineering/stability-analysis", methods=["POST"])
def stability_analysis():
    """System stability analysis (frequency, inertia, voltage, transient)."""
    try:
        from ...services.power_system_service import PowerSystemService
        import pandas as pd

        data = request.get_json() or {}
        ba = data.get("ba", "TEX-ALL")
        load_forecast = data.get("load_forecast")
        system_data = data.get("system_data", {})

        if not load_forecast:
            leap_db = LEAPDatabaseService(current_app)
            load_data = leap_db.get_load_data(ba, limit=168)
            load_df = pd.DataFrame(load_data)
        else:
            load_df = pd.DataFrame(load_forecast)

        pss = PowerSystemService()
        result = pss.analyze_system_stability(load_df, system_data)
        return jsonify({"ba": ba, "stability_analysis": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/engineering/contingency-analysis", methods=["POST"])
def contingency_analysis():
    """N-1 contingency testing."""
    try:
        from ...services.powerflow_service import PowerFlowService

        data = request.get_json() or {}
        base_case = data.get("base_case")
        contingency_list = data.get("contingency_list", [])

        if not base_case:
            return jsonify({"error": "base_case required"}), 400

        pf = PowerFlowService()
        result = pf.contingency_analysis(base_case, contingency_list)
        return jsonify({"contingency_analysis": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/engineering/renewable-integration", methods=["POST"])
def renewable_integration():
    """Renewable energy integration impact on grid stability."""
    try:
        from ...services.power_system_service import PowerSystemService
        import pandas as pd

        data = request.get_json() or {}
        ba = data.get("ba", "TEX-ALL")
        load_forecast = data.get("load_forecast")
        renewable_forecast = data.get("renewable_forecast")
        system_data = data.get("system_data", {})

        if not all([load_forecast, renewable_forecast]):
            return jsonify({"error": "load_forecast and renewable_forecast required"}), 400

        pss = PowerSystemService()
        result = pss.analyze_renewable_integration_impact(
            pd.DataFrame(load_forecast), pd.DataFrame(renewable_forecast), system_data)
        return jsonify({"ba": ba, "renewable_integration_analysis": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Reliability Metrics (SAIDI / SAIFI / CAIDI)
# ---------------------------------------------------------------------------

@bp.route("/leap/reliability/metrics")
def reliability_metrics():
    """Compute SAIDI, SAIFI, and CAIDI from outage data."""
    try:
        from ...services.reliability import saidi, saifi, caidi_from_saidi_saifi, with_duration_minutes
        import pandas as pd

        ba = request.args.get("ba")
        group_by = request.args.get("group_by", "ba")

        leap_db = LEAPDatabaseService(current_app)
        outage_data = leap_db.get_outage_correlation(ba=ba, limit=50000)

        if not outage_data:
            return jsonify({"error": "No outage data available"}), 404

        df = pd.DataFrame(outage_data)
        df["timestamp"] = pd.to_datetime(df["ts_utc"])
        df["customers_served"] = df.get("total_customers", 500000)
        df = with_duration_minutes(df)

        level = [group_by] if group_by in df.columns else ["ba"]

        saidi_df = saidi(df, level)
        saifi_df = saifi(df, level)
        caidi_df = caidi_from_saidi_saifi(saidi_df, saifi_df, on=level)

        result = caidi_df.where(caidi_df.notna(), None).to_dict("records")
        return jsonify({"metrics": result, "count": len(result), "group_by": group_by})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/reliability/benchmarks")
def reliability_benchmarks():
    """EIA national reliability benchmarks for peer comparison."""
    try:
        from ...services.reliability import get_eia_benchmarks
        benchmarks = get_eia_benchmarks()
        result = benchmarks.where(benchmarks.notna(), None).to_dict("records")
        return jsonify({"benchmarks": result, "count": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/reliability/priority")
def reliability_priority():
    """Rank counties by outage priority score."""
    try:
        from ...services.reliability import score_county
        import pandas as pd

        ba = request.args.get("ba")
        w_out = float(request.args.get("w_out", 0.5))
        w_crit = float(request.args.get("w_crit", 0.3))
        w_vuln = float(request.args.get("w_vuln", 0.2))

        leap_db = LEAPDatabaseService(current_app)
        outage_data = leap_db.get_outage_correlation(ba=ba, limit=50000)

        if not outage_data:
            return jsonify({"error": "No outage data available"}), 404

        df = pd.DataFrame(outage_data)
        df["county_fips"] = df.get("fips_code", df.get("county", "unknown"))
        df["svi_score"] = 0.5

        ranked = score_county(df, w_out=w_out, w_crit=w_crit, w_vuln=w_vuln)
        result = ranked.head(50).to_dict("records")

        return jsonify({"priorities": result, "count": len(result),
                        "weights": {"w_out": w_out, "w_crit": w_crit, "w_vuln": w_vuln}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/leap/reliability/alerts")
def reliability_alerts():
    """Check for SAIDI/SAIFI threshold breaches."""
    try:
        from ...services.reliability import saidi, saifi, breaches_saidi, breaches_saifi, with_duration_minutes
        import pandas as pd

        ba = request.args.get("ba")
        saidi_thresh = float(request.args.get("saidi_threshold", 120))
        saifi_thresh = float(request.args.get("saifi_threshold", 1.5))

        leap_db = LEAPDatabaseService(current_app)
        outage_data = leap_db.get_outage_correlation(ba=ba, limit=50000)

        if not outage_data:
            return jsonify({"breaches": [], "count": 0})

        df = pd.DataFrame(outage_data)
        df["timestamp"] = pd.to_datetime(df["ts_utc"])
        df["customers_served"] = df.get("total_customers", 500000)
        df["date"] = df["timestamp"].dt.date.astype(str)
        df = with_duration_minutes(df)

        level = ["ba", "date"]
        saidi_df = saidi(df, level)
        saifi_df = saifi(df, level)

        saidi_b = breaches_saidi(saidi_df, saidi_thresh)
        saifi_b = breaches_saifi(saifi_df, saifi_thresh)

        return jsonify({
            "saidi_breaches": saidi_b.to_dict("records"),
            "saifi_breaches": saifi_b.to_dict("records"),
            "thresholds": {"saidi_min": saidi_thresh, "saifi_events": saifi_thresh},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@bp.route("/leap/config")
def get_leap_config():
    """Application configuration."""
    from pathlib import Path

    data_dir = Path(current_app.config.get("LEAP_DATA_DIR", "data/cache"))
    return jsonify({
        "data_dir": str(data_dir),
        "load_cache_present": (data_dir / "load_hourly.parquet").is_file(),
    })
