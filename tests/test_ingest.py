from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from meta_reporting import ingest
from meta_reporting.sources.meta import Breakdown, MockMetaClient
from meta_reporting.sources.shopify import MockShopifyClient

META = MockMetaClient()
SHOPIFY = MockShopifyClient()

SINCE, UNTIL = date(2026, 1, 1), date(2026, 3, 31)


@pytest.fixture(scope="module")
def daily() -> pd.DataFrame:
    return ingest.meta_daily(META, SINCE, UNTIL)


@pytest.fixture(scope="module")
def all_orders() -> pd.DataFrame:
    return ingest.orders(SHOPIFY)


@pytest.fixture(scope="module")
def all_customers() -> pd.DataFrame:
    return ingest.customers(SHOPIFY)


def test_meta_daily_shape(daily: pd.DataFrame) -> None:
    assert not daily.empty
    assert {"date", "month", "campaign_id", "strategy", "spend", "purchases"} <= set(daily.columns)
    assert daily["date"].dt.tz is None
    assert pd.api.types.is_datetime64_any_dtype(daily["date"])
    assert (daily["spend"] > 0).all()
    assert daily["strategy"].ne("unknown").all()
    assert daily["date"].min() >= pd.Timestamp(SINCE)
    assert daily["date"].max() <= pd.Timestamp(UNTIL)


def test_meta_segment_spend_reconciles_with_daily(daily: pd.DataFrame) -> None:
    by_age = ingest.meta_spend_by_segment(META, SINCE, UNTIL, Breakdown.AGE)
    assert "age" in by_age.columns
    assert by_age["month"].dt.day.eq(1).all()
    assert by_age["spend"].sum() == pytest.approx(daily["spend"].sum(), rel=0.02)


def test_customers_one_row_each_with_month(all_customers: pd.DataFrame) -> None:
    assert all_customers["customer_id"].is_unique
    assert all_customers["acquisition_month"].dt.day.eq(1).all()
    for col in ("acquisition_campaign_id", "acquisition_strategy", "age", "gender", "region"):
        assert all_customers[col].notna().all()


def test_orders_contribution_margin(all_orders: pd.DataFrame) -> None:
    assert (all_orders["cogs"] > 0).all()
    assert (all_orders["contribution_margin"] < all_orders["net_revenue"]).all()
    # skincare is a high-margin category — pooled CM should be a healthy fraction of revenue
    pooled = all_orders["contribution_margin"].sum() / all_orders["net_revenue"].sum()
    assert 0.45 <= pooled <= 0.8
    assert all_orders["has_premium"].dtype == bool


def test_orders_date_filter() -> None:
    q1 = ingest.orders(SHOPIFY, since=date(2026, 1, 1), until=date(2026, 3, 31))
    assert q1["order_date"].min() >= pd.Timestamp("2026-01-01")
    assert q1["order_date"].max() <= pd.Timestamp("2026-03-31")
    assert len(q1) < len(ingest.orders(SHOPIFY))
