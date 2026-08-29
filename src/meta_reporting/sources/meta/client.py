"""Real Meta Marketing API client.

Built to the documented Graph API contract (v21.0). Handles cursor pagination, transient-error
backoff, and Meta's error envelope. It is exercised in tests against synthetic responses; it has
not been run against a live ad account (see docs/data-sources.md).
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import Iterator, Mapping
from typing import Any

import requests

from meta_reporting.sources.meta.types import (
    Campaign,
    CampaignsResponse,
    InsightsRequest,
    InsightsResponse,
    InsightsRow,
)

_GRAPH_ROOT = "https://graph.facebook.com"

_INSIGHTS_FIELDS = (
    "account_id",
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "spend",
    "impressions",
    "clicks",
    "reach",
    "actions",
    "action_values",
)

_CAMPAIGN_FIELDS = ("id", "name", "objective", "status", "effective_status")

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503})


class MetaAPIError(RuntimeError):
    """A non-transient error response from the Graph API."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: int | None = None,
        subcode: int | None = None,
        fbtrace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.subcode = subcode
        self.fbtrace_id = fbtrace_id

    @classmethod
    def from_response(cls, response: requests.Response) -> MetaAPIError:
        payload: dict[str, Any] = {}
        with contextlib.suppress(ValueError, AttributeError):
            payload = response.json().get("error", {})
        return cls(
            payload.get("message", response.text or f"HTTP {response.status_code}"),
            status=response.status_code,
            code=payload.get("code"),
            subcode=payload.get("error_subcode"),
            fbtrace_id=payload.get("fbtrace_id"),
        )


class MetaClient:
    def __init__(
        self,
        *,
        access_token: str,
        ad_account_id: str,
        api_version: str = "v21.0",
        session: requests.Session | None = None,
        max_retries: int = 3,
        backoff_base: float = 1.5,
        page_limit: int = 500,
    ) -> None:
        self.access_token = access_token
        self.ad_account_id = _normalize_account_id(ad_account_id)
        self.api_version = api_version
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.page_limit = page_limit

    # --- public API -----------------------------------------------------------------------

    def get_insights(self, request: InsightsRequest) -> list[InsightsRow]:
        url = f"{_GRAPH_ROOT}/{self.api_version}/{self.ad_account_id}/insights"
        params = self._insights_params(request)
        return [
            row
            for page in self._paginate(url, params)
            for row in InsightsResponse.model_validate(page).data
        ]

    def list_campaigns(self) -> list[Campaign]:
        url = f"{_GRAPH_ROOT}/{self.api_version}/{self.ad_account_id}/campaigns"
        params = {"fields": ",".join(_CAMPAIGN_FIELDS), "limit": self.page_limit}
        return [
            campaign
            for page in self._paginate(url, params)
            for campaign in CampaignsResponse.model_validate(page).data
        ]

    # --- internals ------------------------------------------------------------------------

    def _insights_params(self, request: InsightsRequest) -> dict[str, str]:
        params = {
            "level": request.level.value,
            "fields": ",".join(_INSIGHTS_FIELDS),
            "time_range": json.dumps(
                {"since": request.since.isoformat(), "until": request.until.isoformat()}
            ),
            "time_increment": str(request.time_increment),
            "limit": str(self.page_limit),
        }
        if request.breakdowns:
            params["breakdowns"] = ",".join(b.value for b in request.breakdowns)
        return params

    def _paginate(self, url: str, params: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
        next_url: str | None = url
        next_params: Mapping[str, Any] | None = params
        while next_url:
            payload = self._get(next_url, next_params)
            yield payload
            next_url = payload.get("paging", {}).get("next")
            next_params = None  # the `next` URL already carries the full querystring

    def _get(self, url: str, params: Mapping[str, Any] | None) -> dict[str, Any]:
        # `params is None` means we are following a `paging.next` URL, which already carries the
        # full querystring (access token included) — don't re-attach anything.
        merged = None if params is None else {"access_token": self.access_token, **dict(params)}
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=merged, timeout=60)
            except requests.RequestException as exc:  # network blip
                last_exc = exc
                self._sleep(attempt)
                continue
            if response.status_code == 200:
                return response.json()  # type: ignore[no-any-return]
            if response.status_code in _RETRYABLE_STATUS and attempt < self.max_retries - 1:
                self._sleep(attempt, response)
                continue
            raise MetaAPIError.from_response(response)
        raise MetaAPIError(
            f"request to {url} failed after {self.max_retries} attempts: {last_exc}",
            status=0,
        )

    def _sleep(self, attempt: int, response: requests.Response | None = None) -> None:
        if response is not None and (retry_after := response.headers.get("Retry-After")):
            try:
                time.sleep(float(retry_after))
                return
            except ValueError:
                pass
        time.sleep(self.backoff_base**attempt)


def _normalize_account_id(ad_account_id: str) -> str:
    return ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
