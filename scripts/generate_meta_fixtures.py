"""Regenerate the mock Meta Insights fixtures from scripts/_scenario.py.

    python scripts/generate_meta_fixtures.py

Writes into fixtures/meta/:
  * campaigns.json                       — GET /{ad-account}/campaigns
  * insights_daily.json.gz               — ad x day, no breakdowns
  * insights_monthly_age_gender.json.gz  — campaign x month x age x gender
  * insights_monthly_region.json.gz      — campaign x month x region
  * insights_monthly_platform.json.gz    — campaign x month x publisher_platform x platform_position

Every value is emitted as a string, matching the real API. Breakdown fixtures are exact
partitions of the campaign-month totals, so they reconcile with the daily fixture.
"""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from _scenario import (
    ACCOUNT_ID,
    AGE_BUCKETS,
    CAMPAIGNS,
    GENDERS,
    PLATFORMS,
    REGIONS,
    CampaignSpec,
    DailyCell,
    ads_for,
    age_weights,
    all_days,
    daily_cell,
    gender_weights,
    platform_weights,
    region_weights,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "meta"
_ZERO = DailyCell(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def _s(value: float) -> str:
    return f"{value:.2f}"


def _i(value: float) -> str:
    return str(round(value))


def _actions(cell: DailyCell) -> list[dict[str, str]]:
    return [
        {"action_type": "landing_page_view", "value": _i(cell.landing_page_views)},
        {"action_type": "link_click", "value": _i(cell.clicks)},
        {"action_type": "purchase", "value": _i(cell.purchases)},
    ]


def _action_values(cell: DailyCell) -> list[dict[str, str]]:
    return [{"action_type": "purchase", "value": _s(cell.purchase_value)}]


def _scale(cell: DailyCell, w: float) -> DailyCell:
    return DailyCell(
        spend=cell.spend * w,
        impressions=cell.impressions * w,
        clicks=cell.clicks * w,
        landing_page_views=cell.landing_page_views * w,
        purchases=cell.purchases * w,
        purchase_value=cell.purchase_value * w,
        new_customers=cell.new_customers * w,
    )


def _add(a: DailyCell, b: DailyCell) -> DailyCell:
    return DailyCell(
        spend=a.spend + b.spend,
        impressions=a.impressions + b.impressions,
        clicks=a.clicks + b.clicks,
        landing_page_views=a.landing_page_views + b.landing_page_views,
        purchases=a.purchases + b.purchases,
        purchase_value=a.purchase_value + b.purchase_value,
        new_customers=a.new_customers + b.new_customers,
    )


def _month_end(first: date) -> date:
    nxt = (
        first.replace(year=first.year + 1, month=1)
        if first.month == 12
        else first.replace(month=first.month + 1)
    )
    return nxt - timedelta(days=1)


def _write_gz(name: str, rows: list[dict[str, object]]) -> None:
    path = FIXTURES / f"{name}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(rows, fh, separators=(",", ":"))
    print(f"  fixtures/meta/{name}.json.gz  ({len(rows)} rows)")


def build_campaigns() -> list[dict[str, str]]:
    return [
        {
            "id": c.id,
            "name": c.name,
            "objective": c.objective,
            "status": "ACTIVE" if c.end is None else "PAUSED",
            "effective_status": "ACTIVE" if c.end is None else "CAMPAIGN_PAUSED",
        }
        for c in CAMPAIGNS
    ]


def build_daily(days: list[date]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in CAMPAIGNS:
        ads = ads_for(spec)
        for day in days:
            if not spec.active_on(day):
                continue
            cell = daily_cell(spec, day)
            if cell.impressions <= 0:
                continue
            for adset_id, adset_name, ad_id, ad_name, share in ads:
                part = _scale(cell, share)
                rows.append(
                    {
                        "date_start": day.isoformat(),
                        "date_stop": day.isoformat(),
                        "account_id": ACCOUNT_ID,
                        "campaign_id": spec.id,
                        "campaign_name": spec.name,
                        "adset_id": adset_id,
                        "adset_name": adset_name,
                        "ad_id": ad_id,
                        "ad_name": ad_name,
                        "spend": _s(part.spend),
                        "impressions": _i(part.impressions),
                        "clicks": _i(part.clicks),
                        "reach": _i(part.impressions * 0.62),
                        "actions": _actions(part),
                        "action_values": _action_values(part),
                    }
                )
    return rows


def _month_totals(spec: CampaignSpec, days: list[date]) -> dict[date, DailyCell]:
    totals: dict[date, DailyCell] = defaultdict(lambda: _ZERO)
    for day in days:
        if not spec.active_on(day):
            continue
        key = day.replace(day=1)
        totals[key] = _add(totals[key], daily_cell(spec, day))
    return dict(totals)


def _monthly_row(
    spec: CampaignSpec, month: date, part: DailyCell, dims: dict[str, str]
) -> dict[str, object]:
    return {
        "date_start": month.isoformat(),
        "date_stop": _month_end(month).isoformat(),
        "account_id": ACCOUNT_ID,
        "campaign_id": spec.id,
        "campaign_name": spec.name,
        **dims,
        "spend": _s(part.spend),
        "impressions": _i(part.impressions),
        "clicks": _i(part.clicks),
        "reach": _i(part.impressions * 0.34),
        "actions": _actions(part),
        "action_values": _action_values(part),
    }


def build_monthly_age_gender(days: list[date]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in CAMPAIGNS:
        age_w = age_weights(spec.age_profile)
        gen_w = gender_weights(spec.gender_profile)
        for month, total in _month_totals(spec, days).items():
            for age in AGE_BUCKETS:
                for gender in GENDERS:
                    part = _scale(total, age_w[age] * gen_w[gender])
                    rows.append(_monthly_row(spec, month, part, {"age": age, "gender": gender}))
    return rows


def build_monthly_region(days: list[date]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in CAMPAIGNS:
        reg_w = region_weights(spec.region_profile)
        for month, total in _month_totals(spec, days).items():
            for region in REGIONS:
                rows.append(
                    _monthly_row(spec, month, _scale(total, reg_w[region]), {"region": region})
                )
    return rows


def build_monthly_platform(days: list[date]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in CAMPAIGNS:
        plat_w = platform_weights(spec.platform_profile)
        for month, total in _month_totals(spec, days).items():
            for pub, pos in PLATFORMS:
                rows.append(
                    _monthly_row(
                        spec,
                        month,
                        _scale(total, plat_w[(pub, pos)]),
                        {"publisher_platform": pub, "platform_position": pos},
                    )
                )
    return rows


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    days = all_days()
    print(f"generating Meta fixtures for {days[0]} .. {days[-1]}")
    (FIXTURES / "campaigns.json").write_text(json.dumps(build_campaigns(), indent=2) + "\n")
    print("  fixtures/meta/campaigns.json")
    _write_gz("insights_daily", build_daily(days))
    _write_gz("insights_monthly_age_gender", build_monthly_age_gender(days))
    _write_gz("insights_monthly_region", build_monthly_region(days))
    _write_gz("insights_monthly_platform", build_monthly_platform(days))


if __name__ == "__main__":
    main()
