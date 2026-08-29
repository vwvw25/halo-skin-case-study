from __future__ import annotations

import pytest

from meta_reporting.sources.meta import Strategy, classify
from meta_reporting.sources.meta.mock_client import MockMetaClient


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Prospecting — Broad", Strategy.PROSPECTING_BROAD),
        ("TOF | Cold | Acquisition", Strategy.PROSPECTING_BROAD),
        ("Prospecting — Interests (Skincare Stack)", Strategy.PROSPECTING_INTEREST),
        ("LAL 1% — Purchasers", Strategy.LOOKALIKE),
        ("US / Lookalike 3% / Static", Strategy.LOOKALIKE),
        ("Advantage+ Shopping", Strategy.ADVANTAGE_PLUS),
        ("ASC — evergreen", Strategy.ADVANTAGE_PLUS),
        ("Retargeting — 14d ATC/VC", Strategy.RETARGETING),
        ("DPA remarketing 180d", Strategy.RETARGETING),
        ("Brand — Video Views", Strategy.AWARENESS),
        ("Q3 Reach & Frequency", Strategy.AWARENESS),
        ("Some Random Campaign", Strategy.UNKNOWN),
    ],
)
def test_classify(name: str, expected: Strategy) -> None:
    assert classify(name) == expected


def test_every_seeded_campaign_classifies_to_a_known_strategy() -> None:
    for campaign in MockMetaClient().list_campaigns():
        assert classify(campaign.name) is not Strategy.UNKNOWN, campaign.name
