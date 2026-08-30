# Testing

**101 tests across 14 files** (~1,350 lines), run on every push and pull request.

```bash
uv run pytest          # ~28 seconds locally
```

## The three CI gates

Every commit to `main` and every PR runs all three; all must pass.

| Gate | Command | Catches |
|---|---|---|
| Lint + format | `ruff check .` / `ruff format --check .` | import order, unused names, line length, style drift |
| Types | `mypy` (strict) | signature mismatches, `None` handling, wrong argument types |
| Tests | `pytest` | behaviour — the 101 tests below |

`mypy` runs strict everywhere. The pandas-heavy modules (`ingest`, `transform.*`, `report.*`,
`emit`) keep fully typed function signatures but relax the *internal* dataframe-expression
checks, because `pandas-stubs` under `--strict` is unworkably noisy on chained `.loc`,
comparisons and `groupby`/`apply`. CI also runs `apt-get install libpango-1.0-0
libpangoft2-1.0-0` before the suite, because WeasyPrint (PDF rendering) needs system graphics
libraries.

## The core design decision: no test touches a live API

Everything runs against the seeded mock fixtures (`fixtures/meta/*.json.gz`,
`fixtures/shopify/*.json.gz`), which are deterministic — the same ~20k customers and ~43k orders
every run. That buys three things:

- tests are fast, run offline, and need no credentials
- assertions can be **exact** ("blended CAC is $28–30", "target cohort is 16–24% of customers")
  because the data never changes
- the real API clients are still tested — against hand-written fake HTTP responses, not a network

See [data-sources.md](data-sources.md) for how the real/mock seam is built.

## What each area tests, and why

### Config — `test_config.py` (8)

The `mock`/`live` switching logic, which is the seam that keeps everything else hermetic. Checks
that it defaults to fully-mock, that `META_REPORTING_MODE=live` cascades to each source, that a
per-source override wins, and that a `live` source with no credentials fails **at startup** with
a clear message rather than halfway through a run.

### Mock clients — `test_meta_mock_client.py` (13), `test_shopify_mock_client.py` (9)

These prove the mock does real work rather than returning canned answers. The signature tests
are **reconciliation tests**:

- `test_account_level_reconciles_with_campaign_level` — pull spend at account level and at
  campaign level; the totals match to the cent
- `test_ad_level_reconciles_with_campaign_level` — same, one level deeper
- `test_age_gender_breakdown_reconciles_with_topline` — sum spend across all 18 age×gender cells;
  it equals the campaign total
- `test_region_and_platform_breakdowns_partition_the_same_total` — the region slice and the
  platform slice are two views of the same number, so they must sum equally

If these pass, the fixture generator produced internally consistent data and the mock client's
filtering/aggregation is correct — so a weird number downstream is the transform's fault, not
the data's.

Also here: missing-fixture errors are clear (`test_missing_fixture_dir_raises`), and asking for
a slice that was never extracted raises a helpful message
(`test_daily_breakdown_not_cached`), mirroring how the real API would need a fresh pull.

### Real clients — `test_meta_client.py` (7), `test_shopify_client.py` (7)

Since these can't hit a live API, each test injects a **`FakeSession`** — a stand-in for
`requests.Session` preloaded with fake responses:

```python
session = FakeSession(
    FakeResponse(503, text="try later"),  # first call fails
    FakeResponse(200, {"data": []}),  # retry succeeds
)
rows = _client(session).get_insights(...)
assert len(session.calls) == 2  # it retried once
```

This exercises the parts of real HTTP code that are easy to get wrong: cursor pagination
(follows `paging.next` / the `Link` header to a second page), retry-with-backoff on 429/503,
parsing Meta's error envelope, `act_` prefix normalisation, and request-param construction
(`time_range` as JSON, `breakdowns=age,gender`, auth header present).

### Transforms — `test_transform_cohorts.py` (6), `test_transform_target_cohort.py` (7), `test_transform_acquisition.py` (4)

Where analytics correctness lives. Two kinds:

**Structural / mathematical**

- `test_maturation_curve_is_increasing_and_decelerating` — the repeat-purchase curve rises every
  month and each month adds *less* than the last (the shape of a real retention curve)
- `test_spend_and_cac_weekly_has_more_rows` — same data weekly vs monthly: more rows, identical
  total spend
