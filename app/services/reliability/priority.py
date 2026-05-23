"""Prioritization scoring for counties and feeders."""

from __future__ import annotations

import pandas as pd


def _nz(s: pd.Series) -> pd.Series:
    x = s.fillna(0)
    rng = x.max() - x.min()
    return (x - x.min()) / (rng if rng > 0 else 1)


def score_county(
    df: pd.DataFrame,
    w_out: float = 0.5,
    w_crit: float = 0.3,
    w_vuln: float = 0.2,
) -> pd.DataFrame:
    """County priority scores from customers_out, critical_out, svi_score."""
    tmp = df.groupby("county_fips", as_index=False).agg(
        customers_out=("customers_out", "sum"),
        critical_out=(
            ("critical_out", "sum")
            if "critical_out" in df.columns
            else ("customers_out", "sum")
        ),
        svi_score=("svi_score", "mean"),
    )
    s_out = _nz(tmp["customers_out"])
    s_crit = _nz(tmp["critical_out"])
    s_vuln = tmp["svi_score"].fillna(tmp["svi_score"].mean())
    tmp["priority_score"] = w_out * s_out + w_crit * s_crit + w_vuln * s_vuln
    return tmp.sort_values("priority_score", ascending=False).reset_index(drop=True)


def score_feeder(
    df: pd.DataFrame,
    w_out: float = 0.5,
    w_crit: float = 0.3,
    w_vuln: float = 0.2,
) -> pd.DataFrame:
    """Feeder priority scores from customers_out, critical_out, svi_score."""
    tmp = df.groupby("feeder_id", as_index=False).agg(
        customers_out=("customers_out", "sum"),
        critical_out=(
            ("critical_out", "sum")
            if "critical_out" in df.columns
            else ("customers_out", "sum")
        ),
        svi_score=("svi_score", "mean"),
    )
    s_out = _nz(tmp["customers_out"])
    s_crit = _nz(tmp["critical_out"])
    s_vuln = tmp["svi_score"].fillna(tmp["svi_score"].mean())
    tmp["priority_score"] = w_out * s_out + w_crit * s_crit + w_vuln * s_vuln
    return tmp.sort_values("priority_score", ascending=False).reset_index(drop=True)
