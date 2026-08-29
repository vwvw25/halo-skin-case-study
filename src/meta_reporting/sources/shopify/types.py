"""Typed models for the Shopify Admin API (orders and customers).

Field names match the Admin REST API (2024-10). Money fields arrive as strings, as they do
from Shopify. Acquisition attribution and survey demographics are not native Shopify columns —
Halo Skin stores them as structured customer tags (``acq_campaign:238500000000003``,
``age:35-44``), which is a common pattern; :meth:`Customer.attrs` parses them back out.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LineItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sku: str
    title: str | None = None
    quantity: int = 1
    price: float = 0.0
    product_id: int | None = None

    @property
    def gross(self) -> float:
        return self.price * self.quantity


class CustomerRef(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int


class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    customer: CustomerRef | None = None
    created_at: datetime
    processed_at: datetime | None = None
    currency: str = "USD"
    total_price: float = 0.0
    subtotal_price: float = 0.0
    total_discounts: float = 0.0
    total_tax: float = 0.0
    total_refunded: float = 0.0
    financial_status: str = "paid"
    line_items: list[LineItem] = Field(default_factory=list)

    @property
    def customer_id(self) -> int | None:
        return self.customer.id if self.customer else None

    @property
    def order_date(self) -> date:
        return (self.processed_at or self.created_at).date()

    @property
    def net_revenue(self) -> float:
        """Revenue booked to the brand: subtotal after discounts, before tax, less refunds."""
        return self.subtotal_price - self.total_refunded


class Address(BaseModel):
    model_config = ConfigDict(extra="ignore")
    province: str | None = None
    country_code: str | None = None


class CustomerAttrs(BaseModel):
    """The bits parsed out of a customer's tags."""

    acquisition_campaign_id: str | None = None
    acquisition_date: date | None = None
    acquisition_strategy: str | None = None
    age: str | None = None
    gender: str | None = None


class Customer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    email: str | None = None
    created_at: datetime
    first_name: str | None = None
    last_name: str | None = None
    orders_count: int = 0
    total_spent: float = 0.0
    tags: str = ""
    default_address: Address | None = None

    @property
    def region(self) -> str | None:
        return self.default_address.province if self.default_address else None

    def attrs(self) -> CustomerAttrs:
        parsed: dict[str, Any] = {}
        for raw in self.tags.split(","):
            tag = raw.strip()
            if ":" not in tag:
                continue
            key, _, value = tag.partition(":")
            match key.strip():
                case "acq_campaign":
                    parsed["acquisition_campaign_id"] = value.strip()
                case "acq_date":
                    parsed["acquisition_date"] = date.fromisoformat(value.strip())
                case "acq_strategy":
                    parsed["acquisition_strategy"] = value.strip()
                case "age":
                    parsed["age"] = value.strip()
                case "gender":
                    parsed["gender"] = value.strip()
        return CustomerAttrs.model_validate(parsed)
