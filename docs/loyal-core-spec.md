# Spec — Loyal Core (signal vs outcome)

**Status:** designed, not built. Deferred from the main build. This document is a self-contained
handoff — a fresh session should be able to implement it without the conversation it came from.

## Why

The dashboard currently has one target cohort, **Regimen Builders**, defined by *early*
behaviour: ≥3 orders in the first 90 days, AOV ≥ $62, ≥1 premium SKU
(`meta_reporting/domain.py`). That's a **leading indicator** — something you can measure at
acquisition time and optimise ad spend against.

It is not the same thing as *"a customer who actually turned out to be valuable"*. Some Regimen
Builders front-load orders and churn; some quiet first-90-days customers become 3-year
loyalists. Optimising hard against the early signal without checking it against the real outcome
is textbook **Goodhart's law** — the proxy drifts from the goal and you don't notice.

Loyal Core adds the **retrospective** cohort — defined by the outcome, "still spending steadily
a year or two later" — and puts the two side by side so the drift between them is visible and
measurable.

## The two cohorts, and how they relate

| | Regimen Builders (exists) | Loyal Core (to build) |
|---|---|---|
| Definition | first-90-day behaviour | sustained retention, judged retrospectively |
| Known when | day 90 | ~14+ months after acquisition |
| Used for | the metric you optimise acquisition against, week to week | the definition of a valuable customer; the lookalike seed list |
| Value curve shape | ramp then gently decelerating (churn erodes the cohort) | near-linear — members are *defined* as not churning |

**The relationship is the analysis:**

- **precision** — of Regimen Builders, what share became Loyal Core (are we chasing the right people?)
- **recall** — of Loyal Core, what share did the early signal catch (are we missing people?)
- **per-campaign core-capture** — of the customers a campaign acquired, what share became Loyal
  Core. *This* is the number that should drive budget, not day-1 ROAS or even LTV:CAC.

The lookalike `LAL 1% — Regimen Builders` is reframed: it's seeded from a retrospective list of
**Loyal Core** members; Regimen Builders is the fast-feedback proxy you watch in between.

## Prerequisite: extend the mock timeline to ~3 years

You cannot show "still spending at month 24" — or distinguish near-linear from
"linear then plateaus at month 15" — inside the current ~14 months of data.

- `scripts/_scenario.py`: `START = date(2023, 8, 1)` (keep `END = date(2026, 7, 31)`). ~35 months.
- `src/meta_reporting/emit.py` and `src/meta_reporting/report/context.py`: `_HISTORY_START` /
  `_CAMPAIGN_HISTORY_START` currently hard-code `date(2025, 6, 1)` — point them at
  `_scenario.START` or the same new date.
- Regenerate **all** fixtures: `uv run python scripts/generate_meta_fixtures.py` then
  `uv run python scripts/generate_shopify_fixtures.py`.
- Re-tune if the headline numbers drift: `_CVR_BOOST` (`_scenario.py`), `ATTRIBUTION_RATE` and
  `_TARGET_TUNE` (`_customers.py`). Targets to hold: blended CAC ~$28-45, target-cohort share
  ~20%, LTV:CAC story unchanged (LAL Regimen Builders top acquisition campaign, retargeting
  tops the raw list).
- **Fixture size is a real constraint.** 3 years ≈ 40-55k customers, 150k+ orders → the gzipped
  orders fixture could hit 4-6 MB. If that's too big for the repo, dial down campaign
  `daily_budget`s or `ATTRIBUTION_RATE` to land ~25-30k customers. Decide this early.

## Data model — add a loyalist segment

In `scripts/_customers.py::_history` there are currently two archetypes driven by the
`high_value` flag (routine assembly then replenish-until-churn, churn ~5.5%/mo for Builders,
~34%/mo for everyone else). Add a third:

- **Loyalists** — a sub-slice, e.g. `loyalist = high_value and rng.random() < 0.35` (≈8-12% of
  all customers). Near-zero churn (`monthly_churn ≈ 0.01`), steady replenishment every ~35-45
  days, runs to `END`. Their cumulative-value line is near-linear.
- Keep the rest as they are. Non-loyalist Builders still churn at ~5-8%/mo — they're the
  false positives that make precision < 1.

