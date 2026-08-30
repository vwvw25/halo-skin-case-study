from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from meta_reporting import ingest
from meta_reporting.domain import LTV_HORIZON_MONTHS
from meta_reporting.sources.meta import MockMetaClient, classify
from meta_reporting.sources.shopify import MockShopifyClient
from meta_reporting.transform import cohorts, spend
from meta_reporting.transform.ltv_cac import ltv_cac_by_segment

META = MockMetaClient()
SHOPIFY = MockShopifyClient()
AS_OF = pd.Timestamp("2026-07-31")


@pytest.fixture(scope="module")
def frames() -> dict[str, pd.DataFrame]:
    return {
        "meta_daily": ingest.meta_daily(META, date(2025, 6, 1), date(2026, 7, 31)),
        "customers": ingest.customers(SHOPIFY),
        "orders": ingest.orders(SHOPIFY),
    }


@pytest.fixture(scope="module")
def curve(frames: dict[str, pd.DataFrame]) -> cohorts.MaturationCurve:
    return cohorts.maturation_curve(frames["orders"], frames["customers"], as_of=AS_OF)


def test_maturation_curve_is_increasing_and_decelerating(curve: cohorts.MaturationCurve) -> None:
    values = curve.cum_cm
    assert list(values.index) == list(range(LTV_HORIZON_MONTHS + 1))
    assert values.is_monotonic_increasing
    assert values.iloc[0] > 0
    increments = values.diff().dropna()
    # each month adds less than the previous (repeat-purchase curve flattens)
    assert (increments.iloc[1:].values <= increments.iloc[:-1].values + 1e-6).all()


def test_spend_and_cac_blended_monthly(frames: dict[str, pd.DataFrame]) -> None:
    out = spend.spend_and_cac(frames["meta_daily"], frames["customers"])
    assert (out["cac"] == out["spend"] / out["new_customers"]).all()
    assert out["period"].dt.day.eq(1).all()
    assert out["spend"].sum() == pytest.approx(frames["meta_daily"]["spend"].sum())


def test_spend_and_cac_weekly_has_more_rows(frames: dict[str, pd.DataFrame]) -> None:
    monthly = spend.spend_and_cac(frames["meta_daily"], frames["customers"], freq="M")
    weekly = spend.spend_and_cac(frames["meta_daily"], frames["customers"], freq="W-MON")
    assert len(weekly) > len(monthly) * 3
    assert weekly["spend"].sum() == pytest.approx(monthly["spend"].sum(), rel=1e-6)


def test_cohort_ltv_projection_behaviour(
    frames: dict[str, pd.DataFrame], curve: cohorts.MaturationCurve
) -> None:
    cl = cohorts.cohort_ltv(frames["orders"], frames["customers"], curve, as_of=AS_OF)
    assert len(cl) == cl["acquisition_month"].nunique()

    mature = cl[cl["observed_age_months"] >= LTV_HORIZON_MONTHS]
    young = cl[cl["observed_age_months"] <= 2]
    assert (mature["maturity"] == "realized").all()
    assert mature["projected_cm_per_customer"].equals(mature["realized_cm_per_customer"])
    assert (young["projected_cm_per_customer"] > young["realized_cm_per_customer"]).all()

    # projected 12-month LTV should be roughly stable across cohorts — that's the curve working
    projected = cl["projected_cm_per_customer"]
    assert projected.std() / projected.mean() < 0.15


def test_ltv_cac_ranking_matches_the_story(
    frames: dict[str, pd.DataFrame], curve: cohorts.MaturationCurve
) -> None:
    cl = cohorts.cohort_ltv(
        frames["orders"], frames["customers"], curve, as_of=AS_OF, by="campaign"
    )
    sc = spend.spend_and_cac(frames["meta_daily"], frames["customers"], by="campaign")
    out = ltv_cac_by_segment(cl, sc, curve, by="campaign")

    out["cm_ltv_over_cac"] = out["cm_ltv_12"] / out["cac"]
    assert out["ltv_cac"].equals(out["cm_ltv_over_cac"])

    campaigns = META.list_campaigns()
    out["name"] = out["campaign"].map({c.id: c.name for c in campaigns})
    out["strategy"] = out["campaign"].map({c.id: classify(c.name).value for c in campaigns})
    ranked = out.set_index("name")["ltv_cac"]

    # Retargeting tops the raw LTV:CAC list — that is the trap the report is built to expose
    # (cheap CAC, low incremental value). Among genuine *acquisition* campaigns, the high-AOV
    # lookalike wins and broad prospecting is the worst.
    acquisition = out[~out["strategy"].isin(["retargeting", "awareness"])].set_index("name")[
        "ltv_cac"
    ]
    assert acquisition.idxmax() == "LAL 1% — Regimen Builders"
    assert acquisition.idxmin() == "Prospecting — Broad"
    assert acquisition["LAL 1% — Regimen Builders"] > 2 * acquisition["Prospecting — Broad"]
    assert ranked["Retargeting — 14d ATC/VC"] > acquisition.median()


