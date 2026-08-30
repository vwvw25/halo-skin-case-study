"""Customer + order simulation for the mock Shopify fixtures.

Reads the shared campaign roster and per-day new-customer counts from ``_scenario`` and turns
them into customers with realistic order histories. Repeat-purchase behaviour is correlated
with the acquiring campaign (moderately — the spread is ~2-2.5x and partly buried in noise, so
the analysis has to work to surface it).

Recent acquisition cohorts naturally show fewer orders because their customers run out of
calendar before END — that truncation is the whole point of the cohort-maturation analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from random import Random

from _scenario import (
    CAMPAIGNS,
    END,
    SEED,
    age_weights,
    all_days,
    daily_cell,
    gender_weights,
    region_weights,
)

from meta_reporting.catalog import CATALOG, Product
from meta_reporting.sources.meta.strategy import classify

Sku = Product  # local alias — this module was written before the catalogue moved into the package

# fraction of Meta-acquired customers that land in Shopify with attribution tags intact
# (UTM capture + post-purchase survey). The ~18% gap inflates measured CAC vs true CAC — the
# report appendix notes this.
ATTRIBUTION_RATE = 0.82
# nudges the share of customers meeting the target-cohort definition toward ~20%
_TARGET_TUNE = 1.45

_FIRST_ORDER_ID = 5_500_000_000
_FIRST_CUSTOMER_ID = 7_100_000_000


# --- product catalog --------------------------------------------------------------------

_CORE = [s for s in CATALOG if s.line == "core"]
_PREMIUM = [s for s in CATALOG if s.line == "premium"]

_FIRST_NAMES = [
    "Ava",
    "Mia",
    "Zoe",
    "Leah",
    "Noah",
    "Kai",
    "Ella",
    "Ivy",
    "Ruby",
    "Owen",
    "Cole",
    "Nia",
    "Jade",
    "Finn",
    "Remy",
    "Skye",
]
_LAST_NAMES = [
    "Ng",
    "Patel",
    "Reed",
    "Cruz",
    "Wolfe",
    "Shah",
    "Frost",
    "Lin",
    "Beck",
    "Hale",
    "Voss",
    "Kerr",
    "Pace",
    "Dunn",
]


# --- records ----------------------------------------------------------------------------


@dataclass(slots=True)
class GenOrder:
    id: int
    customer_id: int
    processed_at: datetime
    line_items: list[tuple[Sku, int]]
    discount: float
    tax: float
    refund: float

    @property
    def subtotal(self) -> float:
        return round(sum(s.price * q for s, q in self.line_items), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal - self.discount + self.tax, 2)


@dataclass(slots=True)
class GenCustomer:
    id: int
    first_name: str
    last_name: str
    created_at: datetime
    region: str
    age: str
    gender: str
    campaign_id: str
    strategy: str
    orders: list[GenOrder]

    @property
    def email(self) -> str:
        return f"{self.first_name}.{self.last_name}{self.id % 1000}@example.com".lower()

    @property
    def total_spent(self) -> float:
        return round(sum(o.total for o in self.orders), 2)


def _rng(*parts: object) -> Random:
    return Random(f"{SEED}:{':'.join(str(p) for p in parts)}")


def _weighted(rng: Random, weights: dict[str, float]) -> str:
    roll = rng.random() * sum(weights.values())
    cum = 0.0
    for key, weight in weights.items():
        cum += weight
        if roll <= cum:
            return key
    return next(iter(weights))


def _order_totals(rng: Random, items: list[tuple[Sku, int]]) -> tuple[float, float, float]:
    subtotal = sum(s.price * q for s, q in items)
    discount = round(subtotal * 0.1, 2) if rng.random() < 0.22 else 0.0
    tax = round((subtotal - discount) * 0.08, 2)
    refund = round(subtotal * rng.uniform(0.3, 1.0), 2) if rng.random() < 0.03 else 0.0
    return discount, tax, refund


def _basket(rng: Random, premium_lean: float) -> list[tuple[Sku, int]]:
    size = rng.choices([1, 2, 3], weights=[5, 4, 2])[0]
    items: list[tuple[Sku, int]] = []
    for _ in range(size):
        pool = _PREMIUM if rng.random() < premium_lean else _CORE
        sku = rng.choice(pool)
        qty = 1 if rng.random() < 0.85 else 2
        items.append((sku, qty))
    return items


def _emit_order(
    rng: Random, customer_id: int, seq: int, when: date, items: list[tuple[Sku, int]]
) -> GenOrder:
    discount, tax, refund = _order_totals(rng, items)
    return GenOrder(
        id=_FIRST_ORDER_ID + customer_id * 40 + seq,
        customer_id=customer_id,
        processed_at=datetime.combine(when, datetime.min.time()).replace(
            hour=rng.randint(7, 22), minute=rng.randint(0, 59)
        ),
        line_items=items,
        discount=discount,
        tax=tax,
        refund=refund,
    )


def _history(
    rng: Random, customer_id: int, acq: date, high_value: bool
) -> tuple[list[GenOrder], bool]:
    """A customer's order history: a front-loaded routine-assembly phase, then replenishment
    that runs until a per-cycle churn draw ends it or the data does.

    Regimen Builders assemble a full routine fast, then keep replenishing with a low monthly
    churn hazard — so their cumulative value keeps climbing. Everyone else buys once or twice
    and mostly drops within a few months.
    """
    if high_value:
        premium_lean = 0.6
        assembly = rng.choices([2, 3, 4], weights=[3, 4, 2])[0]
        assembly_gaps = [round(rng.gauss(26, 9)) for _ in range(assembly)]
        replen_mean, replen_sd, monthly_churn = 44.0, 13.0, 0.055
    else:
        premium_lean = 0.16
        assembly = rng.choices([1, 1, 2], weights=[5, 3, 2])[0]
        assembly_gaps = [round(rng.gauss(64, 26)) for _ in range(assembly)]
        replen_mean, replen_sd, monthly_churn = 82.0, 34.0, 0.34

    orders: list[GenOrder] = []
    when = acq
    bought_premium = False
    seq = 0

    for gap in assembly_gaps:
        if when > END:
            break
        items = _basket(rng, premium_lean if seq > 0 else premium_lean * 0.8)
        if high_value and seq == 0 and not any(s.line == "premium" for s, _ in items):
            items[0] = (rng.choice(_PREMIUM), 1)
        bought_premium = bought_premium or any(s.line == "premium" for s, _ in items)
        orders.append(_emit_order(rng, customer_id, seq, when, items))
        seq += 1
        when = when + timedelta(days=max(6, gap))

    while when <= END:
        cycle = max(12, round(rng.gauss(replen_mean, replen_sd)))
        churn_prob = 1 - (1 - monthly_churn) ** (cycle / 30)
        if rng.random() < churn_prob:
            break
        items = _basket(rng, premium_lean)
        bought_premium = bought_premium or any(s.line == "premium" for s, _ in items)
        orders.append(_emit_order(rng, customer_id, seq, when, items))
        seq += 1
        when = when + timedelta(days=cycle)

    return orders, bought_premium


def generate_customers() -> list[GenCustomer]:
    customers: list[GenCustomer] = []
    next_id = _FIRST_CUSTOMER_ID

    for spec in CAMPAIGNS:
        strategy = classify(spec.name).value
        age_w = age_weights(spec.age_profile)
        gender_w = gender_weights(spec.gender_profile)
        region_w = region_weights(spec.region_profile)
        for day in all_days():
            if not spec.active_on(day):
                continue
            n = round(daily_cell(spec, day).new_customers * ATTRIBUTION_RATE)
            for _ in range(n):
                cid = next_id
                next_id += 1
                rng = _rng("cust", cid)
                high_value = rng.random() < min(0.7, spec.target_cohort_rate * _TARGET_TUNE)
                orders, _premium = _history(rng, cid, day, high_value)
                if not orders:
                    continue
                customers.append(
                    GenCustomer(
                        id=cid,
                        first_name=rng.choice(_FIRST_NAMES),
                        last_name=rng.choice(_LAST_NAMES),
                        created_at=orders[0].processed_at,
                        region=_weighted(rng, region_w),
                        age=_weighted(rng, age_w),
                        gender=_weighted(rng, gender_w),
                        campaign_id=spec.id,
                        strategy=strategy,
                        orders=orders,
                    )
                )
    return customers