- `test_cohort_ltv_projection_behaviour` — mature cohorts report as realized (no projection),
  young cohorts project *above* their realized-to-date, and every cohort projects to roughly the
  same 12-month LTV (coefficient of variation < 15%). That last assertion is the whole
  maturation model working: a 1-month-old cohort should still land near the mature cohorts'
  ~$145–155.
- `test_maturity_flag_tracks_acquisition_age` — customers acquired 120+ days ago are "matured",
  those within 90 days are not
- `test_is_target_requires_all_three_criteria` — every target-cohort member has ≥3 orders in
  90 days **and** AOV ≥ $62 **and** a premium purchase
- `test_predicted_prob_is_a_probability_and_rises_with_early_orders` — the early-signal lookup
  returns values in [0, 1] that increase with first-30-day order count
- `test_week_over_week` / `test_repeat_rate_only_for_matured_weeks` — deltas equal
  `current − prior`; the 30-day repeat rate is `NaN` for weeks too recent to have observed 30 days

**"Story" tests** — assert the mock data tells the narrative the project is about

- `test_ltv_cac_ranking_matches_the_story` — the high-AOV lookalike is the best acquisition
  campaign, broad prospecting the worst, gap > 2×; and retargeting tops the *raw* LTV:CAC list
  (the trap the report exists to expose)
- `test_capture_rate_by_strategy_spread` — lookalike captures the target cohort at ~2–3.5× the
  rate of broad prospecting
- `test_realized_target_rate_is_about_a_fifth` — the target cohort is 16–24% of customers,
  guarding the thresholds tuned to ~20%
- `test_payback_is_within_horizon_for_healthy_segments` — lookalike pays back in ≤3 months, and
  no faster than broad prospecting

If a fixture-generator tweak flattens the signal, or a transform bug inverts a ranking, these
fail loudly. They are a regression guard on the *point* of the project, not just the code.

### Reports — `test_report.py` (8)

- context assembly: weekly has 5 KPIs and the right chart keys; monthly has 2 tables; charts are
  real SVG strings
- `test_render_pdf_bytes` — output starts with `%PDF-` and is > 10 KB
- `test_monthly_narrative_flags_the_retargeting_trap` — the auto-generated prose names retargeting
  and says "care"/"reacquires", and no recommendation ever says "scale budget" into retargeting
- `test_weekly_does_not_push_budget_to_retargeting` — the weekly "shift budget" recommendation is
  scoped to acquisition strategies only

The last two are regression tests on a real bug: the first draft ranked purely by CAC and
recommended shifting budget into retargeting, contradicting the report's own narrative.

### Emit / deliver / pipeline — `test_emit.py` (5), `test_deliver.py` (5), `test_pipeline.py` (4)

- `test_emit` — the dashboard JSON has the right keys, sane headline numbers, and is **fully
  serialisable**: no `NaN`, no pandas `Timestamp` leaked through (a real risk when dumping
  dataframes)
- `test_deliver` — `LocalDeliverer` reports the path; `EmailDeliverer` gets a **`_FakeSMTP`**
  injected and the test asserts it called `starttls()`, `login()` with the right credentials and
  attached `report.pdf`; `DriveDeliverer` gets a fake Google service injected and the test checks
  the upload targets the right folder. No real SMTP server or Google credentials involved.
- `test_pipeline` — runs `main(["weekly", "--out", tmp, "--data-dir", tmp])` end to end into a
  temp directory and checks a real PDF, `dashboard.json` and a dated snapshot all appear;
  `--deliver` runs local delivery and prints `[ok]`

## Patterns used throughout

| Pattern | Where | Purpose |
|---|---|---|
| **Deterministic fixtures** | everything | exact assertions, offline, fast |
| **Reconciliation tests** | mock clients | totals must agree across levels / breakdowns |
| **Story tests** | transforms, reports | guard the narrative, not just the code |
| **Fake injection** (`FakeSession`, `_FakeSMTP`, fake Drive service) | real clients, delivery | test real I/O code with no network or credentials |
| **`tmp_path`** | pipeline, emit | end-to-end runs that write files, cleaned up automatically |
| **Module-scoped fixtures** | transform / report / emit tests | load the 20k-customer dataset once per file, not per test |

## A bug the tests caught

`test_monthly_pipeline_with_custom_as_of` failed with `ZeroDivisionError` on
`--as-of 2026-06-30`: customers acquired in July (after the report date) created a spend-free
July row, and the code picked that row's CAC (zero) as the denominator for blended LTV:CAC. The
fix was to make `emit.py` use "the last month that actually had spend". Without the test, the
pipeline would have shipped working only for its default date.