def test_payback_is_within_horizon_for_healthy_segments(
    frames: dict[str, pd.DataFrame], curve: cohorts.MaturationCurve
) -> None:
    cl = cohorts.cohort_ltv(
        frames["orders"], frames["customers"], curve, as_of=AS_OF, by="strategy"
    )
    sc = spend.spend_and_cac(frames["meta_daily"], frames["customers"], by="strategy")
    out = ltv_cac_by_segment(cl, sc, curve, by="strategy").set_index("strategy")
    assert out.loc["lookalike", "payback_months"] <= 3
    assert out.loc["prospecting_broad", "payback_months"] >= out.loc["lookalike", "payback_months"]


def test_cohort_value_curves_are_cumulative_and_triangular(
    frames: dict[str, pd.DataFrame],
) -> None:
    curves = cohorts.cohort_value_curves(frames["orders"], frames["customers"], as_of=AS_OF)
    assert {"acquisition_month", "month_index", "cum_revenue", "cum_cm"} <= set(curves.columns)

    for _, cohort in curves.groupby("acquisition_month"):
        ordered = cohort.sort_values("month_index")
        assert ordered["cum_revenue"].is_monotonic_increasing
        assert (ordered["cum_cm"] < ordered["cum_revenue"]).all()  # margin < revenue

    # the oldest cohort is observed for more months than the newest — the triangle shape
    span = curves.groupby("acquisition_month")["month_index"].max()
    assert span.iloc[0] > span.iloc[-1]
    assert span.iloc[0] == LTV_HORIZON_MONTHS


def test_cohort_summary_metadata(frames: dict[str, pd.DataFrame]) -> None:
    monthly_cac = spend.spend_and_cac(frames["meta_daily"], frames["customers"], freq="M")
    summary = cohorts.cohort_summary(frames["orders"], frames["customers"], monthly_cac)

    assert (summary["cohort_size"] > 0).all()
    assert summary["repeat_rate"].between(0, 1).all()
    # recent cohorts have had less time to make a second order
    assert summary.iloc[0]["repeat_rate"] > summary.iloc[-1]["repeat_rate"]
    assert (summary["first_order_revenue"] > summary["first_order_cm"]).all()


def test_value_curve_by_target_shows_the_power_law(frames: dict[str, pd.DataFrame]) -> None:
    from meta_reporting.transform import target_cohort

    classified = target_cohort.classify_customers(
        frames["orders"], frames["customers"], as_of=AS_OF
    )
    curve = cohorts.value_curve_by_target(
        frames["orders"], frames["customers"], classified, as_of=AS_OF
    )
    wide = curve.pivot(index="month_index", columns="segment", values="cum_revenue")

    # the target cohort compounds hard; non-members grow slowly then plateau
    assert wide["target"].is_monotonic_increasing
    assert wide["target"].iloc[-1] > 3 * wide["target"].iloc[0]
    assert wide["other"].iloc[-1] > wide["other"].iloc[0]
    assert wide["other"].iloc[-1] < 2 * wide["other"].iloc[0]

    # the gap widens every step of the year
    gap = wide["target"] - wide["other"]
    assert gap.is_monotonic_increasing
    assert gap.iloc[-1] > 5 * gap.iloc[0]
    assert wide["target"].iloc[-1] > 4 * wide["other"].iloc[-1]

    # the blended average hugs the non-member line — that is the whole point
    assert (wide["blended"] - wide["other"] < wide["target"] - wide["blended"]).all()
