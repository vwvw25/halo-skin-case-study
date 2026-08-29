"""Monthly acquisition cohorts, the repeat-purchase maturation curve, and CM-LTV.

The problem: a 12-month contribution-margin LTV takes 12 months to observe, but most cohorts
are younger than that. The approach here is deliberately transparent (no parametric retention
model):

1. **Maturation curve** — pool *every* customer by tenure (months since first order) and take
   the mean cumulative CM per customer at each tenure month. This uses the whole order history,
   not just fully-mature cohorts. Past the last well-observed tenure the curve is extended by
   the average of the last few monthly increments, decayed — the tail of a repeat-purchase
   curve is small, so a rough estimate there barely moves the 12-month number.

2. **Per-cohort projection** — a cohort observed to age *t* with realized CM *c* is projected to
   ``c * curve(12) / curve(t)``. Multiplicative, so a cohort that over- or under-indexes on
   value keeps that through the projection. Cohorts already 12 months old are reported as
   realized, no projection.

Everything is reported as realized **and** projected so the extrapolation is visible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from meta_reporting.domain import LTV_HORIZON_MONTHS

# canonical segment name -> the column on the customers frame
SEGMENT_COLUMN = {
    "strategy": "acquisition_strategy",
    "campaign": "acquisition_campaign_id",
    "age": "age",
    "gender": "gender",
    "region": "region",
}


def _month_index(start: pd.Series, end: pd.Series) -> pd.Series:
    """Whole months from ``start`` to ``end`` (0 = same calendar month)."""
    return (end.dt.year - start.dt.year) * 12 + (end.dt.month - start.dt.month)


@dataclass(frozen=True, slots=True)
class MaturationCurve:
    """Cumulative CM per customer by tenure month, 0..horizon."""

    cum_cm: pd.Series  # index: tenure month (int), value: cumulative CM per customer
    last_observed_month: int

    def at(self, month: int) -> float:
        m = max(0, min(int(month), int(self.cum_cm.index.max())))
        return float(self.cum_cm.loc[m])

    @property
    def horizon_value(self) -> float:
        return self.at(int(self.cum_cm.index.max()))


def maturation_curve(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
    horizon: int = LTV_HORIZON_MONTHS,
    min_customers_per_month: int = 150,
) -> MaturationCurve:
    first_order = orders.groupby("customer_id")["order_date"].min().rename("first_order_date")
    joined = orders.merge(first_order, on="customer_id")
    joined["tenure"] = _month_index(joined["first_order_date"], joined["order_date"])
    joined["observable"] = _month_index(
        joined["first_order_date"], pd.Series(as_of, index=joined.index)
    )

    # CM booked at each tenure month, per customer, only counting customers old enough to have
    # been observable at that tenure
    per_month_cm = joined.groupby(["customer_id", "tenure"])["contribution_margin"].sum()
    max_tenure = int(joined["observable"].max())
    rows: list[tuple[int, float]] = []
    customer_first = first_order.to_frame().assign(
        observable=lambda d: _month_index(d["first_order_date"], pd.Series(as_of, index=d.index))
    )
    for tenure in range(max_tenure + 1):
        eligible = customer_first.index[customer_first["observable"] >= tenure]
        if len(eligible) < min_customers_per_month:
            break
        cm_at_tenure = (
            per_month_cm.reindex(
                pd.MultiIndex.from_product([eligible, [tenure]], names=["customer_id", "tenure"])
            )
            .fillna(0.0)
            .sum()
        )
        rows.append((tenure, cm_at_tenure / len(eligible)))

    incremental = pd.Series({t: v for t, v in rows}).sort_index()
    cum = incremental.cumsum()
    last_observed = int(cum.index.max())

    if last_observed < horizon:
        tail_step = float(incremental.iloc[-3:].mean())
        value = float(cum.iloc[-1])
        for month in range(last_observed + 1, horizon + 1):
            tail_step *= 0.8
            value += tail_step
            cum.loc[month] = value

    cum = cum.loc[:horizon].astype(float)
    return MaturationCurve(cum_cm=cum, last_observed_month=last_observed)


def cohort_ltv(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    curve: MaturationCurve,
    *,
    as_of: pd.Timestamp,
    by: str | None = None,
    horizon: int = LTV_HORIZON_MONTHS,
) -> pd.DataFrame:
    """One row per acquisition-month (x segment): cohort size, realized + projected CM-LTV.

    ``by`` is a canonical segment name (``strategy`` / ``campaign`` / ``age`` / ...); the output
    carries a column of that name.
    """
    seg_col = SEGMENT_COLUMN[by] if by else None
    cust = customers[["customer_id", "acquisition_month", *([seg_col] if seg_col else [])]].copy()
    if seg_col and seg_col != by:
        cust = cust.rename(columns={seg_col: by})

    order_cm = orders.merge(cust, on="customer_id").assign(
        age=lambda d: _month_index(d["acquisition_month"], d["order_date"]),
    )
    order_cm = order_cm[order_cm["age"] <= horizon]

    group_cols = ["acquisition_month", *([by] if by else [])]
    realized_cm = order_cm.groupby(group_cols)["contribution_margin"].sum().rename("realized_cm")
    size = cust.groupby(group_cols).size().rename("cohort_size")

    out = pd.concat([size, realized_cm], axis=1).reset_index()
    out["realized_cm"] = out["realized_cm"].fillna(0.0)
    out["observed_age_months"] = _month_index(
        out["acquisition_month"], pd.Series(as_of, index=out.index)
    ).clip(lower=0, upper=horizon)

    out["realized_cm_per_customer"] = out["realized_cm"] / out["cohort_size"]
    out["projection_factor"] = out["observed_age_months"].map(
        lambda t: curve.horizon_value / curve.at(t) if curve.at(t) > 0 else np.nan
    )
    out["projected_cm_per_customer"] = np.where(
        out["observed_age_months"] >= horizon,
        out["realized_cm_per_customer"],
        out["realized_cm_per_customer"] * out["projection_factor"],
    )
    out["maturity"] = np.where(out["observed_age_months"] >= horizon, "realized", "projected")
    return out.sort_values(group_cols).reset_index(drop=True)
