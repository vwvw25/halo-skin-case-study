"""Meta Marketing API source — real client, mock client, and shared types.

See docs/data-sources.md for how the real/mock seam works.
"""

from meta_reporting.sources.meta.base import MetaSource, get_meta_source
from meta_reporting.sources.meta.client import MetaAPIError, MetaClient
from meta_reporting.sources.meta.mock_client import MockMetaClient, MockMetaError
from meta_reporting.sources.meta.strategy import Strategy, classify
from meta_reporting.sources.meta.types import (
    Breakdown,
    Campaign,
    InsightsRequest,
    InsightsRow,
    Level,
)

__all__ = [
    "Breakdown",
    "Campaign",
    "InsightsRequest",
    "InsightsRow",
    "Level",
    "MetaAPIError",
    "MetaClient",
    "MetaSource",
    "MockMetaClient",
    "MockMetaError",
    "Strategy",
    "classify",
    "get_meta_source",
]
