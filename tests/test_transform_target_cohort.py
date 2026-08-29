from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from meta_reporting import ingest
from meta_reporting.sources.shopify import MockShopifyClient
from meta_reporting.transform import target_cohort as tc

SHOPIFY = MockShopifyClient()
AS_OF = pd.Timestamp("2026-07-31")


@pytest.fixture(scope="module")
def classified() -> pd.DataFrame:
    orders = ingest.orders(SHOPIFY)
    customers = ingest.customers(SHOPIFY)
    return tc.classify_customers(orders, customers, as_of=AS_OF)


def test_maturity_flag_tracks_acquisition_age(classified: pd.DataFrame) -> None:
    recent = classified[classified["acquisition_date"] > AS_OF - pd.Timedelta(days=90)]
    old = classified[classified["acquisition_date"] < AS_OF - pd.Timedelta(days=120)]
    assert not recent["matured"].any()
    assert old["matured"].all()


def test_realized_target_rate_is_about_a_fifth(classified: pd.DataFrame) -> None:
    matured = classified[classified["matured"]]
    assert 0.16 <= matured["is_target"].mean() <= 0.26


def test_is_target_requires_all_three_criteria(classified: pd.DataFrame) -> None:
    from meta_reporting.domain import TARGET_MIN_AOV, TARGET_MIN_ORDERS

    targets = classified[classified["matured"] & classified["is_target"]]
    assert (targets["orders_90d"] >= TARGET_MIN_ORDERS).all()
    assert (targets["aov_90d"] >= TARGET_MIN_AOV).all()
    assert targets["premium_90d"].all()


def test_predicted_prob_is_a_probability_and_rises_with_early_orders(
    classified: pd.DataFrame,
) -> None:
    assert classified["predicted_prob"].between(0, 1).all()
    by_orders = classified.groupby(classified["orders_30d"].clip(upper=3))["predicted_prob"].mean()
    assert by_orders.is_monotonic_increasing


def test_capture_rate_by_strategy_spread(classified: pd.DataFrame) -> None:
    cr = tc.capture_rate(classified, by="strategy").set_index("acquisition_strategy")
    assert (
        cr.loc["lookalike", "realized_capture_rate"]
        > cr.loc["prospecting_broad", "realized_capture_rate"]
    )
    ratio = (
        cr.loc["lookalike", "realized_capture_rate"]
        / cr.loc["prospecting_broad", "realized_capture_rate"]
    )
    assert 1.8 <= ratio <= 3.5
    # blended sits between realized and predicted
    for strategy in ("lookalike", "prospecting_broad", "advantage_plus"):
        row = cr.loc[strategy]
        lo, hi = sorted([row["realized_capture_rate"], row["predicted_capture_rate"]])
        assert lo - 1e-9 <= row["blended_capture_rate"] <= hi + 1e-9


def test_capture_rate_blended_view_is_one_row(classified: pd.DataFrame) -> None:
    overall = tc.capture_rate(classified, by=None)
    assert len(overall) == 1
    assert 0.16 <= overall.iloc[0]["realized_capture_rate"] <= 0.26


def test_frame_shape() -> None:
    # smoke: classify on a small window still returns one row per customer
    orders = ingest.orders(SHOPIFY, since=date(2025, 6, 1), until=date(2026, 7, 31))
    customers = ingest.customers(SHOPIFY)
    out = tc.classify_customers(orders, customers, as_of=AS_OF)
    assert len(out) == len(customers)
    assert out["customer_id"].is_unique
