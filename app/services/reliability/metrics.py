"""Reliability metrics: SAIDI, SAIFI, and CAIDI."""

import pandas as pd


def saidi(df: pd.DataFrame, level: list[str]) -> pd.DataFrame:
    """Compute SAIDI (minutes per customer) for the given grouping."""
    g = df.groupby(level, dropna=False, as_index=False).agg(
        cust_min=(
            "customers_out",
            lambda s: (s * df.loc[s.index, "slot_minutes"]).sum(),
        ),
        cust_served=("customers_served", "sum"),
    )
    g["SAIDI_min"] = g["cust_min"] / g["cust_served"]
    return g[level + ["SAIDI_min"]]


def saifi(df: pd.DataFrame, level: list[str]) -> pd.DataFrame:
    """Compute SAIFI (interruptions per customer) for the given grouping."""
    g = df.groupby(level, dropna=False, as_index=False).agg(
        cust_int=("customers_out", "sum"),
        cust_served=("customers_served", "sum"),
    )
    g["SAIFI_events_per_cust"] = g["cust_int"] / g["cust_served"]
    return g[level + ["SAIFI_events_per_cust"]]


def caidi_from_saidi_saifi(
    saidi_df: pd.DataFrame, saifi_df: pd.DataFrame, on: list[str]
) -> pd.DataFrame:
    """Derive CAIDI (average interruption duration) from SAIDI and SAIFI."""
    m = saidi_df.merge(saifi_df, on=on, how="inner")
    m["CAIDI_min_per_event"] = m["SAIDI_min"] / m["SAIFI_events_per_cust"].replace(
        0, pd.NA
    )
    return m
