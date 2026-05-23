"""
ERCOT Four Coincident Peak (4CP) scoring service.
Embeds the 4CP engine from the standalone project to provide
real-time 4CP risk scoring within LEAP.
"""
from .engine import FourCPEngine, RuleConfig, build_daily_table

__all__ = ["FourCPEngine", "RuleConfig", "build_daily_table"]
