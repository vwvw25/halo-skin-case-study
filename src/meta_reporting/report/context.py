"""Assemble a report context: run the transforms for a given date + cadence, shape the results
into KPIs, charts, tables and plain-English callouts that the templates just lay out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from meta_reporting import domain, ingest
from meta_reporting.report import charts
from meta_reporting.sources.meta import MetaSource
from meta_reporting.sources.shopify import ShopifySource
from meta_reporting.transform import acquisition, cohorts, spend, target_cohort
from meta_reporting.transform.ltv_cac import ltv_cac_by_segment

_CAMPAIGN_HISTORY_START = date(2025, 6, 1)
_STRATEGY_LABEL = {
    "prospecting_broad": "Prospecting — Broad",
    "prospecting_interest": "Prospecting — Interest",
    "lookalike": "Lookalike",
    "advantage_plus": "Advantage+",
    "retargeting": "Retargeting",
    "awareness": "Awareness",
}


@dataclass(frozen=True, slots=True)
class Kpi:
    label: str
    value: str
    delta_pct: float | None = None
    higher_is_better: bool = True

    @property
    def direction(self) -> str:
        if self.delta_pct is None or abs(self.delta_pct) < 0.005:
            return "flat"
        return "up" if self.delta_pct > 0 else "down"

    @property
    def is_good(self) -> str:
        if self.direction == "flat":
            return "neutral"
        rising = self.direction == "up"
        return "good" if rising == self.higher_is_better else "bad"

    @property
    def delta_label(self) -> str:
        if self.delta_pct is None:
            return "—"
        return f"{self.delta_pct:+.0%}"


@dataclass(frozen=True, slots=True)
class Table:
    title: str
    columns: list[str]
    rows: list[list[str]]


@dataclass(frozen=True, slots=True)
class ReportContext:
    brand: str
    cadence: str
    period_label: str
    comparison_label: str
    generated_on: date
    kpis: list[Kpi]
    charts: dict[str, str]
    tables: list[Table] = field(default_factory=list)
    narrative: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# --- public -------------------------------------------------------------------------------


def build_context(
    meta: MetaSource, shopify: ShopifySource, *, as_of: date, cadence: str
) -> ReportContext:
    if cadence not in ("weekly", "monthly"):
        raise ValueError(cadence)
    md = ingest.meta_daily(meta, _CAMPAIGN_HISTORY_START, as_of)
    customers = ingest.customers(shopify)
    orders = ingest.orders(shopify)
    as_of_ts = pd.Timestamp(as_of)
    if cadence == "weekly":
        return _weekly(md, orders, customers, as_of_ts)
    return _monthly(md, orders, customers, as_of_ts)


# --- weekly -------------------------------------------------------------------------------


def _weekly(
    md: pd.DataFrame, orders: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp
) -> ReportContext:
    topline = acquisition.weekly_topline(md, orders, customers, as_of=as_of)
    complete = topline[topline["week"] + pd.Timedelta(days=7) <= as_of]
    wow = acquisition.week_over_week(complete)
    latest = complete.iloc[-1]
    prior = complete.iloc[-2]

    def d(metric: str) -> float | None:
        row = wow.set_index("metric").loc[metric]
        return None if pd.isna(row["pct_change"]) else float(row["pct_change"])

    kpis = [
        Kpi("Spend", f"${latest['spend']:,.0f}", d("spend"), higher_is_better=False),
        Kpi("New customers", f"{latest['new_customers']:,.0f}", d("new_customers")),
        Kpi("CAC", f"${latest['cac']:,.2f}", d("cac"), higher_is_better=False),
        Kpi("First-order CM", f"${latest['first_order_cm']:,.2f}", d("first_order_cm")),
        Kpi(
            "30-day repeat rate",
            "maturing"
            if pd.isna(latest["repeat_rate_30d"])
            else f"{latest['repeat_rate_30d']:.0%}",
            None,
        ),
    ]

    classified = target_cohort.classify_customers(orders, customers, as_of=as_of)
    capture = target_cohort.capture_rate(classified, by="strategy")
    capture["label"] = capture["acquisition_strategy"].map(_STRATEGY_LABEL)

    cac_week = spend.spend_and_cac(md, customers, by="strategy", freq="W-SUN")
    this_week = cac_week[cac_week["period"] == latest["week"]].set_index("strategy")
    last_week = cac_week[cac_week["period"] == prior["week"]].set_index("strategy")
    cac_rows = [
        [
            _STRATEGY_LABEL.get(s, s),
            f"${this_week.loc[s, 'spend']:,.0f}",
            f"{this_week.loc[s, 'new_customers']:,.0f}",
            _money(this_week.loc[s, "cac"]),
            _delta_str(this_week.loc[s, "cac"], last_week["cac"].get(s)),
        ]
        for s in this_week.index
        if s in _STRATEGY_LABEL
    ]

    chart_dict = {
        "spend_cac_trend": charts.spend_and_cac_trend(complete),
        "funnel": charts.acquisition_funnel(latest),
        "predicted_capture": charts.bar_by_segment(
            capture.dropna(subset=["predicted_capture_rate"]),
            label_col="label",
            value_col="predicted_capture_rate",
            title="Predicted target-cohort capture — cohorts still maturing",
            as_pct=True,
        ),
    }

    narrative = _weekly_narrative(wow, latest)
    recs = _weekly_recommendations(this_week, capture)

    return ReportContext(
        brand="Halo Skin",
        cadence="weekly",
        period_label=f"Week of {latest['week']:%-d %b %Y}",
        comparison_label=f"vs week of {prior['week']:%-d %b %Y}",
        generated_on=as_of.date(),
        kpis=kpis,
        charts=chart_dict,
        tables=[
            Table(
                "CAC by strategy — this week",
                ["Strategy", "Spend", "New customers", "CAC", "Δ CAC vs last week"],
                cac_rows,
            )
        ],
        narrative=narrative,
        recommendations=recs,
    )


_METRIC_LABEL = {
    "spend": "Spend",
    "new_customers": "New customers",
    "cac": "CAC",
    "first_order_cm": "First-order CM",
    "repeat_rate_30d": "30-day repeat rate",
}


def _weekly_narrative(wow: pd.DataFrame, latest: pd.Series) -> list[str]:
    out: list[str] = []
    moves = wow.dropna(subset=["pct_change"]).copy()
    moves["abs"] = moves["pct_change"].abs()
    for _, row in moves.sort_values("abs", ascending=False).head(3).iterrows():
        direction = "up" if row["delta"] > 0 else "down"
        label = _METRIC_LABEL.get(row["metric"], row["metric"].replace("_", " ").capitalize())
        out.append(
            f"{label} {direction} {abs(row['pct_change']):.0%} week over week "
            f"({row['prior']:,.2f} → {row['current']:,.2f})."
        )
    if pd.isna(latest["repeat_rate_30d"]):
        out.append(
            "30-day repeat rate for the latest cohorts is still maturing; the predicted "
            "target-cohort capture chart is the leading indicator to watch."
        )
    return out


def _weekly_recommendations(this_week: pd.DataFrame, capture: pd.DataFrame) -> list[str]:
    recs: list[str] = []
    ranked = (
        this_week.drop(index=["retargeting", "awareness"], errors="ignore")
        .dropna(subset=["cac"])
        .sort_values("cac")
    )
    if len(ranked) >= 2:
        best, worst = ranked.index[0], ranked.index[-1]
        recs.append(
            f"Among acquisition strategies, {_STRATEGY_LABEL.get(best, best)} has the lowest CAC "
            f"this week (${ranked.loc[best, 'cac']:,.2f}) and "
            f"{_STRATEGY_LABEL.get(worst, worst)} the highest "
            f"(${ranked.loc[worst, 'cac']:,.2f}). Shift budget toward the former for next week."
        )
    cap = capture.dropna(subset=["predicted_capture_rate"]).sort_values(
        "predicted_capture_rate", ascending=False
    )
    if len(cap):
        top = cap.iloc[0]
        recs.append(
            f"{top['label']} is predicted to bring the highest share of high-LTV customers "
            f"({top['predicted_capture_rate']:.0%}). Protect its budget even if its day-1 ROAS "
            f"looks weaker than retargeting."
        )
    return recs


# --- monthly -----------------------------------------------------------------------------


def _monthly(
    md: pd.DataFrame, orders: pd.DataFrame, customers: pd.DataFrame, as_of: pd.Timestamp
) -> ReportContext:
    month_start = (as_of.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
    prev_start = (month_start - pd.Timedelta(days=1)).replace(day=1)

    monthly_spend = spend.spend_and_cac(md, customers, freq="M").set_index("period")
    this_m = monthly_spend.loc[month_start]
    prev_m = monthly_spend.loc[prev_start]

    curve = cohorts.maturation_curve(orders, customers, as_of=as_of)
    cohort_all = cohorts.cohort_ltv(orders, customers, curve, as_of=as_of)
    cohort_by_campaign = cohorts.cohort_ltv(orders, customers, curve, as_of=as_of, by="campaign")
    cac_by_campaign = spend.spend_and_cac(md, customers, by="campaign")
    lc = ltv_cac_by_segment(cohort_by_campaign, cac_by_campaign, curve, by="campaign")

    cohort_by_strategy = cohorts.cohort_ltv(orders, customers, curve, as_of=as_of, by="strategy")
    cac_by_strategy = spend.spend_and_cac(md, customers, by="strategy")
    lc_strategy = ltv_cac_by_segment(cohort_by_strategy, cac_by_strategy, curve, by="strategy")
    lc_strategy["label"] = lc_strategy["strategy"].map(_STRATEGY_LABEL)

    classified = target_cohort.classify_customers(orders, customers, as_of=as_of)
    capture = target_cohort.capture_rate(classified, by="strategy")
    capture["label"] = capture["acquisition_strategy"].map(_STRATEGY_LABEL)

    blended_ltv = _weighted(cohort_all["projected_cm_per_customer"], cohort_all["cohort_size"])
    blended_cac = this_m["cac"]

    kpis = [
        Kpi(
            "Spend",
            f"${this_m['spend']:,.0f}",
            _pct(this_m["spend"], prev_m["spend"]),
            higher_is_better=False,
        ),
        Kpi(
            "New customers",
            f"{this_m['new_customers']:,.0f}",
            _pct(this_m["new_customers"], prev_m["new_customers"]),
        ),
        Kpi(
            "Blended CAC",
            f"${blended_cac:,.2f}",
            _pct(this_m["cac"], prev_m["cac"]),
            higher_is_better=False,
        ),
        Kpi("12-mo CM-LTV (proj.)", f"${blended_ltv:,.0f}", None),
        Kpi("Blended LTV:CAC", f"{blended_ltv / blended_cac:.1f}", None),
    ]

    names = _campaign_names(md)
    strategies = _campaign_strategies(md)
    lc["name"] = lc["campaign"].map(names)
    lc["strategy"] = lc["campaign"].map(strategies)
    lc_rows = [
        [
            r["name"],
            _money(r["cac"]),
            f"${r['cm_ltv_12']:,.0f}",
            f"{r['ltv_cac']:.1f}",
            _payback_label(r["payback_months"]),
            f"{r['realized_share']:.0%}",
        ]
        for _, r in lc.iterrows()
    ]

    cap_rows = [
        [
            r["label"],
            f"{r['realized_capture_rate']:.0%}" if pd.notna(r["realized_capture_rate"]) else "—",
            f"{r['predicted_capture_rate']:.0%}" if pd.notna(r["predicted_capture_rate"]) else "—",
            f"{r['matured']:,.0f} / {r['customers']:,.0f}",
        ]
        for _, r in capture.dropna(subset=["label"]).iterrows()
    ]

    chart_dict = {
        "cohort_maturation": charts.cohort_maturation(cohort_all),
        "maturation_curve": charts.maturation_curve_plot(curve.cum_cm),
        "ltv_cac_by_strategy": charts.bar_by_segment(
            lc_strategy.dropna(subset=["label"]),
            label_col="label",
            value_col="ltv_cac",
            title="LTV:CAC by strategy",
        ),
        "capture_by_strategy": charts.bar_by_segment(
            capture.dropna(subset=["realized_capture_rate", "label"]),
            label_col="label",
            value_col="realized_capture_rate",
            title="Realized target-cohort capture by strategy",
            as_pct=True,
        ),
    }

    narrative = _monthly_narrative(lc, lc_strategy, capture)
    recs = _monthly_recommendations(lc, lc_strategy, capture)

    return ReportContext(
        brand="Halo Skin",
        cadence="monthly",
        period_label=f"{month_start:%B %Y}",
        comparison_label=f"vs {prev_start:%B %Y}",
        generated_on=as_of.date(),
        kpis=kpis,
        charts=chart_dict,
        tables=[
            Table(
                "LTV:CAC by campaign",
                ["Campaign", "CAC", "12-mo CM-LTV", "LTV:CAC", "Payback", "Cohorts matured"],
                lc_rows,
            ),
            Table(
                "Target-cohort capture by strategy",
                ["Strategy", "Realized", "Predicted", "Matured / total"],
                cap_rows,
            ),
        ],
        narrative=narrative,
        recommendations=recs,
    )


def _monthly_narrative(
    lc: pd.DataFrame, lc_strategy: pd.DataFrame, capture: pd.DataFrame
) -> list[str]:
    out: list[str] = []
    acq = lc_strategy[~lc_strategy["strategy"].isin(["retargeting", "awareness"])]
    if len(acq):
        best = acq.loc[acq["ltv_cac"].idxmax()]
        worst = acq.loc[acq["ltv_cac"].idxmin()]
        out.append(
            f"Among acquisition strategies, {best['label']} leads on LTV:CAC "
            f"({best['ltv_cac']:.1f}) and {worst['label']} trails ({worst['ltv_cac']:.1f})."
        )
    rt = lc_strategy[lc_strategy["strategy"] == "retargeting"]
    if len(rt):
        out.append(
            f"Retargeting shows an LTV:CAC of {rt.iloc[0]['ltv_cac']:.1f} on a very low CAC, but "
            f"its target-cohort capture is among the lowest — it largely reacquires customers who "
            f"would have returned anyway, so treat that ratio with care."
        )
    cap = capture.dropna(subset=["realized_capture_rate"]).sort_values(
        "realized_capture_rate", ascending=False
    )
    if len(cap) >= 2:
        out.append(
            f"{cap.iloc[0]['label']} captures the target cohort at "
            f"{cap.iloc[0]['realized_capture_rate']:.0%} vs {cap.iloc[-1]['label']} at "
            f"{cap.iloc[-1]['realized_capture_rate']:.0%}."
        )
    return out


def _monthly_recommendations(
    lc: pd.DataFrame, lc_strategy: pd.DataFrame, capture: pd.DataFrame
) -> list[str]:
    recs: list[str] = []
    acquisition = lc[~lc["strategy"].isin(["retargeting", "awareness"])]
    healthy = acquisition[acquisition["ltv_cac"] >= domain.HEALTHY_LTV_CAC].sort_values(
        "ltv_cac", ascending=False
    )
    weak = acquisition[acquisition["ltv_cac"] < 1.5].sort_values("ltv_cac")
    if len(healthy):
        recs.append(
            "Scale budget into "
            + ", ".join(healthy["name"].head(2))
            + f" — both clear the {domain.HEALTHY_LTV_CAC:.0f}:1 health line on a 12-month view."
        )
    if len(weak):
        recs.append(
            "Cut or rework "
            + ", ".join(weak["name"].head(2))
            + " — 12-month CM-LTV does not cover CAC."
        )
    cap = capture.dropna(subset=["realized_capture_rate"]).sort_values(
        "realized_capture_rate", ascending=False
    )
    if len(cap):
        recs.append(
            f"Rebuild the lookalike seed list from customers acquired via {cap.iloc[0]['label']} "
            f"in the last two matured cohorts — that is where the high-LTV cohort concentrates."
        )
    return recs


# --- helpers -----------------------------------------------------------------------------


def _pct(now: float, before: float) -> float | None:
    if before in (0, None) or pd.isna(before):
        return None
    return float((now - before) / before)


def _delta_str(now: float, before: float | None) -> str:
    if before is None or pd.isna(before) or before == 0 or pd.isna(now):
        return "—"
    return f"{(now - before) / before:+.0%}"


def _money(value: float) -> str:
    return "—" if pd.isna(value) else f"${value:,.2f}"


def _payback_label(months: float) -> str:
    if pd.isna(months):
        return "—"
    return "<1 mo" if months < 1 else f"{months:.0f} mo"


def _weighted(values: pd.Series, weights: pd.Series) -> float:
    total = weights.sum()
    return float((values * weights).sum() / total) if total else float("nan")


def _campaign_names(md: pd.DataFrame) -> dict[str, str]:
    return (
        md[["campaign_id", "campaign_name"]]
        .drop_duplicates()
        .set_index("campaign_id")["campaign_name"]
        .to_dict()
    )


def _campaign_strategies(md: pd.DataFrame) -> dict[str, str]:
    return (
        md[["campaign_id", "strategy"]]
        .drop_duplicates()
        .set_index("campaign_id")["strategy"]
        .to_dict()
    )
