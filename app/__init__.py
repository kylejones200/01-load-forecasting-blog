"""Flask app factory."""

from __future__ import annotations

import os

from flask import Flask

from .blueprints.api import bp as api_bp
from .blueprints.main import bp as main_bp


def create_app() -> Flask:
    """Create and configure the LEAP Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
    app.config["LEAP_DATA_DIR"] = os.getenv("LEAP_DATA_DIR", "data/cache")

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app
