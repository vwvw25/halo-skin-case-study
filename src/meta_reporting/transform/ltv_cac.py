"""LTV:CAC ratio and payback period by acquisition segment.

Joins the projected 12-month CM-LTV per cohort (from :mod:`cohorts`) to the CAC per segment
(from :mod:`spend`), aggregating cohorts into a single per-segment view weighted by cohort size.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from meta_reporting.domain import LTV_HORIZON_MONTHS
from meta_reporting.transform.cohorts import MaturationCurve


def ltv_cac_by_segment(
    cohort_ltv: pd.DataFrame,
    spend_and_cac: pd.DataFrame,
    curve: MaturationCurve,
    *,
    by: str,
) -> pd.DataFrame:
    """One row per segment: blended CAC, 12-month CM-LTV, LTV:CAC ratio, payback months."""
    ltv = (
        cohort_ltv.assign(_w=cohort_ltv["cohort_size"])
        .groupby(by)
        .apply(
            lambda g: pd.Series(
                {
                    "cohorts": len(g),
                    "customers": g["cohort_size"].sum(),
                    "cm_ltv_12": np.average(g["projected_cm_per_customer"], weights=g["_w"]),
                    "realized_share": (g["maturity"] == "realized").mean(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )

    cac = (
        spend_and_cac.groupby(by)
        .apply(
            lambda g: pd.Series(
                {
                    "spend": g["spend"].sum(),
                    "new_customers": g["new_customers"].sum(),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    cac["cac"] = np.where(cac["new_customers"] > 0, cac["spend"] / cac["new_customers"], np.nan)

    out = ltv.merge(cac, on=by, how="left")
    out["ltv_cac"] = out["cm_ltv_12"] / out["cac"]
    out["payback_months"] = out.apply(lambda r: _payback(curve, r["cac"], r["cm_ltv_12"]), axis=1)
    return out.sort_values("ltv_cac", ascending=False).reset_index(drop=True)


def _payback(curve: MaturationCurve, cac: float, cm_ltv_12: float) -> float:
    """Months until cumulative CM per customer covers CAC, scaling the curve to this segment."""
    if not np.isfinite(cac) or cm_ltv_12 <= 0:
        return float("nan")
    scale = cm_ltv_12 / curve.horizon_value if curve.horizon_value > 0 else 1.0
    for month in range(0, LTV_HORIZON_MONTHS + 1):
        if curve.at(month) * scale >= cac:
            return float(month)
    return float("nan")  # not recovered within the horizon
