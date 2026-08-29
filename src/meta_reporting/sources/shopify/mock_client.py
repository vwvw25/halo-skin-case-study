"""Mock Shopify source — reads gzipped fixtures in Admin API shape.

Fixtures shipped in fixtures/shopify/:
  * ``customers.json.gz`` — list of customer objects (attribution + survey demographics in tags)
  * ``orders.json.gz``    — list of order objects, sorted by processed_at

See scripts/generate_shopify_fixtures.py for how they are built from the shared scenario.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

from meta_reporting.sources.shopify.types import Customer, Order

_DEFAULT_FIXTURES = Path(__file__).resolve().parents[4] / "fixtures" / "shopify"


class MockShopifyError(RuntimeError):
    pass


class MockShopifyClient:
    def __init__(self, *, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or _DEFAULT_FIXTURES

    def iter_customers(self) -> Iterator[Customer]:
        for row in _load(self.fixtures_dir, "customers"):
            yield Customer.model_validate(row)

    def iter_orders(
        self, *, since: date | None = None, until: date | None = None
    ) -> Iterator[Order]:
        for row in _load(self.fixtures_dir, "orders"):
            order = Order.model_validate(row)
            if since is not None and order.order_date < since:
                continue
            if until is not None and order.order_date > until:
                continue
            yield order


@cache
def _load_cached(path_str: str) -> tuple[dict[str, Any], ...]:
    with gzip.open(path_str, "rt", encoding="utf-8") as fh:
        return tuple(json.load(fh))


def _load(fixtures_dir: Path, name: str) -> tuple[dict[str, Any], ...]:
    path = fixtures_dir / f"{name}.json.gz"
    if not path.exists():
        raise MockShopifyError(
            f"fixture {path} is missing — run scripts/generate_shopify_fixtures.py"
        )
    return _load_cached(str(path))
