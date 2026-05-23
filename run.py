#!/usr/bin/env python3
"""Flask app entry point. Run locally: python run.py"""

from __future__ import annotations

import logging
import os
import sys

from app import create_app

logger = logging.getLogger(__name__)
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_PORT = 3000


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def resolve_port(argv: list[str]) -> int:
    """Resolve listen port from argv, PORT, or FLASK_PORT."""
    if len(argv) > 1 and argv[1].startswith("--port"):
        try:
            if "=" in argv[1]:
                return int(argv[1].split("=", 1)[1])
            return int(argv[2])
        except (IndexError, ValueError):
            return DEFAULT_PORT
    return int(os.getenv("PORT", os.getenv("FLASK_PORT", DEFAULT_PORT)))


app = create_app()

if __name__ == "__main__":
    configure_logging()
    port = resolve_port(sys.argv)
    data_dir = os.getenv("LEAP_DATA_DIR", "data/cache")
    logger.info("LEAP - Load Estimation and Planning")
    logger.info("Server URL: http://0.0.0.0:%s", port)
    logger.info("Dashboard: http://0.0.0.0:%s/", port)
    logger.info("API base: http://0.0.0.0:%s/api", port)
    logger.info("Data directory: %s", data_dir)
    app.run(debug=True, host="0.0.0.0", port=port)
