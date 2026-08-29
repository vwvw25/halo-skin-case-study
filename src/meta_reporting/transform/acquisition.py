"""Weekly acquisition topline for the operational report.

Everything here matures fast enough to compare week over week: spend, delivery, acquired
customers, first-order contribution margin, and the 30-day repeat rate (only for weeks old
enough to have observed 30 days).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from meta_reporting.domain import TARGET_EARLY_SIGNAL_DAYS


def weekly_topline(
    meta_daily: pd.DataFrame,
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """One row per ISO week (Mon-anchored): spend/delivery + acquisition + early value signals."""
    meta = meta_daily.assign(week=_week(meta_daily["date"]))
    spend = meta.groupby("week").agg(
        spend=("spend", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        meta_purchases=("purchases", "sum"),
    )

    firsts = orders.sort_values("order_date").groupby("customer_id").first()
    firsts = firsts.merge(
        customers[["customer_id", "acquisition_date"]], left_index=True, right_on="customer_id"
    )
    firsts["week"] = _week(firsts["acquisition_date"])

    order_no = orders.sort_values("order_date").groupby("customer_id").cumcount()
    second_orders = orders.assign(order_no=order_no)
    second = second_orders[second_orders["order_no"] == 1][["customer_id", "order_date"]]
    second = second.rename(columns={"order_date": "second_order_date"})
    firsts = firsts.merge(second, on="customer_id", how="left")
    firsts["repeated_30d"] = (
        firsts["second_order_date"] - firsts["acquisition_date"]
    ).dt.days <= TARGET_EARLY_SIGNAL_DAYS

    acq = firsts.groupby("week").agg(
        new_customers=("customer_id", "size"),
        first_order_cm=("contribution_margin", "mean"),
    )
    repeat = (
        firsts.assign(week=firsts["week"])
        .groupby("week")
        .apply(
            lambda g: (
                g["repeated_30d"].mean()
                if (as_of - g["acquisition_date"].max()).days >= TARGET_EARLY_SIGNAL_DAYS
                else np.nan
            ),
            include_groups=False,
        )
        .rename("repeat_rate_30d")
    )

    out = spend.join([acq, repeat], how="outer").reset_index()
    out["cac"] = np.where(out["new_customers"] > 0, out["spend"] / out["new_customers"], np.nan)
    return out.sort_values("week").reset_index(drop=True)


def week_over_week(topline: pd.DataFrame, *, metrics: list[str] | None = None) -> pd.DataFrame:
    """Latest complete week vs the one before: absolute and % change per metric."""
    metrics = metrics or ["spend", "new_customers", "cac", "first_order_cm", "repeat_rate_30d"]
    if len(topline) < 2:
        raise ValueError("need at least two weeks for a comparison")
    latest, prior = topline.iloc[-1], topline.iloc[-2]
    rows = []
    for metric in metrics:
        now, before = latest[metric], prior[metric]
        delta = now - before
        usable = pd.notna(before) and before != 0
        rows.append(
            {
                "metric": metric,
                "current": now,
                "prior": before,
                "delta": delta,
                "pct_change": (delta / before) if usable else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _week(dates: pd.Series) -> pd.Series:
    return dates.dt.to_period("W-SUN").dt.start_time
