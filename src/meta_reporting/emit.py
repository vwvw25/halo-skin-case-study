"""Emit the dashboard data file.

The Next.js dashboard is an always-on view of the current picture, so this writes one
comprehensive JSON (not one per cadence): headline KPIs, the weekly trend series, the cohort
maturation triangle, LTV:CAC by campaign and strategy, and target-cohort capture. The pipeline
writes ``data/dashboard.json`` (latest) plus a dated snapshot under ``data/snapshots/``.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from meta_reporting import domain, ingest
from meta_reporting.sources.meta import MetaSource
from meta_reporting.sources.shopify import ShopifySource
from meta_reporting.transform import acquisition, cohorts, spend, target_cohort
from meta_reporting.transform.ltv_cac import ltv_cac_by_segment

_HISTORY_START = date(2025, 6, 1)


def build_dashboard_data(
    meta: MetaSource, shopify: ShopifySource, *, as_of: date
) -> dict[str, Any]:
    md = ingest.meta_daily(meta, _HISTORY_START, as_of)
    customers = ingest.customers(shopify)
    orders = ingest.orders(shopify)
    as_of_ts = pd.Timestamp(as_of)

    curve = cohorts.maturation_curve(orders, customers, as_of=as_of_ts)
    cohort_all = cohorts.cohort_ltv(orders, customers, curve, as_of=as_of_ts)
    cohort_campaign = cohorts.cohort_ltv(orders, customers, curve, as_of=as_of_ts, by="campaign")
    cohort_strategy = cohorts.cohort_ltv(orders, customers, curve, as_of=as_of_ts, by="strategy")

    lc_campaign = ltv_cac_by_segment(
        cohort_campaign, spend.spend_and_cac(md, customers, by="campaign"), curve, by="campaign"
    )
    lc_strategy = ltv_cac_by_segment(
        cohort_strategy, spend.spend_and_cac(md, customers, by="strategy"), curve, by="strategy"
    )
    names = (
        md[["campaign_id", "campaign_name"]]
        .drop_duplicates()
        .set_index("campaign_id")["campaign_name"]
    )
    lc_campaign["name"] = lc_campaign["campaign"].map(names)

    classified = target_cohort.classify_customers(orders, customers, as_of=as_of_ts)
    capture = target_cohort.capture_rate(classified, by="strategy")

    weekly = acquisition.weekly_topline(md, orders, customers, as_of=as_of_ts)
    weekly = weekly[weekly["week"] + pd.Timedelta(days=7) <= as_of_ts]

    monthly_spend = spend.spend_and_cac(md, customers, freq="M")
    # the trailing rows can be spend-free months of future-dated acquisitions; use the last
    # month that actually had spend as the "current" CAC
    spent_months = monthly_spend[monthly_spend["spend"] > 0]

    blended_ltv = _weighted(cohort_all["projected_cm_per_customer"], cohort_all["cohort_size"])
    blended_cac = float(spent_months.iloc[-1]["cac"]) if len(spent_months) else float("nan")

    return {
        "brand": "Halo Skin",
        "as_of": as_of.isoformat(),
        "assumptions": {
            "ltv_horizon_months": domain.LTV_HORIZON_MONTHS,
            "target_cohort": {
                "min_orders": domain.TARGET_MIN_ORDERS,
                "window_days": domain.TARGET_WINDOW_DAYS,
                "min_aov": domain.TARGET_MIN_AOV,
                "requires_premium_sku": domain.TARGET_REQUIRE_PREMIUM_SKU,
            },
            "healthy_ltv_cac": domain.HEALTHY_LTV_CAC,
        },
        "headline": {
            "blended_cac": round(blended_cac, 2),
            "blended_cm_ltv_12": round(blended_ltv, 2),
            "blended_ltv_cac": round(blended_ltv / blended_cac, 2) if blended_cac else None,
            "customers_total": len(customers),
            "target_cohort_share": _round(capture_overall(classified)),
        },
        "weekly_trend": _records(
            weekly,
            [
                "week",
                "spend",
                "impressions",
                "clicks",
                "new_customers",
                "cac",
                "first_order_cm",
                "repeat_rate_30d",
            ],
        ),
        "monthly_spend": _records(monthly_spend, ["period", "spend", "new_customers", "cac"]),
        "maturation_curve": [
            {"tenure_month": int(t), "cum_cm_per_customer": round(float(v), 2)}
            for t, v in curve.cum_cm.items()
        ],
        "cohort_ltv": _records(
            cohort_all,
            [
                "acquisition_month",
                "cohort_size",
                "observed_age_months",
                "realized_cm_per_customer",
                "projected_cm_per_customer",
                "maturity",
            ],
        ),
        "ltv_cac_by_campaign": _records(
            lc_campaign,
            [
                "name",
                "customers",
                "cac",
                "cm_ltv_12",
                "ltv_cac",
                "payback_months",
                "realized_share",
            ],
        ),
        "ltv_cac_by_strategy": _records(
            lc_strategy,
            ["strategy", "customers", "cac", "cm_ltv_12", "ltv_cac", "payback_months"],
        ),
        "capture_by_strategy": _records(
            capture,
            [
                "acquisition_strategy",
                "customers",
                "matured",
                "realized_capture_rate",
                "predicted_capture_rate",
                "blended_capture_rate",
            ],
        ),
    }


def write_dashboard_data(data: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / "dashboard.json"
    latest.write_text(json.dumps(data, indent=2, default=str) + "\n")

    snapshots = out_dir / "snapshots"
    snapshots.mkdir(exist_ok=True)
    (snapshots / f"{data['as_of']}.json").write_text(json.dumps(data, default=str) + "\n")
    return latest


# --- helpers -----------------------------------------------------------------------------


def capture_overall(classified: pd.DataFrame) -> float:
    matured = classified[classified["matured"]]
    return float(matured["is_target"].mean()) if len(matured) else float("nan")


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    present = [c for c in columns if c in frame.columns]
    out: list[dict[str, Any]] = []
    for _, row in frame[present].iterrows():
        rec: dict[str, Any] = {}
        for col in present:
            value = row[col]
            if isinstance(value, pd.Timestamp):
                rec[col] = value.date().isoformat()
            elif pd.isna(value):
                rec[col] = None
            elif hasattr(value, "item"):
                rec[col] = _round(value.item())
            else:
                rec[col] = _round(value) if isinstance(value, float) else value
        out.append(rec)
    return out


def _round(value: Any) -> Any:
    return round(value, 4) if isinstance(value, float) else value


def _weighted(values: pd.Series, weights: pd.Series) -> float:
    total = weights.sum()
    return float((values * weights).sum() / total) if total else float("nan")
