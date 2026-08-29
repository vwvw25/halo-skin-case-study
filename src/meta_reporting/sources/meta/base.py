"""The ``MetaSource`` protocol and a factory that returns the right implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from meta_reporting.config import MetaConfig, SourceMode
from meta_reporting.sources.meta.types import Campaign, InsightsRequest, InsightsRow


@runtime_checkable
class MetaSource(Protocol):
    """Everything the pipeline needs from Meta.

    Implemented by ``MetaClient`` (real) and ``MockMetaClient`` (fixtures).
    """

    def get_insights(self, request: InsightsRequest) -> list[InsightsRow]:
        """Return one row per (entity x time bucket x breakdown combination) for the request."""
        ...

    def list_campaigns(self) -> list[Campaign]:
        """Return every campaign in the ad account (active or not)."""
        ...


def get_meta_source(config: MetaConfig, *, fixtures_dir: Path | None = None) -> MetaSource:
    if config.mode is SourceMode.LIVE:
        from meta_reporting.sources.meta.client import MetaClient

        assert config.access_token is not None  # guaranteed by MetaConfig.from_env
        assert config.ad_account_id is not None
        return MetaClient(
            access_token=config.access_token,
            ad_account_id=config.ad_account_id,
            api_version=config.api_version,
        )

    from meta_reporting.sources.meta.mock_client import MockMetaClient

    return MockMetaClient(fixtures_dir=fixtures_dir)
