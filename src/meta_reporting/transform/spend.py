"""Spend, acquired customers, and CAC — by period and by acquisition segment.

Spend comes from Meta (``meta_daily``); acquired-customer counts come from Shopify attribution.
Because ~18% of Meta-acquired customers never get tagged (see scripts/_customers.py), the CAC
here is *cost per attributed new customer* and sits a little above true CAC — the report
appendix says so.

``by`` selects the segmentation:
  * ``None``       — blended account view
  * ``"strategy"`` — prospecting / lookalike / retargeting / ...
  * ``"campaign"`` — per Meta campaign

Demographic breakdowns (age / gender / region) only exist at monthly granularity and come from
``meta_spend_by_segment`` — see :func:`spend_and_cac_by_dimension`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_META_KEY = {"strategy": "strategy", "campaign": "campaign_id"}
_CUSTOMER_KEY = {"strategy": "acquisition_strategy", "campaign": "acquisition_campaign_id"}


def spend_and_cac(
    meta_daily: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    by: str | None = None,
    freq: str = "M",
) -> pd.DataFrame:
    """One row per period (x segment): ``spend``, ``new_customers``, ``cac``.

    ``freq`` is a pandas offset alias — ``"M"`` for the monthly deep-dive, ``"W-MON"`` weekly.
    """
    if by not in (None, "strategy", "campaign"):
        raise ValueError(f"by must be None, 'strategy' or 'campaign'; got {by!r}")

    spend = _sum_by(
        meta_daily,
        value="spend",
        period_col="date",
        freq=freq,
        segment=None if by is None else _META_KEY[by],
        segment_out=by,
    )
    acq = _count_by(
        customers,
        period_col="acquisition_date",
        freq=freq,
        segment=None if by is None else _CUSTOMER_KEY[by],
        segment_out=by,
    )

    keys = ["period"] + ([] if by is None else [by])
    merged = spend.merge(acq, on=keys, how="outer")
    merged[["spend", "new_customers"]] = merged[["spend", "new_customers"]].fillna(0.0)
    merged["cac"] = np.where(
        merged["new_customers"] > 0, merged["spend"] / merged["new_customers"], np.nan
    )
    return merged.sort_values(keys).reset_index(drop=True)


def spend_and_cac_by_dimension(
    meta_spend_by_segment: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    dimension: str,
) -> pd.DataFrame:
    """Monthly spend / new_customers / cac split by a demographic dimension (age|gender|region)."""
    spend = (
        meta_spend_by_segment.groupby(["month", dimension], dropna=False)["spend"]
        .sum()
        .reset_index()
    )
    acq = (
        customers.assign(month=customers["acquisition_month"])
        .groupby(["month", dimension], dropna=False)
        .size()
        .reset_index(name="new_customers")
    )
    merged = spend.merge(acq, on=["month", dimension], how="outer")
    merged[["spend", "new_customers"]] = merged[["spend", "new_customers"]].fillna(0.0)
    merged["cac"] = np.where(
        merged["new_customers"] > 0, merged["spend"] / merged["new_customers"], np.nan
    )
    return merged.sort_values(["month", dimension]).reset_index(drop=True)


def _sum_by(
    frame: pd.DataFrame,
    *,
    value: str,
    period_col: str,
    freq: str,
    segment: str | None,
    segment_out: str | None,
) -> pd.DataFrame:
    work = frame.assign(period=frame[period_col].dt.to_period(freq).dt.start_time)
    keys = ["period"] + ([] if segment is None else [segment])
    out = work.groupby(keys, dropna=False)[value].sum().reset_index()
    if segment and segment_out and segment != segment_out:
        out = out.rename(columns={segment: segment_out})
    return out


def _count_by(
    frame: pd.DataFrame,
    *,
    period_col: str,
    freq: str,
    segment: str | None,
    segment_out: str | None,
) -> pd.DataFrame:
    work = frame.assign(period=frame[period_col].dt.to_period(freq).dt.start_time)
    keys = ["period"] + ([] if segment is None else [segment])
    out = work.groupby(keys, dropna=False).size().reset_index(name="new_customers")
    if segment and segment_out and segment != segment_out:
        out = out.rename(columns={segment: segment_out})
    return out
