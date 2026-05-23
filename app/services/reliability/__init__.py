"""
Utility reliability metrics: SAIDI, SAIFI, CAIDI.
Adapted from the SAIDI app for LEAP's outage data.

- metrics.py: SAIDI/SAIFI/CAIDI computation
- processing.py: outage resampling, windowing, slot durations
- priority.py: county/feeder priority scoring (customers × critical × SVI)
- rules.py: threshold breach detection + alerting
- eia_benchmarks.py: EIA national reliability benchmarks for peer comparison
"""
from .metrics import saidi, saifi, caidi_from_saidi_saifi
from .processing import resample_outages, window, with_duration_minutes
from .priority import score_county, score_feeder
from .rules import breaches_saidi, breaches_saifi
from .eia_benchmarks import get_eia_benchmarks

__all__ = [
    "saidi", "saifi", "caidi_from_saidi_saifi",
    "resample_outages", "window", "with_duration_minutes",
    "score_county", "score_feeder",
    "breaches_saidi", "breaches_saifi",
    "get_eia_benchmarks",
]
