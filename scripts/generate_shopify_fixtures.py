"""Regenerate the mock Shopify fixtures from the shared scenario.

    python scripts/generate_shopify_fixtures.py

Writes into fixtures/shopify/:
  * customers.json.gz — Admin API customer objects (attribution + survey demographics in tags)
  * orders.json.gz    — Admin API order objects, sorted by processed_at

Money is emitted as strings, matching the Admin API.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from _customers import GenCustomer, GenOrder, generate_customers

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "shopify"

_REGION_COUNTRY = {
    "California": "US",
    "New York": "US",
    "Texas": "US",
    "Florida": "US",
    "Illinois": "US",
    "Washington": "US",
    "Other": "US",
}


def _m(value: float) -> str:
    return f"{value:.2f}"


def _iso(dt: object) -> str:
    return f"{dt:%Y-%m-%dT%H:%M:%S}+00:00"


def customer_json(cust: GenCustomer) -> dict[str, object]:
    tags = ", ".join(
        [
            f"acq_campaign:{cust.campaign_id}",
            f"acq_date:{cust.orders[0].processed_at:%Y-%m-%d}",
            f"acq_strategy:{cust.strategy}",
            f"age:{cust.age}",
            f"gender:{cust.gender}",
        ]
    )
    return {
        "id": cust.id,
        "email": cust.email,
        "created_at": _iso(cust.created_at),
        "updated_at": _iso(cust.orders[-1].processed_at),
        "first_name": cust.first_name,
        "last_name": cust.last_name,
        "orders_count": len(cust.orders),
        "total_spent": _m(cust.total_spent),
        "tags": tags,
        "default_address": {
            "province": cust.region,
            "country_code": _REGION_COUNTRY.get(cust.region, "US"),
        },
    }


def order_json(order: GenOrder) -> dict[str, object]:
    return {
        "id": order.id,
        "customer": {"id": order.customer_id},
        "created_at": _iso(order.processed_at),
        "processed_at": _iso(order.processed_at),
        "currency": "USD",
        "subtotal_price": _m(order.subtotal),
        "total_discounts": _m(order.discount),
        "total_tax": _m(order.tax),
        "total_price": _m(order.total),
        "total_refunded": _m(order.refund),
        "financial_status": "partially_refunded" if order.refund else "paid",
        "line_items": [
            {
                "sku": sku.sku,
                "title": sku.title,
                "quantity": qty,
                "price": _m(sku.price),
                "product_id": sku.product_id,
            }
            for sku, qty in order.line_items
        ],
    }


def _write_gz(name: str, rows: list[dict[str, object]]) -> None:
    path = FIXTURES / f"{name}.json.gz"
    payload = json.dumps(rows, separators=(",", ":")).encode("utf-8")
    path.write_bytes(gzip.compress(payload, mtime=0))  # mtime=0 -> byte-stable across runs
    print(
        f"  fixtures/shopify/{name}.json.gz  ({len(rows)} rows, {path.stat().st_size // 1024} KB)"
    )


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    customers = generate_customers()
    orders = sorted((o for c in customers for o in c.orders), key=lambda o: o.processed_at)
    print(f"generated {len(customers)} customers, {len(orders)} orders")
    _write_gz("customers", [customer_json(c) for c in customers])
    _write_gz("orders", [order_json(o) for o in orders])


if __name__ == "__main__":
    main()
