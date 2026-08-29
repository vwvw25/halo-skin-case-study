"""Typed models for the Meta Marketing API Insights endpoint.

Field names and the response envelope match what
``GET /{ad-account}/insights`` and ``GET /{ad-account}/campaigns`` actually return, including
the quirk that every numeric metric comes back as a **string**. Pydantic coerces them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- request-side ----------------------------------------------------------------------------


class Level(StrEnum):
    ACCOUNT = "account"
    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"


class Breakdown(StrEnum):
    AGE = "age"
    GENDER = "gender"
    REGION = "region"
    PUBLISHER_PLATFORM = "publisher_platform"
    PLATFORM_POSITION = "platform_position"


TimeIncrement = Literal[1, 7, 28, "monthly", "all_days"]


@dataclass(frozen=True, slots=True)
class InsightsRequest:
    """A single Insights query. Mirrors the meaningful subset of the endpoint's parameters."""

    since: date
    until: date
    level: Level = Level.CAMPAIGN
    time_increment: TimeIncrement = 1
    breakdowns: tuple[Breakdown, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.until < self.since:
            raise ValueError(f"until ({self.until}) is before since ({self.since})")


# --- response-side -------------------------------------------------------------------------


class ActionStat(BaseModel):
    """One entry in the ``actions`` / ``action_values`` arrays."""

    model_config = ConfigDict(extra="ignore")

    action_type: str
    value: float


class InsightsRow(BaseModel):
    """One row of the Insights ``data`` array.

    Which fields are populated depends on ``level`` (ad rows carry adset/campaign ids too) and
    ``breakdowns`` (the dimension columns). Everything optional defaults to ``None`` / ``0``.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    date_start: date
    date_stop: date

    account_id: str | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    adset_id: str | None = None
    adset_name: str | None = None
    ad_id: str | None = None
    ad_name: str | None = None

    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    reach: int = 0

    # breakdown dimensions
    age: str | None = None
    gender: str | None = None
    region: str | None = None
    publisher_platform: str | None = None
    platform_position: str | None = None

    actions: list[ActionStat] = Field(default_factory=list)
    action_values: list[ActionStat] = Field(default_factory=list)

    def _action(self, source: list[ActionStat], action_type: str) -> float:
        return sum(a.value for a in source if a.action_type == action_type)

    @property
    def purchases(self) -> float:
        return self._action(self.actions, "purchase")

    @property
    def purchase_value(self) -> float:
        return self._action(self.action_values, "purchase")

    @property
    def link_clicks(self) -> float:
        return self._action(self.actions, "link_click")

    @property
    def landing_page_views(self) -> float:
        return self._action(self.actions, "landing_page_view")

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def cpm(self) -> float:
        return 1000 * self.spend / self.impressions if self.impressions else 0.0

    @property
    def cpc(self) -> float:
        return self.spend / self.clicks if self.clicks else 0.0


class Cursors(BaseModel):
    model_config = ConfigDict(extra="ignore")
    before: str | None = None
    after: str | None = None


class Paging(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cursors: Cursors | None = None
    next: str | None = None


class InsightsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[InsightsRow] = Field(default_factory=list)
    paging: Paging | None = None


class Campaign(BaseModel):
    """A row from ``GET /{ad-account}/campaigns``.

    ``strategy`` is not a native Meta field — it is parsed from a naming convention in
    ``campaign_name`` (``"LAL 1% — Purchasers"`` -> ``lookalike``). See
    :func:`meta_reporting.sources.meta.strategy.classify`.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    objective: str | None = None
    status: str | None = None
    effective_status: str | None = None


class CampaignsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[Campaign] = Field(default_factory=list)
    paging: Paging | None = None
