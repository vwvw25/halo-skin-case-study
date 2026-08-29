"""Classify a campaign into an acquisition strategy from its name.

Meta has no native "strategy" field, so brands encode it in a naming convention. This mirrors
that: it is deliberately forgiving (case-insensitive substring matching) because real campaign
names are messy.
"""

from __future__ import annotations

from enum import StrEnum


class Strategy(StrEnum):
    PROSPECTING_BROAD = "prospecting_broad"
    PROSPECTING_INTEREST = "prospecting_interest"
    LOOKALIKE = "lookalike"
    ADVANTAGE_PLUS = "advantage_plus"
    RETARGETING = "retargeting"
    AWARENESS = "awareness"
    UNKNOWN = "unknown"


# checked in order; first match wins
_RULES: list[tuple[Strategy, tuple[str, ...]]] = [
    (Strategy.RETARGETING, ("retargeting", "remarketing", " rt ", "dpa", "atc/vc", "abandoned")),
    (Strategy.ADVANTAGE_PLUS, ("advantage+", "advantage plus", "asc", "adv+")),
    (Strategy.LOOKALIKE, ("lookalike", "lal", "look-alike", "similar audience")),
    (Strategy.AWARENESS, ("awareness", "video views", "reach", "brand", "thruplay")),
    (Strategy.PROSPECTING_INTEREST, ("interest", "interests", "detailed targeting", "stack")),
    (Strategy.PROSPECTING_BROAD, ("prospecting", "broad", "cold", "acquisition", "tof")),
]


def classify(campaign_name: str) -> Strategy:
    haystack = f" {campaign_name.lower()} "
    for strategy, needles in _RULES:
        if any(needle in haystack for needle in needles):
            return strategy
    return Strategy.UNKNOWN
