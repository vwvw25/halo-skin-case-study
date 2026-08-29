from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pytest

from meta_reporting.sources.meta import (
    Breakdown,
    InsightsRequest,
    InsightsRow,
    Level,
    MockMetaClient,
    MockMetaError,
)
from meta_reporting.sources.meta.types import TimeIncrement

client = MockMetaClient()


def req(
    since: date,
    until: date,
    *,
    level: Level = Level.CAMPAIGN,
    time_increment: TimeIncrement = 1,
    breakdowns: tuple[Breakdown, ...] = (),
) -> InsightsRequest:
    return InsightsRequest(
        since=since,
        until=until,
        level=level,
        time_increment=time_increment,
        breakdowns=breakdowns,
    )


def total_spend(rows: Sequence[InsightsRow]) -> float:
    return round(sum(r.spend for r in rows), 2)


def test_list_campaigns() -> None:
    campaigns = client.list_campaigns()
    assert len(campaigns) == 10
    lal = next(c for c in campaigns if c.name == "LAL 1% — High-AOV Purchasers")
    assert lal.objective == "OUTCOME_SALES"
    assert lal.id == "238500000000005"


def test_daily_campaign_rows_are_one_per_campaign_per_day() -> None:
    rows = client.get_insights(req(date(2026, 1, 1), date(2026, 1, 7)))
    assert len(rows) == 70  # 10 campaigns x 7 days
    assert len({(r.campaign_id, r.date_start) for r in rows}) == 70
    assert all(r.spend > 0 for r in rows)
    assert all(r.date_start == r.date_stop for r in rows)


def test_account_level_reconciles_with_campaign_level() -> None:
    since, until = date(2026, 3, 1), date(2026, 3, 31)
    campaign_rows = client.get_insights(req(since, until, level=Level.CAMPAIGN))
    account_rows = client.get_insights(req(since, until, level=Level.ACCOUNT))
    assert len(account_rows) == 31
    assert total_spend(account_rows) == pytest.approx(total_spend(campaign_rows), rel=1e-6)


def test_ad_level_reconciles_with_campaign_level() -> None:
    since, until = date(2025, 9, 1), date(2025, 9, 30)
    ad_rows = client.get_insights(req(since, until, level=Level.AD))
    campaign_rows = client.get_insights(req(since, until, level=Level.CAMPAIGN))
    assert len(ad_rows) == len(campaign_rows) * 2
    assert total_spend(ad_rows) == pytest.approx(total_spend(campaign_rows), rel=1e-6)


def test_monthly_increment_buckets_days() -> None:
    since, until = date(2026, 2, 1), date(2026, 4, 30)
    daily = client.get_insights(req(since, until, level=Level.ACCOUNT))
    monthly = client.get_insights(req(since, until, level=Level.ACCOUNT, time_increment="monthly"))
    assert {r.date_start for r in monthly} == {
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
    }
    assert total_spend(monthly) == pytest.approx(total_spend(daily), rel=1e-6)


def test_all_days_collapses_to_one_bucket() -> None:
    rows = client.get_insights(req(date(2026, 1, 1), date(2026, 1, 31), time_increment="all_days"))
    assert len(rows) == 10
    assert all(r.date_start == date(2026, 1, 1) and r.date_stop == date(2026, 1, 31) for r in rows)


def test_age_gender_breakdown_reconciles_with_topline() -> None:
    since, until = date(2026, 1, 1), date(2026, 1, 31)
    topline = client.get_insights(req(since, until, time_increment="monthly"))
    by_age_gender = client.get_insights(
        req(since, until, time_increment="monthly", breakdowns=(Breakdown.AGE, Breakdown.GENDER))
    )
    assert len(by_age_gender) == 10 * 6 * 3
    assert total_spend(by_age_gender) == pytest.approx(total_spend(topline), abs=5.0)


def test_requesting_only_age_aggregates_over_gender() -> None:
    since, until = date(2026, 1, 1), date(2026, 1, 31)
    by_age = client.get_insights(
        req(since, until, time_increment="monthly", breakdowns=(Breakdown.AGE,))
    )
    by_age_gender = client.get_insights(
        req(since, until, time_increment="monthly", breakdowns=(Breakdown.AGE, Breakdown.GENDER))
    )
    assert len(by_age) == 10 * 6
    assert all(r.gender is None for r in by_age)
    assert total_spend(by_age) == pytest.approx(total_spend(by_age_gender), rel=1e-6)


def test_region_and_platform_breakdowns_partition_the_same_total() -> None:
    since, until = date(2025, 11, 1), date(2025, 11, 30)
    by_region = client.get_insights(
        req(since, until, time_increment="monthly", breakdowns=(Breakdown.REGION,))
    )
    by_platform = client.get_insights(
        req(since, until, time_increment="monthly", breakdowns=(Breakdown.PUBLISHER_PLATFORM,))
    )
    assert total_spend(by_region) == pytest.approx(total_spend(by_platform), abs=5.0)


def test_unsupported_breakdown_combo_raises() -> None:
    with pytest.raises(MockMetaError, match="no cached breakdown extract"):
        client.get_insights(
            req(
                date(2026, 1, 1),
                date(2026, 1, 31),
                time_increment="monthly",
                breakdowns=(Breakdown.AGE, Breakdown.REGION),
            )
        )


def test_daily_breakdown_not_cached() -> None:
    with pytest.raises(MockMetaError, match="only cached at monthly"):
        client.get_insights(req(date(2026, 1, 1), date(2026, 1, 31), breakdowns=(Breakdown.AGE,)))


def test_breakdown_at_ad_level_not_cached() -> None:
    with pytest.raises(MockMetaError, match="only cached at campaign level"):
        client.get_insights(
            req(
                date(2026, 1, 1),
                date(2026, 1, 31),
                level=Level.AD,
                time_increment="monthly",
                breakdowns=(Breakdown.AGE,),
            )
        )


def test_missing_fixture_dir_raises() -> None:
    stray = MockMetaClient(fixtures_dir=Path("/nonexistent/meta"))
    with pytest.raises(MockMetaError, match="missing"):
        stray.get_insights(req(date(2026, 1, 1), date(2026, 1, 2)))
