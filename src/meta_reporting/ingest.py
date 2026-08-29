"""Pull both sources into tidy pandas frames.

Nothing here computes business metrics — that is the transform layer's job. Ingest only
flattens the typed API objects into columns, joins in the reference data every downstream step
needs (campaign strategy, per-order contribution margin), and normalises dates.

Frames produced:
  * ``meta_daily``          — one row per ad x day
  * ``meta_spend_by_segment`` — one row per campaign x month x breakdown value
  * ``customers``           — one row per customer (acquisition attribution + demographics)
  * ``orders``              — one row per order (revenue, COGS, contribution margin)
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from meta_reporting import domain
from meta_reporting.catalog import BY_SKU, PREMIUM_SKUS
from meta_reporting.sources.meta import Breakdown, InsightsRequest, Level, MetaSource, classify
from meta_reporting.sources.shopify import Order, ShopifySource


def meta_daily(meta: MetaSource, since: date, until: date) -> pd.DataFrame:
    rows = meta.get_insights(
        InsightsRequest(since=since, until=until, level=Level.AD, time_increment=1)
    )
    frame = pd.DataFrame.from_records(
        {
            "date": r.date_start,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
            "adset_id": r.adset_id,
            "ad_id": r.ad_id,
            "ad_name": r.ad_name,
            "strategy": classify(r.campaign_name or "").value,
            "spend": r.spend,
            "impressions": r.impressions,
            "clicks": r.clicks,
            "link_clicks": r.link_clicks,
            "landing_page_views": r.landing_page_views,
            "purchases": r.purchases,
            "purchase_value": r.purchase_value,
        }
        for r in rows
    )
    return _with_month(frame, "date", "month")


def meta_spend_by_segment(
    meta: MetaSource, since: date, until: date, breakdown: Breakdown
) -> pd.DataFrame:
    rows = meta.get_insights(
        InsightsRequest(
            since=since,
            until=until,
            level=Level.CAMPAIGN,
            time_increment="monthly",
            breakdowns=(breakdown,),
        )
    )
    dim = breakdown.value
    frame = pd.DataFrame.from_records(
        {
            "month": r.date_start,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
            "strategy": classify(r.campaign_name or "").value,
            dim: getattr(r, dim),
            "spend": r.spend,
            "impressions": r.impressions,
            "clicks": r.clicks,
            "purchases": r.purchases,
        }
        for r in rows
    )
    frame["month"] = pd.to_datetime(frame["month"]).dt.to_period("M").dt.to_timestamp()
    return frame


def customers(shopify: ShopifySource) -> pd.DataFrame:
    records = []
    for cust in shopify.iter_customers():
        attrs = cust.attrs()
        records.append(
            {
                "customer_id": cust.id,
                "acquisition_date": attrs.acquisition_date,
                "acquisition_campaign_id": attrs.acquisition_campaign_id,
                "acquisition_strategy": attrs.acquisition_strategy,
                "age": attrs.age,
                "gender": attrs.gender,
                "region": cust.region,
            }
        )
    frame = pd.DataFrame.from_records(records)
    return _with_month(frame, "acquisition_date", "acquisition_month")


def orders(
    shopify: ShopifySource, *, since: date | None = None, until: date | None = None
) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(
        _order_record(o) for o in shopify.iter_orders(since=since, until=until)
    )
    return _with_month(frame, "order_date", "order_month")


def _order_record(order: Order) -> dict[str, object]:
    cogs = sum(
        BY_SKU[li.sku].unit_cost * li.quantity for li in order.line_items if li.sku in BY_SKU
    )
    payment_fee = domain.PAYMENT_FEE_RATE * order.total_price + domain.PAYMENT_FEE_FLAT
    contribution_margin = order.net_revenue - cogs - domain.SHIPPING_COST_PER_ORDER - payment_fee
    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "order_date": order.order_date,
        "gross_revenue": order.subtotal_price,
        "net_revenue": round(order.net_revenue, 2),
        "discount": order.total_discounts,
        "refund": order.total_refunded,
        "cogs": round(cogs, 2),
        "contribution_margin": round(contribution_margin, 2),
        "units": sum(li.quantity for li in order.line_items),
        "has_premium": any(li.sku in PREMIUM_SKUS for li in order.line_items),
    }


def _with_month(frame: pd.DataFrame, date_col: str, month_col: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    frame[date_col] = pd.to_datetime(frame[date_col])
    frame[month_col] = frame[date_col].dt.to_period("M").dt.to_timestamp()
    return frame
