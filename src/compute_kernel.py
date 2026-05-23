"""Pure Python/numpy SAIDI/SAIFI on flat arrays (grouped by single key)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def saidi_saifi_by_key(
    group_key: np.ndarray,
    customers_out: np.ndarray,
    slot_minutes: np.ndarray,
    customers_served: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    df = pd.DataFrame(
        {
            "key": group_key,
            "customers_out": customers_out,
            "slot_minutes": slot_minutes,
            "customers_served": customers_served,
        }
    )
    g = df.groupby("key", as_index=False).agg(
        cust_min=("customers_out", lambda s: (s * df.loc[s.index, "slot_minutes"]).sum()),
        cust_int=("customers_out", "sum"),
        cust_served=("customers_served", "sum"),
    )
    saidi = g["cust_min"] / g["cust_served"]
    saifi = g["cust_int"] / g["cust_served"]
    return g["key"].to_numpy(), saidi.to_numpy(), saifi.to_numpy()