The `is_target` (Regimen Builders) definition **does not change** — some loyalists won't hit
3-in-90 (recall < 1), some non-loyalists will (precision < 1). That gap is the point.

## Transform layer

New module `src/meta_reporting/transform/loyal_core.py` (or extend `target_cohort.py`):

1. **`classify_loyal_core(orders, customers, *, as_of)`** → one row per customer:
   - `observable_months` = months from first order to `as_of`
   - `eligible` = `observable_months >= LOYAL_CORE_MIN_TENURE_MONTHS` (only these get a verdict)
   - `is_loyal_core` (bool, NaN when not eligible): active in the last `LOYAL_CORE_ACTIVE_WINDOW_DAYS`
     **and** `total_orders >= LOYAL_CORE_MIN_ORDERS` **and** order span `>= LOYAL_CORE_MIN_SPAN_MONTHS`
     **and** ordered in `>= LOYAL_CORE_MIN_ACTIVE_MONTHS` of the last 12 (consistency).
   - carry the acquisition campaign / strategy columns through for the per-campaign rollup.

2. **`signal_vs_outcome(regimen_builders_classified, loyal_core_classified)`** → precision,
   recall, F1, plus a small confusion-matrix-style breakdown (builder∩core, builder¬core,
   ¬builder∩core, ¬builder¬core) over the customers eligible for *both* verdicts.

3. **`core_capture_by_segment(loyal_core_classified, *, by)`** → per campaign / strategy:
   `customers`, `eligible`, `core_capture_rate`. Mirror `target_cohort.capture_rate`.

4. **`value_curve_by_loyal_core(orders, customers, loyal_core_classified, regimen_builders_classified, *, as_of, horizon)`**
   — like the existing `cohorts.value_curve_by_target` but a **4-way** split:
   `loyal_core` / `builder_not_core` (false positives) / `other` / `blended`. Longer horizon than
   12 months here — go to ~24-30 so the linearity is visible. Cumulative value per customer by
   month of life; only customers observed at least that long contribute to each month.

Add constants to `src/meta_reporting/domain.py`:

```python
LOYAL_CORE_NAME: Final = "Loyal Core"
LOYAL_CORE_MIN_TENURE_MONTHS: Final = 14   # need this much observation to judge
LOYAL_CORE_ACTIVE_WINDOW_DAYS: Final = 60  # ordered within the last N days = "still active"
LOYAL_CORE_MIN_ORDERS: Final = 6
LOYAL_CORE_MIN_SPAN_MONTHS: Final = 12     # first to last order
LOYAL_CORE_MIN_ACTIVE_MONTHS: Final = 6    # of the last 12
LOYAL_CORE_CURVE_HORIZON_MONTHS: Final = 30
```

Tune so Loyal Core lands ~8-14% of *eligible* customers.

## Emit

`src/meta_reporting/emit.py::build_dashboard_data` — add:

```jsonc
"loyal_core": {
  "name": "Loyal Core",
  "definition": { /* the LOYAL_CORE_* constants */ },
  "share_of_eligible": 0.11,
  "revenue_share": 0.38,               // of all revenue, from Loyal Core customers
  "signal_vs_outcome": {               // Regimen Builders (signal) vs Loyal Core (outcome)
    "precision": 0.55, "recall": 0.62,
    "builder_and_core": 1200, "builder_not_core": 980,
    "core_not_builder": 730, "neither": 14000
  },
  "core_capture_by_strategy": [ {"strategy": "lookalike", "core_capture_rate": 0.19, ...}, ... ],
  "value_curve": [ {"month_index": 0, "segment": "loyal_core", "cum_revenue": ..., "cum_cm": ..., "n": ...}, ... ]
}
```

Reuse the `_records` / `_round` helpers. Keep everything JSON-clean (no NaN, no Timestamp — the
existing tests guard this).

## Dashboard (`dashboard/`)

1. **`lib/data.ts`** — add the `loyal_core` types to the `Dashboard` interface.
2. **New card "The Loyal Core"** in `components/DashboardBody.tsx`:
   - the retrospective definition (plain English)
   - its size (`share_of_eligible`) and its `revenue_share` — "11% of customers, 38% of revenue"
   - one line: seeded the lookalike from here.
