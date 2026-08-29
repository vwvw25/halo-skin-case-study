"""Mock Meta source.

Reads gzipped JSON fixtures that are stored in the same shape the Insights endpoint returns,
then does the filtering / time-bucketing / breakdown-rollup that Meta would do server-side. It
is not a canned-response stub: totals reconcile across levels and breakdowns because every
fixture is a partition of the same underlying simulation (see scripts/generate_meta_fixtures.py).

Fixtures shipped:
  * ``insights_daily.json.gz``            — ad x day, no breakdowns
  * ``insights_monthly_age_gender.json.gz`` — campaign x month x age x gender
  * ``insights_monthly_region.json.gz``    — campaign x month x region
  * ``insights_monthly_platform.json.gz``  — campaign x month x platform (publisher + position)
  * ``campaigns.json``

Breakdown reports are only cached at monthly granularity and campaign level — asking for a
combination that was not extracted raises :class:`MockMetaError`, the same way a real workflow
would need a fresh pull.
"""

from __future__ import annotations

import gzip
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from meta_reporting.sources.meta.types import (
    Breakdown,
    Campaign,
    InsightsRequest,
    InsightsRow,
    Level,
)

_DEFAULT_FIXTURES = Path(__file__).resolve().parents[4] / "fixtures" / "meta"

_BREAKDOWN_FIXTURE: dict[frozenset[Breakdown], str] = {
    frozenset(): "insights_daily",
    frozenset({Breakdown.AGE}): "insights_monthly_age_gender",
    frozenset({Breakdown.GENDER}): "insights_monthly_age_gender",
    frozenset({Breakdown.AGE, Breakdown.GENDER}): "insights_monthly_age_gender",
    frozenset({Breakdown.REGION}): "insights_monthly_region",
    frozenset({Breakdown.PUBLISHER_PLATFORM}): "insights_monthly_platform",
    frozenset({Breakdown.PLATFORM_POSITION}): "insights_monthly_platform",
    frozenset(
        {Breakdown.PUBLISHER_PLATFORM, Breakdown.PLATFORM_POSITION}
    ): "insights_monthly_platform",
}

_LEVEL_KEYS: dict[Level, tuple[str, ...]] = {
    Level.ACCOUNT: ("account_id",),
    Level.CAMPAIGN: ("account_id", "campaign_id", "campaign_name"),
    Level.ADSET: ("account_id", "campaign_id", "campaign_name", "adset_id", "adset_name"),
    Level.AD: (
        "account_id",
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
    ),
}

_METRICS = ("spend", "impressions", "clicks", "reach")


class MockMetaError(RuntimeError):
    """Raised when the requested slice was not extracted into a fixture."""


class MockMetaClient:
    def __init__(self, *, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or _DEFAULT_FIXTURES

    def list_campaigns(self) -> list[Campaign]:
        raw = json.loads((self.fixtures_dir / "campaigns.json").read_text())
        return [Campaign.model_validate(row) for row in raw]

    def get_insights(self, request: InsightsRequest) -> list[InsightsRow]:
        key = frozenset(request.breakdowns)
        fixture = _BREAKDOWN_FIXTURE.get(key)
        if fixture is None:
            raise MockMetaError(
                f"no cached breakdown extract for {sorted(b.value for b in key)}; "
                f"available: {sorted({v for v in _BREAKDOWN_FIXTURE.values()})}"
            )

        monthly_only = fixture != "insights_daily"
        if monthly_only:
            if request.time_increment not in ("monthly", "all_days"):
                raise MockMetaError(
                    "breakdown reports are only cached at monthly granularity "
                    f"(got time_increment={request.time_increment!r})"
                )
            if request.level not in (Level.ACCOUNT, Level.CAMPAIGN):
                raise MockMetaError(
                    f"breakdown reports are only cached at campaign level (got {request.level})"
                )

        rows = _load_fixture(self.fixtures_dir, fixture)
        in_window = [
            r for r in rows if request.since <= date.fromisoformat(r["date_start"]) <= request.until
        ]
        wanted_dims = tuple(b.value for b in request.breakdowns)
        return _aggregate(in_window, request, wanted_dims)


# --- fixture loading -------------------------------------------------------------------------


@cache
def _load_fixture_cached(path_str: str) -> tuple[dict[str, Any], ...]:
    path = Path(path_str)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return tuple(json.load(fh))


def _load_fixture(fixtures_dir: Path, name: str) -> tuple[dict[str, Any], ...]:
    path = fixtures_dir / f"{name}.json.gz"
    if not path.exists():
        raise MockMetaError(f"fixture {path} is missing — run scripts/generate_meta_fixtures.py")
    return _load_fixture_cached(str(path))


# --- aggregation ----------------------------------------------------------------------------


def _aggregate(
    rows: Iterable[dict[str, Any]],
    request: InsightsRequest,
    wanted_dims: tuple[str, ...],
) -> list[InsightsRow]:
    id_keys = _LEVEL_KEYS[request.level]
    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}

    for row in rows:
        day = date.fromisoformat(row["date_start"])
        b_start, b_stop = _bucket_bounds(day, request)
        dim_values = tuple(row.get(dim) for dim in wanted_dims)
        id_values = tuple(row.get(k) for k in id_keys)
        key = (b_start, b_stop, *id_values, *dim_values)

        acc = buckets.get(key)
        if acc is None:
            acc = {
                "date_start": b_start.isoformat(),
                "date_stop": b_stop.isoformat(),
                **{k: row.get(k) for k in id_keys},
                **{dim: row.get(dim) for dim in wanted_dims},
                **dict.fromkeys(_METRICS, 0.0),
                "_actions": defaultdict(float),
                "_action_values": defaultdict(float),
            }
            buckets[key] = acc

        for metric in _METRICS:
            acc[metric] += _num(row.get(metric))
        for entry in row.get("actions", []):
            acc["_actions"][entry["action_type"]] += _num(entry["value"])
        for entry in row.get("action_values", []):
            acc["_action_values"][entry["action_type"]] += _num(entry["value"])

    return [_finalize(acc) for acc in buckets.values()]


def _finalize(acc: dict[str, Any]) -> InsightsRow:
    acc["spend"] = round(acc["spend"], 2)
    for metric in ("impressions", "clicks", "reach"):
        acc[metric] = round(acc[metric])
    acc["actions"] = [
        {"action_type": t, "value": round(v, 4)} for t, v in sorted(acc.pop("_actions").items())
    ]
    acc["action_values"] = [
        {"action_type": t, "value": round(v, 2)}
        for t, v in sorted(acc.pop("_action_values").items())
    ]
    return InsightsRow.model_validate(acc)


def _bucket_bounds(day: date, request: InsightsRequest) -> tuple[date, date]:
    inc = request.time_increment
    if inc == "all_days":
        return request.since, request.until
    if inc == "monthly":
        start = day.replace(day=1)
        end = _month_end(start)
        return max(start, request.since), min(end, request.until)
    if inc == 1:
        return day, day
    span = int(inc)
    offset = (day - request.since).days // span * span
    start = request.since + timedelta(days=offset)
    end = min(start + timedelta(days=span - 1), request.until)
    return start, end


def _month_end(first_of_month: date) -> date:
    if first_of_month.month == 12:
        return first_of_month.replace(year=first_of_month.year + 1, month=1) - timedelta(days=1)
    return first_of_month.replace(month=first_of_month.month + 1) - timedelta(days=1)


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
