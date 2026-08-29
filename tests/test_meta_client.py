from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from meta_reporting.sources.meta import InsightsRequest, MetaAPIError, MetaClient
from meta_reporting.sources.meta.types import Breakdown, Level


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict[str, Any] | None = None,
        *,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, *responses: FakeResponse) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(
        self, url: str, params: dict[str, Any] | None = None, timeout: int | None = None
    ) -> FakeResponse:
        self.calls.append({"url": url, "params": params})
        return self._responses.pop(0)


def _client(session: FakeSession, **kw: Any) -> MetaClient:
    return MetaClient(
        access_token="tok",
        ad_account_id="123",
        session=session,  # type: ignore[arg-type]
        backoff_base=0.0,
        **kw,
    )


def test_account_id_normalized() -> None:
    assert _client(FakeSession()).ad_account_id == "act_123"
    assert MetaClient(access_token="t", ad_account_id="act_9").ad_account_id == "act_9"


def test_insights_params_are_built_correctly() -> None:
    session = FakeSession(FakeResponse(200, {"data": []}))
    _client(session).get_insights(
        InsightsRequest(
            since=date(2026, 1, 1),
            until=date(2026, 1, 31),
            level=Level.AD,
            time_increment="monthly",
            breakdowns=(Breakdown.AGE, Breakdown.GENDER),
        )
    )
    params = session.calls[0]["params"]
    assert params["level"] == "ad"
    assert params["time_increment"] == "monthly"
    assert params["breakdowns"] == "age,gender"
    assert json.loads(params["time_range"]) == {"since": "2026-01-01", "until": "2026-01-31"}
    assert "spend" in params["fields"]
    assert params["access_token"] == "tok"


def test_pagination_follows_next() -> None:
    page1 = FakeResponse(
        200,
        {
            "data": [{"date_start": "2026-01-01", "date_stop": "2026-01-01", "spend": "10"}],
            "paging": {"next": "https://graph.facebook.com/next-page"},
        },
    )
    page2 = FakeResponse(
        200,
        {"data": [{"date_start": "2026-01-02", "date_stop": "2026-01-02", "spend": "20"}]},
    )
    session = FakeSession(page1, page2)
    rows = _client(session).get_insights(
        InsightsRequest(
            since=date(2026, 1, 1),
            until=date(2026, 1, 2),
        )
    )
    assert [r.spend for r in rows] == [10.0, 20.0]
    assert session.calls[1]["url"] == "https://graph.facebook.com/next-page"
    assert session.calls[1]["params"] is None


def test_retries_then_succeeds_on_503() -> None:
    session = FakeSession(
        FakeResponse(503, text="try later"),
        FakeResponse(200, {"data": []}),
    )
    rows = _client(session).get_insights(
        InsightsRequest(
            since=date(2026, 1, 1),
            until=date(2026, 1, 1),
        )
    )
    assert rows == []
    assert len(session.calls) == 2


def test_non_retryable_error_raises_parsed() -> None:
    session = FakeSession(
        FakeResponse(
            400,
            {
                "error": {
                    "message": "Invalid parameter",
                    "code": 100,
                    "error_subcode": 1487056,
                    "fbtrace_id": "AbCdEf",
                }
            },
        )
    )
    with pytest.raises(MetaAPIError) as excinfo:
        _client(session).get_insights(
            InsightsRequest(
                since=date(2026, 1, 1),
                until=date(2026, 1, 1),
            )
        )
    assert excinfo.value.status == 400
    assert excinfo.value.code == 100
    assert excinfo.value.fbtrace_id == "AbCdEf"
    assert "Invalid parameter" in str(excinfo.value)


def test_gives_up_after_max_retries() -> None:
    session = FakeSession(*[FakeResponse(503) for _ in range(3)])
    with pytest.raises(MetaAPIError):
        _client(session, max_retries=3).get_insights(
            InsightsRequest(
                since=date(2026, 1, 1),
                until=date(2026, 1, 1),
            )
        )
    assert len(session.calls) == 3


def test_list_campaigns_parses() -> None:
    session = FakeSession(
        FakeResponse(
            200,
            {
                "data": [
                    {"id": "1", "name": "Prospecting — Broad", "objective": "OUTCOME_SALES"},
                    {"id": "2", "name": "Retargeting — 14d", "objective": "OUTCOME_SALES"},
                ]
            },
        )
    )
    campaigns = _client(session).list_campaigns()
    assert [c.name for c in campaigns] == ["Prospecting — Broad", "Retargeting — 14d"]
