from __future__ import annotations

import warnings
from datetime import date
from pathlib import Path

import pytest

from meta_reporting.report import (
    ReportContext,
    build_context,
    build_report,
    render_html,
    render_pdf,
)
from meta_reporting.sources.meta import MockMetaClient
from meta_reporting.sources.shopify import MockShopifyClient

warnings.filterwarnings("ignore", category=FutureWarning)

META = MockMetaClient()
SHOPIFY = MockShopifyClient()
AS_OF = date(2026, 7, 31)


@pytest.fixture(scope="module")
def weekly() -> ReportContext:
    return build_context(META, SHOPIFY, as_of=AS_OF, cadence="weekly")


@pytest.fixture(scope="module")
def monthly() -> ReportContext:
    return build_context(META, SHOPIFY, as_of=AS_OF, cadence="monthly")


def test_weekly_context(weekly: ReportContext) -> None:
    assert weekly.cadence == "weekly"
    assert len(weekly.kpis) == 5
    assert {"spend_cac_trend", "funnel", "predicted_capture"} <= weekly.charts.keys()
    assert all(svg.lstrip().startswith("<") and "svg" in svg for svg in weekly.charts.values())
    assert weekly.narrative and weekly.recommendations
    assert weekly.tables[0].rows


def test_monthly_context(monthly: ReportContext) -> None:
    assert monthly.cadence == "monthly"
    assert {
        "cohort_maturation",
        "maturation_curve",
        "ltv_cac_by_strategy",
        "capture_by_strategy",
    } <= (monthly.charts.keys())
    assert len(monthly.tables) == 2
    assert any("LAL 1% — High-AOV" in " ".join(row) for row in monthly.tables[0].rows)


def test_monthly_narrative_flags_the_retargeting_trap(monthly: ReportContext) -> None:
    joined = " ".join(monthly.narrative + monthly.recommendations)
    assert "retargeting" in joined.lower()
    assert "care" in joined.lower() or "reacquires" in joined.lower()
    # never recommends scaling budget into retargeting or awareness
    for rec in monthly.recommendations:
        if rec.lower().startswith("scale budget"):
            assert "retargeting" not in rec.lower()
            assert "video views" not in rec.lower()


def test_weekly_does_not_push_budget_to_retargeting(weekly: ReportContext) -> None:
    for rec in weekly.recommendations:
        if "shift budget" in rec.lower():
            assert "among acquisition strategies" in rec.lower()


def test_render_html(monthly: ReportContext) -> None:
    html = render_html(monthly)
    assert "Halo" in html and "Skin" in html
    assert "June 2026" in html
    assert "<svg" in html


def test_render_pdf_bytes(weekly: ReportContext) -> None:
    pdf = render_pdf(weekly)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 10_000


def test_build_report_writes_file(tmp_path: Path) -> None:
    path = build_report(META, SHOPIFY, as_of=AS_OF, cadence="weekly", out_dir=tmp_path)
    assert path.exists() and path.suffix == ".pdf"
    assert path.read_bytes()[:5] == b"%PDF-"


def test_bad_cadence_raises() -> None:
    with pytest.raises(ValueError, match="quarterly"):
        build_context(META, SHOPIFY, as_of=AS_OF, cadence="quarterly")