3. **New chart `components/LoyalCoreCurve.tsx`** — the 4-line cumulative-value chart:
   `Loyal Core` (near-linear, climbing to month 30), `Regimen Builders who didn't convert`
   (ramp then plateau — the false positives), `Everyone else` (flat by month 4), `Blended
   average`. Same palette conventions as `ValueSplitChart.tsx`. Recharts `LineChart`,
   `isAnimationActive={false}`.
4. **"Signal vs outcome" panel** — small: precision / recall of the early signal as two stat
   tiles, plus a bar of `core_capture_rate` by strategy (mirror `SegmentScatter` colours:
   teal acquisition, amber retargeting/awareness). Headline: the LAL seed campaign has the
   highest core-capture.
5. **Reframe the existing "Regimen Builders" card** — it's now explicitly "the leading
   indicator you act on"; add a sentence tying it to Loyal Core as "the outcome it predicts,
   caught early ~55% of the time."
6. `ValueSplitChart` can stay (12-month view of Builders vs rest) or be retired in favour of
   the 4-line chart — reviewer's call.

## Report (PDF) — optional

`src/meta_reporting/report/context.py` monthly path: add a "Loyal Core" section — the
retrospective definition, size, revenue share, the signal→outcome precision/recall, and the
per-campaign core-capture table. Chart via `report/charts.py` (matplotlib → SVG, existing
pattern). The weekly report stays as-is (Loyal Core is strategic, not operational).

## Tests

- `tests/test_transform_loyal_core.py`:
  - Loyal Core is a smaller slice than Regimen Builders (~8-14% of eligible)
  - its value curve is near-linear: monthly increments roughly constant, *not* decelerating
    like the Builders curve (`increment.std() / increment.mean()` below some bound)
  - precision and recall are both strictly between 0 and 1
  - `core_capture_by_strategy`: lookalike > prospecting_broad; retargeting low
  - customers below `LOYAL_CORE_MIN_TENURE_MONTHS` observation get no verdict (NaN)
- `tests/test_emit.py`: the `loyal_core` block has the expected keys, `revenue_share` in a
  sane band, `value_curve` has 4 segments, fully JSON-serialisable.
- Existing story tests (`test_transform_cohorts.py`, `test_report.py`) will shift because the
  timeline changed — expect to re-baseline a handful of numeric bands, not rewrite them.

## Definition of done

- `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` — green
  (pandas-heavy modules are in the mypy override list in `pyproject.toml`; add
  `meta_reporting.transform.loyal_core` there).
- `cd dashboard && npm run lint && npm run typecheck && npm run build` — green.
- `uv run python -m meta_reporting.pipeline monthly` produces the PDF + `data/dashboard.json`;
  `cp data/dashboard.json dashboard/data/dashboard.json`.
- Dashboard shows the Loyal Core card + the 4-line curve + the signal-vs-outcome panel, and
  the numbers reconcile with the PDF.
- README milestone table + `docs/` updated; commit with the usual co-author trailer.

## Files, at a glance

| Area | Files |
|---|---|
| Data model | `scripts/_scenario.py`, `scripts/_customers.py`, regenerate `fixtures/**` |
| Constants | `src/meta_reporting/domain.py` |
| Transform | `src/meta_reporting/transform/loyal_core.py` (new), maybe `target_cohort.py` |
| Emit | `src/meta_reporting/emit.py` |
| Pipeline history start | `src/meta_reporting/emit.py`, `src/meta_reporting/report/context.py` |
| Report | `src/meta_reporting/report/context.py`, `report/charts.py`, `report/templates/monthly.html` |
| Dashboard | `dashboard/lib/data.ts`, `dashboard/components/DashboardBody.tsx`, `components/LoyalCoreCurve.tsx` (new), a signal-vs-outcome component |
| Tests | `tests/test_transform_loyal_core.py` (new), `tests/test_emit.py`, re-baseline `test_transform_cohorts.py` / `test_report.py` |
| mypy | add `meta_reporting.transform.loyal_core` to the override in `pyproject.toml` |
| Docs | `README.md` milestone table, this file's status line |
