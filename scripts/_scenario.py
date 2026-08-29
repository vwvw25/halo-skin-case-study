"""Shared scenario definition for Halo Skin's mock data.

Both fixture generators import this so the Meta ad numbers and the Shopify customer records
describe the same business:

  * ``CAMPAIGNS``            — the ad account roster, with the economic + demographic knobs
  * ``daily_cell()``         — deterministic per-(campaign, day) metrics
  * ``AGE_BUCKETS`` etc.     — the breakdown dimensions and per-campaign skews

Determinism: every random draw is seeded from ``SEED`` plus a stable CRC of the cell's keys, so
output does not depend on iteration order and regenerating is a no-op in git.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import date, timedelta
from random import Random

SEED = 20260829
ACCOUNT_ID = "act_1088231947624015"
CURRENCY = "USD"

START = date(2025, 6, 1)
END = date(2026, 7, 31)


def all_days() -> list[date]:
    return [START + timedelta(days=i) for i in range((END - START).days + 1)]


def months() -> list[date]:
    out: list[date] = []
    cur = START.replace(day=1)
    while cur <= END:
        out.append(cur)
        cur = (cur.replace(day=28) + timedelta(days=7)).replace(day=1)
    return out


# --- breakdown dimensions ------------------------------------------------------------------

AGE_BUCKETS = ("18-24", "25-34", "35-44", "45-54", "55-64", "65+")
GENDERS = ("female", "male", "unknown")
REGIONS = ("California", "New York", "Texas", "Florida", "Illinois", "Washington", "Other")
PLATFORMS: tuple[tuple[str, str], ...] = (
    ("instagram", "feed"),
    ("instagram", "story"),
    ("instagram", "reels"),
    ("facebook", "feed"),
    ("facebook", "story"),
    ("audience_network", "classic"),
)

# named skew profiles: relative weights, normalized at use
_AGE_PROFILES = {
    "young": {"18-24": 3, "25-34": 4, "35-44": 2, "45-54": 1, "55-64": 0.4, "65+": 0.2},
    "core": {"18-24": 1, "25-34": 3, "35-44": 4, "45-54": 2.5, "55-64": 1, "65+": 0.5},
    "mature": {"18-24": 0.4, "25-34": 1.5, "35-44": 3, "45-54": 3.5, "55-64": 2, "65+": 1},
    "flat": dict.fromkeys(AGE_BUCKETS, 1.0),
}
_GENDER_PROFILES = {
    "skincare": {"female": 8, "male": 1.5, "unknown": 0.5},
    "broad": {"female": 6, "male": 3, "unknown": 1},
}
_REGION_PROFILES = {
    "coastal": {
        "California": 4,
        "New York": 3,
        "Washington": 2,
        "Illinois": 1.5,
        "Florida": 1.5,
        "Texas": 1.5,
        "Other": 3,
    },
    "even": {r: 1.0 for r in REGIONS},
}
_PLATFORM_PROFILES = {
    "ig_first": {
        ("instagram", "reels"): 4,
        ("instagram", "feed"): 3,
        ("instagram", "story"): 1.5,
        ("facebook", "feed"): 2,
        ("facebook", "story"): 0.8,
        ("audience_network", "classic"): 0.5,
    },
    "fb_lean": {
        ("instagram", "reels"): 1.5,
        ("instagram", "feed"): 2,
        ("instagram", "story"): 1,
        ("facebook", "feed"): 4,
        ("facebook", "story"): 1.5,
        ("audience_network", "classic"): 2,
    },
}


def normalized(weights: dict) -> dict:
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def age_weights(profile: str) -> dict[str, float]:
    return normalized({b: _AGE_PROFILES[profile].get(b, 0.0) for b in AGE_BUCKETS})


def gender_weights(profile: str) -> dict[str, float]:
    return normalized(_GENDER_PROFILES[profile])


def region_weights(profile: str) -> dict[str, float]:
    return normalized(_REGION_PROFILES[profile])


def platform_weights(profile: str) -> dict[tuple[str, str], float]:
    return normalized(_PLATFORM_PROFILES[profile])


# --- campaign roster ----------------------------------------------------------------------

_OUTCOME_SALES = "OUTCOME_SALES"
_OUTCOME_AWARENESS = "OUTCOME_AWARENESS"


@dataclass(frozen=True, slots=True)
class CampaignSpec:
    id: str
    name: str
    objective: str
    launch: date
    end: date | None
    daily_budget: float
    budget_shape: str  # flat | scale | decay | spike_test
    cpm: float
    ctr: float  # link clicks / impressions
    cvr: float  # purchases / link click (first order)
    lpv_rate: float  # landing page views / link click
    fatigue_per_month: float
    refresh: date | None
    aov: float
    new_customer_share: float  # of purchases, fraction that are new customers
    target_cohort_rate: float  # of NEW customers, fraction that become high-LTV
    age_profile: str
    gender_profile: str
    region_profile: str
    platform_profile: str

    def active_on(self, day: date) -> bool:
        return self.launch <= day and (self.end is None or day <= self.end)


def _d(y: int, m: int, day: int) -> date:
    return date(y, m, day)


CAMPAIGNS: tuple[CampaignSpec, ...] = (
    CampaignSpec(
        id="238500000000001",
        name="Prospecting — Broad",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=420.0,
        budget_shape="flat",
        cpm=9.0,
        ctr=0.011,
        cvr=0.021,
        lpv_rate=0.82,
        fatigue_per_month=0.22,
        refresh=_d(2026, 3, 2),
        aov=46.0,
        new_customer_share=0.86,
        target_cohort_rate=0.09,
        age_profile="young",
        gender_profile="broad",
        region_profile="even",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000002",
        name="Prospecting — Interests (Skincare Stack)",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=300.0,
        budget_shape="flat",
        cpm=10.5,
        ctr=0.013,
        cvr=0.026,
        lpv_rate=0.85,
        fatigue_per_month=0.16,
        refresh=_d(2026, 1, 15),
        aov=52.0,
        new_customer_share=0.8,
        target_cohort_rate=0.15,
        age_profile="core",
        gender_profile="skincare",
        region_profile="even",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000003",
        name="LAL 1% — Purchasers",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=260.0,
        budget_shape="scale",
        cpm=11.5,
        ctr=0.015,
        cvr=0.037,
        lpv_rate=0.88,
        fatigue_per_month=0.08,
        refresh=None,
        aov=58.0,
        new_customer_share=0.74,
        target_cohort_rate=0.24,
        age_profile="core",
        gender_profile="skincare",
        region_profile="coastal",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000004",
        name="LAL 3% — Purchasers",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=220.0,
        budget_shape="decay",
        cpm=10.8,
        ctr=0.014,
        cvr=0.03,
        lpv_rate=0.86,
        fatigue_per_month=0.14,
        refresh=None,
        aov=54.0,
        new_customer_share=0.78,
        target_cohort_rate=0.17,
        age_profile="core",
        gender_profile="skincare",
        region_profile="coastal",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000005",
        name="LAL 1% — High-AOV Purchasers",
        objective=_OUTCOME_SALES,
        launch=_d(2025, 8, 15),
        end=None,
        daily_budget=110.0,
        budget_shape="scale",
        cpm=13.5,
        ctr=0.016,
        cvr=0.041,
        lpv_rate=0.9,
        fatigue_per_month=0.07,
        refresh=None,
        aov=76.0,
        new_customer_share=0.7,
        target_cohort_rate=0.33,
        age_profile="mature",
        gender_profile="skincare",
        region_profile="coastal",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000006",
        name="Advantage+ Shopping",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=520.0,
        budget_shape="scale",
        cpm=9.8,
        ctr=0.012,
        cvr=0.028,
        lpv_rate=0.83,
        fatigue_per_month=0.1,
        refresh=None,
        aov=51.0,
        new_customer_share=0.68,
        target_cohort_rate=0.16,
        age_profile="core",
        gender_profile="skincare",
        region_profile="even",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000007",
        name="Retargeting — 14d ATC/VC",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=140.0,
        budget_shape="flat",
        cpm=8.0,
        ctr=0.023,
        cvr=0.09,
        lpv_rate=0.8,
        fatigue_per_month=0.12,
        refresh=_d(2026, 2, 1),
        aov=49.0,
        new_customer_share=0.22,
        target_cohort_rate=0.12,
        age_profile="core",
        gender_profile="skincare",
        region_profile="even",
        platform_profile="fb_lean",
    ),
    CampaignSpec(
        id="238500000000008",
        name="Retargeting — 180d All Visitors",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=90.0,
        budget_shape="flat",
        cpm=7.2,
        ctr=0.019,
        cvr=0.06,
        lpv_rate=0.78,
        fatigue_per_month=0.1,
        refresh=None,
        aov=47.0,
        new_customer_share=0.3,
        target_cohort_rate=0.1,
        age_profile="flat",
        gender_profile="skincare",
        region_profile="even",
        platform_profile="fb_lean",
    ),
    CampaignSpec(
        id="238500000000009",
        name="Creative Testing — TOF",
        objective=_OUTCOME_SALES,
        launch=START,
        end=None,
        daily_budget=80.0,
        budget_shape="spike_test",
        cpm=10.0,
        ctr=0.012,
        cvr=0.02,
        lpv_rate=0.8,
        fatigue_per_month=0.05,
        refresh=None,
        aov=45.0,
        new_customer_share=0.88,
        target_cohort_rate=0.11,
        age_profile="young",
        gender_profile="broad",
        region_profile="even",
        platform_profile="ig_first",
    ),
    CampaignSpec(
        id="238500000000010",
        name="Brand — Video Views",
        objective=_OUTCOME_AWARENESS,
        launch=START,
        end=None,
        daily_budget=95.0,
        budget_shape="flat",
        cpm=5.5,
        ctr=0.006,
        cvr=0.004,
        lpv_rate=0.6,
        fatigue_per_month=0.06,
        refresh=None,
        aov=44.0,
        new_customer_share=0.9,
        target_cohort_rate=0.08,
        age_profile="young",
        gender_profile="broad",
        region_profile="even",
        platform_profile="ig_first",
    ),
)

CAMPAIGNS_BY_ID = {c.id: c for c in CAMPAIGNS}


def ads_for(spec: CampaignSpec) -> list[tuple[str, str, str, str, float]]:
    """(adset_id, adset_name, ad_id, ad_name, spend_share) — one adset, two ads per campaign.

    Every id is prefixed with the full campaign id so ids are unique across the account.
    """
    adset_id = f"{spec.id}01"
    adset_name = f"{spec.name} / Broad 18-65"
    return [
        (adset_id, adset_name, f"{spec.id}0101", f"{spec.name} — Ad A (UGC)", 0.6),
        (adset_id, adset_name, f"{spec.id}0102", f"{spec.name} — Ad B (Static)", 0.4),
    ]


# --- per-cell simulation ------------------------------------------------------------------

# global calibration knob: nudges blended first-order CAC into a realistic band (~$30-45)
_CVR_BOOST = 1.4


def _rng(*parts: object) -> Random:
    key = ":".join(str(p) for p in parts).encode()
    return Random(SEED ^ zlib.crc32(key))


def _season(day: date) -> float:
    # Q4 lift, January hangover, mild summer softness
    month_mult = {
        1: 0.88,
        2: 0.95,
        3: 1.0,
        4: 1.0,
        5: 0.98,
        6: 0.95,
        7: 0.93,
        8: 0.96,
        9: 1.03,
        10: 1.08,
        11: 1.22,
        12: 1.15,
    }
    return month_mult[day.month]


def _weekend(day: date) -> float:
    return 0.82 if day.weekday() >= 5 else 1.03


def _months_between(a: date, b: date) -> float:
    return (b - a).days / 30.4


def _budget_mult(spec: CampaignSpec, day: date) -> float:
    ramp = min(1.0, (day - spec.launch).days / 14 + 0.15)
    life = _months_between(spec.launch, day)
    if spec.budget_shape == "scale":
        shape = 1.0 + 0.9 / (1 + pow(2.718, -(life - 6)))  # sigmoid, ~2x by month 6
    elif spec.budget_shape == "decay":
        shape = max(0.45, 1.0 - 0.05 * life)
    elif spec.budget_shape == "spike_test":
        shape = _rng(spec.id, day, "spike").uniform(0.35, 1.7)
    else:
        shape = 1.0
    return ramp * shape


def _fatigue_mult(spec: CampaignSpec, day: date) -> float:
    """CTR decay since launch / last creative refresh. Floored so it never fully collapses."""
    anchor = spec.launch
    if spec.refresh is not None and spec.refresh <= day:
        anchor = spec.refresh
    months = max(0.0, _months_between(anchor, day))
    return max(0.62, 1.0 / (1.0 + spec.fatigue_per_month * months))


@dataclass(frozen=True, slots=True)
class DailyCell:
    # counts are conceptually integers but stored as float so the fixture generator can
    # split a cell across breakdown dimensions without fighting the type checker
    spend: float
    impressions: float
    clicks: float
    landing_page_views: float
    purchases: float
    purchase_value: float
    new_customers: float


def daily_cell(spec: CampaignSpec, day: date) -> DailyCell:
    if not spec.active_on(day):
        return DailyCell(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    rng = _rng(spec.id, day)
    season = _season(day)
    spend = (
        spec.daily_budget
        * _budget_mult(spec, day)
        * season
        * _weekend(day)
        * rng.uniform(0.86, 1.14)
    )
    fatigue = _fatigue_mult(spec, day)
    # fatigue shows up as a rising CPM and a falling CTR; the offer's conversion rate is
    # landing-page driven, so season (not fatigue) moves it
    cpm = spec.cpm * (1.55 - 0.55 * fatigue)
    impressions = spend / cpm * 1000 * rng.uniform(0.94, 1.06)
    clicks = impressions * spec.ctr * fatigue * rng.uniform(0.9, 1.1)
    lpv = clicks * spec.lpv_rate * rng.uniform(0.95, 1.03)
    purchases = clicks * spec.cvr * _CVR_BOOST * season * rng.uniform(0.82, 1.18)
    purchase_value = purchases * spec.aov * rng.uniform(0.9, 1.12)
    new_customers = purchases * spec.new_customer_share

    return DailyCell(
        spend=round(spend, 2),
        impressions=float(int(impressions)),
        clicks=float(int(clicks)),
        landing_page_views=float(int(lpv)),
        purchases=float(round(purchases)),
        purchase_value=round(purchase_value, 2),
        new_customers=float(round(new_customers)),
    )
