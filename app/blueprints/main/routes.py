"""
Main blueprint routes for web pages.
"""

from flask import jsonify, render_template, current_app, request
from . import bp
from ...services.leap_db import LEAPDatabaseService


@bp.route("/")
def index():
    """Render the LEAP home page with map and charts."""
    # Get available balancing authorities for dropdown
    try:
        leap_db = LEAPDatabaseService(current_app)
        areas = leap_db.get_balancing_authorities()
    except Exception:
        areas = []

    return render_template("leap_dashboard.html", areas=areas)


@bp.route("/leap")
def leap_dashboard():
    """Render the main LEAP dashboard."""
    # Get available balancing authorities for dropdown
    try:
        leap_db = LEAPDatabaseService(current_app)
        areas = leap_db.get_balancing_authorities()
    except Exception:
        areas = []

    return render_template("leap_dashboard.html", areas=areas)


@bp.route("/leap/area/<ba>")
def leap_area_detail(ba: str):
    """Render detailed view for a specific balancing authority."""
    try:
        leap_db = LEAPDatabaseService(current_app)

        # Get basic info
        areas = leap_db.get_balancing_authorities()
        area_info = next((a for a in areas if a["ba"] == ba), {"ba": ba, "name": ba})

        # Get recent load data for initial chart
        load_data = leap_db.get_load_data(ba, limit=168) # 1 week

        # Get model metrics
        metrics = leap_db.get_model_metrics(ba)

    except Exception as e:
        area_info = {"ba": ba, "name": ba}
        load_data = []
        metrics = []

    return render_template("leap_area_detail.html",
        area=area_info,
        load_data=load_data,
        metrics=metrics)


@bp.route("/leap/scenarios")
def leap_scenarios():
    """Render scenario planning interface."""
    try:
        leap_db = LEAPDatabaseService(current_app)
        areas = leap_db.get_balancing_authorities()
    except Exception:
        areas = []

    return render_template("leap_scenarios.html", areas=areas)


@bp.route("/health")
def health():
    """Health check endpoint.

    Returns:
        dict: Health status information.
    """
    return jsonify({"status": "healthy"})
