"""Real Shopify Admin API client (REST, 2024-10).

Built to the documented contract: cursor pagination via the ``Link`` header, 429 handling with
``Retry-After``, and the ``{"orders": [...]}`` / ``{"customers": [...]}`` envelopes. Exercised
in tests against synthetic responses; not run against a live store (see docs/data-sources.md).
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from datetime import date
from typing import Any

import requests

from meta_reporting.sources.shopify.types import Customer, Order

_API_VERSION = "2024-10"
_PAGE_SIZE = 250
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class ShopifyAPIError(RuntimeError):
    def __init__(self, message: str, *, status: int) -> None:
        super().__init__(message)
        self.status = status


class ShopifyClient:
    def __init__(
        self,
        *,
        store: str,
        admin_token: str,
        session: requests.Session | None = None,
        max_retries: int = 4,
        backoff_base: float = 1.5,
    ) -> None:
        self.store = store.removesuffix(".myshopify.com")
        self.admin_token = admin_token
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    @property
    def _root(self) -> str:
        return f"https://{self.store}.myshopify.com/admin/api/{_API_VERSION}"

    def iter_customers(self) -> Iterator[Customer]:
        for page in self._paginate(f"{self._root}/customers.json", {"limit": _PAGE_SIZE}):
            for row in page.get("customers", []):
                yield Customer.model_validate(row)

    def iter_orders(
        self, *, since: date | None = None, until: date | None = None
    ) -> Iterator[Order]:
        params: dict[str, Any] = {"limit": _PAGE_SIZE, "status": "any"}
        if since is not None:
            params["processed_at_min"] = f"{since.isoformat()}T00:00:00Z"
        if until is not None:
            params["processed_at_max"] = f"{until.isoformat()}T23:59:59Z"
        for page in self._paginate(f"{self._root}/orders.json", params):
            for row in page.get("orders", []):
                yield Order.model_validate(row)

    # --- internals ----------------------------------------------------------------------

    def _paginate(self, url: str, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
        next_url: str | None = url
        next_params: dict[str, Any] | None = params
        while next_url:
            response = self._get(next_url, next_params)
            yield response.json()
            next_url = _next_link(response.headers.get("Link", ""))
            next_params = None  # the Link URL carries its own querystring

    def _get(self, url: str, params: dict[str, Any] | None) -> requests.Response:
        headers = {"X-Shopify-Access-Token": self.admin_token}
        for attempt in range(self.max_retries):
            response = self.session.get(url, params=params, headers=headers, timeout=60)
            if response.status_code == 200:
                return response
            if response.status_code == 429 and attempt < self.max_retries - 1:
                time.sleep(float(response.headers.get("Retry-After", self.backoff_base**attempt)))
                continue
            if response.status_code in (500, 502, 503) and attempt < self.max_retries - 1:
                time.sleep(self.backoff_base**attempt)
                continue
            raise ShopifyAPIError(
                f"{response.status_code} from {url}: {response.text[:200]}",
                status=response.status_code,
            )
        raise ShopifyAPIError(f"exhausted retries for {url}", status=0)


def _next_link(link_header: str) -> str | None:
    match = _LINK_NEXT.search(link_header)
    return match.group(1) if match else None
