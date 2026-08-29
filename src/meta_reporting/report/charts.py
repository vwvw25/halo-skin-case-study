"""Matplotlib charts rendered to inline SVG strings for the PDF templates.

Every function returns a ``<svg>`` string sized in inches for print. The palette is restrained:
ink for structure, one teal accent, one amber for the "watch this" series.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

INK = "#1f2328"
MUTED = "#8b949e"
GRID = "#e6e8eb"
ACCENT = "#0f766e"
ACCENT_SOFT = "#5eead4"
WARN = "#b45309"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 8,
        "text.color": INK,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "figure.dpi": 150,
        "svg.fonttype": "none",
    }
)


def _svg(fig: Figure) -> str:
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    return buf.getvalue()


def _clean(ax: Axes) -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def spend_and_cac_trend(weekly: pd.DataFrame, *, weeks: int = 13) -> str:
    data = weekly.tail(weeks)
    fig, ax1 = plt.subplots(figsize=(6.4, 2.4))
    ax1.bar(data["week"], data["spend"], width=5, color=ACCENT_SOFT, label="Spend")
    ax1.set_ylabel("Weekly spend ($)")
    ax1.yaxis.set_major_formatter(lambda v, _: f"${v / 1000:.0f}k")
    _clean(ax1)

    ax2 = ax1.twinx()
    ax2.plot(data["week"], data["cac"], color=WARN, marker="o", markersize=3, label="CAC")
    ax2.set_ylabel("CAC ($)")
    ax2.grid(False)
    for spine in ("top",):
        ax2.spines[spine].set_visible(False)

    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 1.02), ncol=2, frameon=False)
    fig.autofmt_xdate(rotation=0, ha="center")
    return _svg(fig)


def acquisition_funnel(row: pd.Series) -> str:
    stages = ["Impressions", "Clicks", "Purchases (Meta)", "New customers"]
    values = [row["impressions"], row["clicks"], row["meta_purchases"], row["new_customers"]]
    fig, ax = plt.subplots(figsize=(6.4, 2.0))
    bars = ax.barh(stages[::-1], values[::-1], color=[ACCENT, ACCENT, ACCENT_SOFT, WARN][::-1])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in values[::-1]], padding=4, color=INK)
    ax.set_xscale("log")
    ax.set_xticks([])
    ax.minorticks_off()
    ax.tick_params(bottom=False)
    ax.grid(False)
    _clean(ax)
    ax.spines["bottom"].set_visible(False)
    return _svg(fig)


def cohort_maturation(cohorts: pd.DataFrame) -> str:
    """Realized (solid) vs projected (dashed) 12-month CM-LTV by acquisition month."""
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    data = cohorts.sort_values("acquisition_month")
    x = data["acquisition_month"]
    ax.plot(
        x,
        data["realized_cm_per_customer"],
        color=ACCENT,
        marker="o",
        markersize=3,
        label="Realized to date",
    )
    ax.plot(
        x,
        data["projected_cm_per_customer"],
        color=WARN,
        linestyle="--",
        marker="o",
        markersize=3,
        label="Projected 12-mo",
    )
    ax.set_ylabel("CM-LTV per customer ($)")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    ax.legend(frameon=False, loc="lower left")
    _clean(ax)
    fig.autofmt_xdate(rotation=30, ha="right")
    return _svg(fig)


def bar_by_segment(
    frame: pd.DataFrame, *, label_col: str, value_col: str, title: str, as_pct: bool = False
) -> str:
    data = frame.sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=(6.4, 0.4 * len(data) + 0.8))
    bars = ax.barh(data[label_col], data[value_col], color=ACCENT)
    fmt = (lambda v: f"{v:.0%}") if as_pct else (lambda v: f"{v:.1f}")
    ax.bar_label(bars, labels=[fmt(v) for v in data[value_col]], padding=4, color=INK)
    ax.set_title(title, loc="left", pad=8)
    ax.set_xticks([])
    _clean(ax)
    ax.spines["bottom"].set_visible(False)
    return _svg(fig)


def maturation_curve_plot(curve_series: pd.Series) -> str:
    fig, ax = plt.subplots(figsize=(6.4, 2.2))
    ax.fill_between(curve_series.index, curve_series.values, color=ACCENT_SOFT, alpha=0.5)
    ax.plot(curve_series.index, curve_series.values, color=ACCENT, marker="o", markersize=3)
    ax.set_xlabel("Months since first order")
    ax.set_ylabel("Cumulative CM / customer ($)")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}")
    _clean(ax)
    return _svg(fig)
