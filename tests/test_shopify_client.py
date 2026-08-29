from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from meta_reporting.sources.shopify import ShopifyAPIError, ShopifyClient


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, *responses: FakeResponse) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self._responses.pop(0)


def _client(session: FakeSession) -> ShopifyClient:
    return ShopifyClient(
        store="halo-skin.myshopify.com",
        admin_token="shpat_x",
        session=session,  # type: ignore[arg-type]
        backoff_base=0.0,
    )


def test_store_suffix_stripped() -> None:
    assert _client(FakeSession()).store == "halo-skin"


def test_auth_header_sent() -> None:
    session = FakeSession(FakeResponse(200, {"customers": []}))
    list(_client(session).iter_customers())
    assert session.calls[0]["headers"]["X-Shopify-Access-Token"] == "shpat_x"
    assert "halo-skin.myshopify.com/admin/api/" in session.calls[0]["url"]


def test_order_date_filters_become_params() -> None:
    session = FakeSession(FakeResponse(200, {"orders": []}))
    list(_client(session).iter_orders(since=date(2026, 1, 1), until=date(2026, 1, 31)))
    params = session.calls[0]["params"]
    assert params["processed_at_min"] == "2026-01-01T00:00:00Z"
    assert params["processed_at_max"] == "2026-01-31T23:59:59Z"
    assert params["status"] == "any"


def test_link_header_pagination() -> None:
    next_url = "https://halo-skin.myshopify.com/admin/api/2024-10/orders.json?page_info=abc"
    page1 = FakeResponse(
        200,
        {"orders": [{"id": 1, "created_at": "2026-01-01T00:00:00+00:00"}]},
        headers={"Link": f'<{next_url}>; rel="next"'},
    )
    page2 = FakeResponse(
        200,
        {"orders": [{"id": 2, "created_at": "2026-01-02T00:00:00+00:00"}]},
    )
    session = FakeSession(page1, page2)
    orders = list(_client(session).iter_orders())
    assert [o.id for o in orders] == [1, 2]
    assert "page_info=abc" in session.calls[1]["url"]
    assert session.calls[1]["params"] is None


def test_429_is_retried_with_retry_after() -> None:
    session = FakeSession(
        FakeResponse(429, headers={"Retry-After": "0"}),
        FakeResponse(200, {"customers": []}),
    )
    list(_client(session).iter_customers())
    assert len(session.calls) == 2


def test_client_error_raises() -> None:
    session = FakeSession(FakeResponse(401, text="Invalid API key"))
    with pytest.raises(ShopifyAPIError) as excinfo:
        list(_client(session).iter_customers())
    assert excinfo.value.status == 401


def test_orders_and_customers_are_parsed() -> None:
    session = FakeSession(
        FakeResponse(
            200,
            {
                "orders": [
                    {
                        "id": 99,
                        "customer": {"id": 7},
                        "created_at": "2026-02-01T12:00:00+00:00",
                        "subtotal_price": "60.00",
                        "total_price": "64.80",
                        "line_items": [{"sku": "HALO-VITC-30", "quantity": 1, "price": "62.00"}],
                    }
                ]
            },
        )
    )
    (order,) = list(_client(session).iter_orders())
    assert order.customer_id == 7
    assert order.order_date == date(2026, 2, 1)
    assert order.line_items[0].sku == "HALO-VITC-30"
