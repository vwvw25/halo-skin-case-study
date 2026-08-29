"""Target-cohort membership and capture rate by acquisition segment.

The target cohort (see :mod:`meta_reporting.domain`) is Halo Skin's high-value customer, judged
on their first 90 days. That means:

* customers acquired **90+ days** before the report date have a *realized* verdict;
* younger customers get a *predicted* probability from a transparent lookup — the realized
  target rate of matured customers who showed the same first-30-day behaviour (order count
  bucket x bought-premium). No fitted model, same spirit as the maturation curve.

``capture_rate`` rolls both up per segment so the weekly report can show a predicted capture
rate and the monthly report the realized one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from meta_reporting import domain
from meta_reporting.transform.cohorts import SEGMENT_COLUMN


def classify_customers(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """One row per customer with realized / predicted target-cohort membership.

    Columns: ``customer_id``, segment columns, ``matured`` (bool), ``is_target`` (bool, NaN
    until matured), ``predicted_prob`` (0..1), ``target`` (is_target where matured else
    predicted_prob rounded).
    """
    firsts = orders.groupby("customer_id")["order_date"].min().rename("acq")
    work = orders.merge(firsts, on="customer_id")
    work["day"] = (work["order_date"] - work["acq"]).dt.days

    in_window = work[work["day"] <= domain.TARGET_WINDOW_DAYS]
    in_early = work[work["day"] <= domain.TARGET_EARLY_SIGNAL_DAYS]

    per_customer = pd.DataFrame({"acq": firsts})
    per_customer["orders_90d"] = in_window.groupby("customer_id").size()
    per_customer["revenue_90d"] = in_window.groupby("customer_id")["net_revenue"].sum()
    per_customer["premium_90d"] = in_window.groupby("customer_id")["has_premium"].any()
    per_customer["orders_30d"] = in_early.groupby("customer_id").size()
    per_customer["premium_30d"] = in_early.groupby("customer_id")["has_premium"].any()
    per_customer = per_customer.fillna(
        {
            "orders_90d": 0,
            "revenue_90d": 0.0,
            "premium_90d": False,
            "orders_30d": 0,
            "premium_30d": False,
        }
    )

    per_customer["aov_90d"] = np.where(
        per_customer["orders_90d"] > 0,
        per_customer["revenue_90d"] / per_customer["orders_90d"].replace(0, np.nan),
        0.0,
    )
    per_customer["matured"] = (as_of - per_customer["acq"]).dt.days >= domain.TARGET_WINDOW_DAYS
    per_customer["is_target"] = (
        (per_customer["orders_90d"] >= domain.TARGET_MIN_ORDERS)
        & (per_customer["aov_90d"] >= domain.TARGET_MIN_AOV)
        & (per_customer["premium_90d"] | (not domain.TARGET_REQUIRE_PREMIUM_SKU))
    )

    lookup = _early_signal_lookup(per_customer)
    per_customer["_bucket"] = _bucket(per_customer)
    per_customer["predicted_prob"] = per_customer["_bucket"].map(lookup).fillna(lookup.mean())

    out = customers.merge(
        per_customer.drop(columns=["acq", "_bucket"]),
        left_on="customer_id",
        right_index=True,
        how="left",
    )
    out["target"] = np.where(out["matured"], out["is_target"], out["predicted_prob"])
    return out


def capture_rate(classified: pd.DataFrame, *, by: str | None = None) -> pd.DataFrame:
    """Per segment: matured/immature counts, realized and predicted target-cohort capture."""
    seg = SEGMENT_COLUMN[by] if by else None
    keys = [seg] if seg else []

    def _agg(group: pd.DataFrame) -> pd.Series:
        matured = group[group["matured"]]
        immature = group[~group["matured"]]
        realized = matured["is_target"].mean() if len(matured) else np.nan
        predicted = immature["predicted_prob"].mean() if len(immature) else np.nan
        blended_hits = matured["is_target"].sum() + immature["predicted_prob"].sum()
        return pd.Series(
            {
                "customers": len(group),
                "matured": len(matured),
                "realized_capture_rate": realized,
                "predicted_capture_rate": predicted,
                "blended_capture_rate": blended_hits / len(group) if len(group) else np.nan,
            }
        )

    if not keys:
        return _agg(classified).to_frame().T.reset_index(drop=True)
    return classified.groupby(keys).apply(_agg, include_groups=False).reset_index()


def _bucket(frame: pd.DataFrame) -> pd.Series:
    orders_bucket = frame["orders_30d"].clip(upper=3).astype(int)
    return orders_bucket.astype(str) + "|" + frame["premium_30d"].astype(bool).astype(str)


def _early_signal_lookup(per_customer: pd.DataFrame) -> pd.Series:
    matured = per_customer[per_customer["matured"]].copy()
    matured["_bucket"] = _bucket(matured)
    return matured.groupby("_bucket")["is_target"].mean()
