#!/usr/bin/env python3
"""Seed local parquet cache with synthetic hourly load for all balancing authorities."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.local_data import BA_PROFILES, persist_synthetic_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("leap-seed")


def main() -> None:
    logger.info("Generating synthetic load for %s balancing authorities", len(BA_PROFILES))
    path = persist_synthetic_cache()
    logger.info("Done. Cache written to %s", path)


if __name__ == "__main__":
    main()
