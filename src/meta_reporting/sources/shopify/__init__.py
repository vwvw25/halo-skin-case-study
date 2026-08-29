"""Shopify Admin API source — real client, mock client, and shared types."""

from meta_reporting.sources.shopify.base import ShopifySource, get_shopify_source
from meta_reporting.sources.shopify.client import ShopifyAPIError, ShopifyClient
from meta_reporting.sources.shopify.mock_client import MockShopifyClient, MockShopifyError
from meta_reporting.sources.shopify.types import (
    Customer,
    CustomerAttrs,
    LineItem,
    Order,
)

__all__ = [
    "Customer",
    "CustomerAttrs",
    "LineItem",
    "MockShopifyClient",
    "MockShopifyError",
    "Order",
    "ShopifyAPIError",
    "ShopifyClient",
    "ShopifySource",
    "get_shopify_source",
]
