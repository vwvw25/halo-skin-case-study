"""The ``ShopifySource`` protocol and a factory that returns the right implementation."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable

from meta_reporting.config import ShopifyConfig, SourceMode
from meta_reporting.sources.shopify.types import Customer, Order


@runtime_checkable
class ShopifySource(Protocol):
    """Everything the pipeline needs from Shopify.

    Implemented by ``ShopifyClient`` (real) and ``MockShopifyClient`` (fixtures).
    """

    def iter_customers(self) -> Iterator[Customer]:
        """Yield every customer in the store."""
        ...

    def iter_orders(
        self, *, since: date | None = None, until: date | None = None
    ) -> Iterator[Order]:
        """Yield orders, optionally bounded by processed date (inclusive)."""
        ...


def get_shopify_source(config: ShopifyConfig, *, fixtures_dir: Path | None = None) -> ShopifySource:
    if config.mode is SourceMode.LIVE:
        from meta_reporting.sources.shopify.client import ShopifyClient

        assert config.store is not None  # guaranteed by ShopifyConfig.from_env
        assert config.admin_token is not None
        return ShopifyClient(store=config.store, admin_token=config.admin_token)

    from meta_reporting.sources.shopify.mock_client import MockShopifyClient

    return MockShopifyClient(fixtures_dir=fixtures_dir)
