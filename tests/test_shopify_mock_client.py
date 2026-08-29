from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pytest

from meta_reporting.domain import (
    TARGET_MIN_AOV,
    TARGET_MIN_ORDERS_90D,
)
from meta_reporting.sources.shopify import (
    Customer,
    MockShopifyClient,
    MockShopifyError,
    Order,
)

client = MockShopifyClient()
CUSTOMERS = list(client.iter_customers())
ORDERS = list(client.iter_orders())
ORDERS_BY_CUSTOMER: dict[int, list[Order]] = defaultdict(list)
for _o in ORDERS:
    assert _o.customer_id is not None
    ORDERS_BY_CUSTOMER[_o.customer_id].append(_o)

_PREMIUM_SKUS = {"HALO-RETINAL-30", "HALO-VITC-30", "HALO-PEPTIDE-30", "HALO-EYE-15"}


def _is_target(cust: Customer) -> bool:
    orders = sorted(ORDERS_BY_CUSTOMER[cust.id], key=lambda o: o.order_date)
    if not orders:
        return False
    acq = orders[0].order_date
    in_90 = [o for o in orders if o.order_date <= acq + timedelta(days=90)]
    if len(in_90) < TARGET_MIN_ORDERS_90D:
        return False
    if sum(o.net_revenue for o in in_90) / len(in_90) < TARGET_MIN_AOV:
        return False
    return any(li.sku in _PREMIUM_SKUS for o in orders for li in o.line_items)


def test_customer_count_in_expected_band() -> None:
    assert 18_000 <= len(CUSTOMERS) <= 24_000


def test_every_customer_has_full_attribution() -> None:
    for cust in CUSTOMERS[::250]:
        attrs = cust.attrs()
        assert attrs.acquisition_campaign_id and attrs.acquisition_campaign_id.isdigit()
        assert isinstance(attrs.acquisition_date, date)
        assert attrs.acquisition_strategy
        assert (attrs.age and "-" in attrs.age) or attrs.age == "65+"
        assert attrs.gender in {"female", "male", "unknown"}
        assert cust.region


def test_orders_are_sorted_by_processed_at() -> None:
    dates = [o.order_date for o in ORDERS]
    assert dates == sorted(dates)


def test_orders_count_and_total_spent_reconcile() -> None:
    for cust in CUSTOMERS[::200]:
        owned = ORDERS_BY_CUSTOMER[cust.id]
        assert cust.orders_count == len(owned)
        assert cust.total_spent == pytest.approx(sum(o.total_price for o in owned), abs=0.05)


def test_iter_orders_date_filtering() -> None:
    window = list(client.iter_orders(since=date(2026, 1, 1), until=date(2026, 1, 31)))
    assert window
    assert all(date(2026, 1, 1) <= o.order_date <= date(2026, 1, 31) for o in window)
    assert len(window) < len(ORDERS)


def test_net_revenue_accounts_for_discounts_and_refunds() -> None:
    refunded = next(o for o in ORDERS if o.total_refunded > 0)
    assert refunded.net_revenue == pytest.approx(
        refunded.subtotal_price - refunded.total_discounts - refunded.total_refunded
    )
    assert refunded.financial_status == "partially_refunded"


def test_target_cohort_is_about_a_fifth() -> None:
    share = sum(_is_target(c) for c in CUSTOMERS) / len(CUSTOMERS)
    assert 0.16 <= share <= 0.24, f"target cohort share drifted to {share:.1%} — retune _customers"


def test_repeat_behaviour_correlates_moderately_with_strategy() -> None:
    hits: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for cust in CUSTOMERS:
        strategy = cust.attrs().acquisition_strategy or "?"
        hits[strategy][0] += _is_target(cust)
        hits[strategy][1] += 1

    rate = {s: h / n for s, (h, n) in hits.items() if n > 300}
    best, worst = max(rate.values()), min(rate.values())
    # "moderate": a real but not cartoonish spread
    assert 1.8 <= best / worst <= 3.5
    assert rate["lookalike"] > rate["prospecting_broad"]


def test_missing_fixture_raises() -> None:
    stray = MockShopifyClient(fixtures_dir=Path("/nonexistent/shopify"))
    with pytest.raises(MockShopifyError, match="missing"):
        list(stray.iter_customers())
