from __future__ import annotations

import json
from pathlib import Path

import pytest

from meta_reporting.pipeline import main


def _run(tmp_path: Path, *args: str) -> int:
    return main(
        [
            *args,
            "--out",
            str(tmp_path / "reports"),
            "--data-dir",
            str(tmp_path / "data"),
        ]
    )


def test_weekly_pipeline_produces_pdf_and_dashboard(tmp_path: Path) -> None:
    assert _run(tmp_path, "weekly") == 0
    pdf = tmp_path / "reports" / "halo-skin-weekly-2026-07-31.pdf"
    assert pdf.read_bytes()[:5] == b"%PDF-"
    dashboard = json.loads((tmp_path / "data" / "dashboard.json").read_text())
    assert dashboard["as_of"] == "2026-07-31"
    assert (tmp_path / "data" / "snapshots" / "2026-07-31.json").exists()


def test_monthly_pipeline_with_custom_as_of(tmp_path: Path) -> None:
    assert _run(tmp_path, "monthly", "--as-of", "2026-06-30") == 0
    assert (tmp_path / "reports" / "halo-skin-monthly-2026-06-30.pdf").exists()


def test_deliver_flag_runs_local_delivery(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(tmp_path, "weekly", "--deliver") == 0
    out = capsys.readouterr().out
    assert "deliver local ->" in out and "[ok]" in out


def test_bad_cadence_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _run(tmp_path, "quarterly")
