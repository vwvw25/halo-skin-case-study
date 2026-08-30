from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from meta_reporting.emit import build_dashboard_data, write_dashboard_data
from meta_reporting.sources.meta import MockMetaClient
from meta_reporting.sources.shopify import MockShopifyClient

AS_OF = date(2026, 7, 31)


@pytest.fixture(scope="module")
def data() -> dict[str, object]:
    return build_dashboard_data(MockMetaClient(), MockShopifyClient(), as_of=AS_OF)


def test_top_level_shape(data: dict[str, object]) -> None:
    assert data["brand"] == "Halo Skin"
    assert data["as_of"] == "2026-07-31"
    assert {
        "assumptions",
        "headline",
        "weekly_trend",
        "monthly_spend",
        "maturation_curve",
        "cohort_ltv",
        "ltv_cac_by_campaign",
        "ltv_cac_by_strategy",
        "capture_by_strategy",
    } <= data.keys()


def test_headline_numbers_are_sane(data: dict[str, object]) -> None:
    h = data["headline"]
    assert 1.5 <= h["blended_ltv_cac"] <= 4.0
    assert 0.16 <= h["target_cohort_share"] <= 0.26
    assert 18_000 <= h["customers_total"] <= 24_000


def test_series_are_populated_and_json_clean(data: dict[str, object]) -> None:
    assert len(data["weekly_trend"]) > 40
    assert len(data["maturation_curve"]) == data["assumptions"]["ltv_horizon_months"] + 1
    assert {r["name"] for r in data["ltv_cac_by_campaign"]} >= {"LAL 1% — High-AOV Purchasers"}
    # fully serialisable, no NaN / Timestamp leaked
    dumped = json.dumps(data)
    assert "NaN" not in dumped
    assert "Timestamp" not in dumped


def test_write_creates_latest_and_snapshot(data: dict[str, object], tmp_path: Path) -> None:
    latest = write_dashboard_data(data, tmp_path)
    assert latest == tmp_path / "dashboard.json"
    assert json.loads(latest.read_text())["as_of"] == "2026-07-31"
    snapshot = tmp_path / "snapshots" / "2026-07-31.json"
    assert json.loads(snapshot.read_text())["brand"] == "Halo Skin"


def test_capture_by_strategy_has_realized_and_predicted(data: dict[str, object]) -> None:
    lookalike = next(
        r for r in data["capture_by_strategy"] if r["acquisition_strategy"] == "lookalike"
    )
    assert lookalike["realized_capture_rate"] > lookalike["predicted_capture_rate"]
    broad = next(
        r for r in data["capture_by_strategy"] if r["acquisition_strategy"] == "prospecting_broad"
    )
    assert lookalike["realized_capture_rate"] > broad["realized_capture_rate"]


def test_cohort_triangle_shape(data: dict[str, object]) -> None:
    tri = data["cohort_triangle"]
    assert tri["months"][0] == 0
    rows = tri["rows"]
    assert len(rows) >= 12
    first, last = rows[0], rows[-1]

    # oldest cohort: full history, older customers, high repeat
    assert sum(1 for v in first["revenue"] if v is not None) == len(tri["months"])
    assert first["repeat_rate"] > last["repeat_rate"]

    # newest cohort: only month 0 observed
    assert sum(1 for v in last["revenue"] if v is not None) == 1

    # cumulative revenue rises and stays above cumulative margin
    for row in rows:
        rev = [v for v in row["revenue"] if v is not None]
        cm = [v for v in row["cm"] if v is not None]
        assert rev == sorted(rev)
        assert all(c < r for c, r in zip(cm, rev, strict=True))
