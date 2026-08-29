"""Business constants shared across the transform and report layers.

These are the assumptions a reader needs to trust the numbers, so they live in one place and
are surfaced in the report appendix. The target-cohort thresholds were tuned against the mock
dataset so that roughly the top fifth of customers by value qualify (see
tests/test_shopify_mock_client.py::test_target_cohort_is_about_a_fifth).
"""

from __future__ import annotations

from typing import Final

# --- LTV horizon --------------------------------------------------------------------------

LTV_HORIZON_MONTHS: Final = 12
"""Every LTV figure is a 12-month contribution-margin LTV, reported as realized + projected."""

COHORT_MATURITY_MONTHS: Final = 6
"""A monthly acquisition cohort is old enough to fit a repeat-purchase curve at this age."""

# --- contribution margin ------------------------------------------------------------------

SHIPPING_COST_PER_ORDER: Final = 5.20
PAYMENT_FEE_RATE: Final = 0.029
PAYMENT_FEE_FLAT: Final = 0.30
# per-SKU COGS lives in the product catalog; these cover the rest of the variable cost stack.

# --- target cohort ----------------------------------------------------------------------

TARGET_MIN_ORDERS_90D: Final = 3
TARGET_MIN_AOV: Final = 62.0
TARGET_REQUIRE_PREMIUM_SKU: Final = True
"""Halo Skin's high-value customer: >= 3 orders in the first 90 days, average order value at or
above TARGET_MIN_AOV, and at least one purchase from the premium SKU line."""

# --- health lines (for report styling / callouts) --------------------------------------

HEALTHY_LTV_CAC: Final = 3.0
TARGET_PAYBACK_MONTHS: Final = 4.0
