from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from meta_reporting import ingest
from meta_reporting.sources.meta import MockMetaClient
from meta_reporting.sources.shopify import MockShopifyClient
from meta_reporting.transform import acquisition as acq

META = MockMetaClient()
SHOPIFY = MockShopifyClient()
AS_OF = pd.Timestamp("2026-07-31")


@pytest.fixture(scope="module")
def topline() -> pd.DataFrame:
    return acq.weekly_topline(
        ingest.meta_daily(META, date(2025, 6, 1), date(2026, 7, 31)),
        ingest.orders(SHOPIFY),
        ingest.customers(SHOPIFY),
        as_of=AS_OF,
    )


def test_weekly_topline_shape(topline: pd.DataFrame) -> None:
    assert topline["week"].is_monotonic_increasing
    assert topline["week"].is_unique
    assert (topline["cac"] == topline["spend"] / topline["new_customers"]).all()
    assert (topline["first_order_cm"] > 0).all()


def test_repeat_rate_only_for_matured_weeks(topline: pd.DataFrame) -> None:
    recent = topline[topline["week"] > AS_OF - pd.Timedelta(days=30)]
    older = topline[topline["week"] < AS_OF - pd.Timedelta(days=60)]
    assert recent["repeat_rate_30d"].isna().all()
    assert older["repeat_rate_30d"].notna().all()
    assert older["repeat_rate_30d"].between(0, 1).all()


def test_week_over_week(topline: pd.DataFrame) -> None:
    wow = acq.week_over_week(topline)
    assert set(wow["metric"]) == {
        "spend",
        "new_customers",
        "cac",
        "first_order_cm",
        "repeat_rate_30d",
    }
    row = wow.set_index("metric").loc["spend"]
    assert row["delta"] == pytest.approx(row["current"] - row["prior"])
    assert row["pct_change"] == pytest.approx(row["delta"] / row["prior"])


def test_week_over_week_needs_two_weeks() -> None:
    with pytest.raises(ValueError, match="two weeks"):
        acq.week_over_week(pd.DataFrame({"spend": [1.0]}))
