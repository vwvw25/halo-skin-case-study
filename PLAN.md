# Meta Ads Reporting — Plan of Record

**Status:** design agreed, not yet built.
**Repo:** new, public GitHub repo (name TBD — suggest `meta-ads-ltv-reporting`).
**Nature:** portfolio project. Built against the real Meta Marketing API contract and a realistic
Shopify data model; ships with mock data providers so it runs end-to-end with no credentials.
Swapping in real tokens makes it live.

---

## 1. The story

Halo Skin is a fictional DTC **skincare** brand. It buys customers on Meta. The naive question is
"what was our ROAS this week"; the real question is **"which Meta choices acquire customers who are
worth more over time than they cost to acquire"** — i.e. LTV:CAC, not day-1 ROAS.

The project builds the pipeline that answers that: it joins **Meta spend** (Marketing API) against
**downstream customer revenue** (Shopify), computes contribution-margin LTV by acquisition cohort,
and attributes it back to the campaign / audience / placement that acquired each customer. Output is
a weekly operational PDF, a monthly strategic PDF, and an always-on dashboard.

Portfolio signal: this is a production-shaped integration and a genuine cross-source analytical
model, not a notebook. See [docs/data-sources.md](docs/data-sources.md) for how the
built-for-real-APIs / runs-on-mock-data architecture works.

---

## 2. Stack (decided)

| Layer               | Choice |
|---------------------|--------|
| Pipeline language   | Python, single language |
| Dep management      | `uv` + `pyproject.toml` |
| Meta API client     | `requests` + Pydantic models; `MockMetaClient` implements the same interface |
| Shopify data        | Pydantic models for orders/customers; `MockShopifyClient` reads seeded fixtures |
| Transform           | pandas |
| Charts              | matplotlib → static PNG/SVG embedded in the PDF |
| PDF                 | Jinja2 HTML/CSS templates → WeasyPrint |
| Dashboard           | **Next.js (App Router), deployed on Vercel free tier** — reads a versioned JSON the pipeline emits |
| Delivery            | `deliver()` interface; Drive (`google-api-python-client`) + email (`smtplib`) impls, disabled by default |
| Automation          | GitHub Actions `cron` — weekly + monthly schedules |

Not chosen: Streamlit (looks generic for a portfolio), a split Python/JS render pipeline
(WeasyPrint covers PDF without a second toolchain), any third-party attribution tool
(Triple Whale / Northbeam — the join is the point of the project).

---

## 3. Two report products + a dashboard

Reporting cadence matches decision cadence. LTV matures over months, so mature LTV analysis is
monthly; fast-maturing leading indicators are weekly.

### Weekly report — operational ("what do I adjust in Ads Manager this week")

- Fortnight-style comparison: this week vs last week.
- Spend & delivery.
- Acquisition volume & **CAC** by campaign / adset / segment.
- First-order contribution margin.
- **30-day repeat rate** (matures fast enough to be weekly).
- **Predicted** 12-mo LTV:CAC for the newest cohorts (from the fitted curve — see §5).
- **Predicted** target-cohort capture rate for recent cohorts (leading indicator — see §6).
- Recommended tactical actions: pause/scale adsets, creative swaps, budget nudges.

### Monthly deep-dive — strategic ("are we acquiring the right people, where does budget go")

- Full cohort maturation: every monthly acquisition cohort's LTV:CAC curve, realized + projected.
- LTV curve refit as another cohort crosses 90 days.
- **Realized** LTV:CAC and **realized** target-cohort capture by campaign / strategy tag /
  age / gender / region / placement / platform.
- Prediction grading: last quarter's predicted capture rates vs what actually happened.
- Recommendations: new lookalike seed lists, monthly budget split, target-ROAS resets, exclusions.

### Dashboard (Next.js / Vercel)

Always-on current state so nobody waits for a PDF: headline KPIs, spend & CAC trends, cohort LTV
curves as they stand today, segment LTV:CAC table, target-cohort capture rate. Reads
`data/report_<date>.json` emitted by the pipeline. The PDFs are the digest + the recommendations;
the dashboard is the live picture.

### Not building

- Quarterly report (a Meta-spending brand can't wait a quarter to catch a bad-LTV campaign; add a
  board roll-up template later if ever wanted).
- Individual-level targeting simulation, media-mix model, incrementality testing, ML LTV
  prediction (a transparent empirical cohort curve is more credible in a portfolio).

---

## 4. What we measure

| Metric | Definition | Source |
|---|---|---|
| **CAC** | Meta spend on acquisition campaigns ÷ new customers acquired, at campaign / adset / segment level | Meta spend + Shopify new-customer flag |
| **CM-LTV** | *Contribution-margin* LTV — cumulative gross margin per customer after COGS, shipping, payment fees, returns. Not revenue. | Shopify orders + per-SKU margin assumptions |
| **LTV horizon** | Fixed and explicit: **12-month CM-LTV**. Always shown as *realized-to-date* + *projected-to-12mo*. | — |
| **Payback period** | Months until cumulative CM per customer ≥ CAC | Both |
| **LTV:CAC** | 12-mo CM-LTV ÷ CAC, per segment. Health line 3:1; operational gate payback < ~4 months | Both |
| **30-day repeat rate** | Share of a cohort placing a 2nd order within 30 days | Shopify |

---

## 5. How we get an LTV number without waiting a year

- **Monthly acquisition cohorts.** Each customer belongs to the cohort of their acquisition month.
- Cohorts **6+ months old** are mature enough to **fit a repeat-purchase curve**: share of the
  cohort placing an Nth order by month *m*. Skincare has a natural ~60–100 day replenishment cycle,
  so this curve is well-behaved.
- Apply the fitted curve to **younger cohorts** to project their 12-month CM-LTV.
- Always display **realized vs projected** side by side — no hiding the extrapolation.
- Transparent empirical cohort curve, not a black box. (BG/NBD is a possible upgrade, noted only.)

### The two-clock principle

- **Fast clock → weekly report:** spend, CAC, new customers, first-order CM, 30-day repeat rate,
  *predicted* LTV:CAC of the just-acquired cohort. All mature inside a week or two.
- **Slow clock → monthly report:** cohort maturation picture, LTV:CAC by cohort as it ages,
  projected mature LTV:CAC for newer cohorts. Re-rendered each month, not framed as
  week-over-week.

---

## 6. The target cohort (the spine of the whole report)

Define Halo Skin's high-value customer **explicitly**:

> **Target cohort:** 3+ orders within the first 90 days, average order value above a set threshold,
> and at least one purchase from the premium SKU line.

(Exact thresholds set during fixture design so the mock data has a real spread — roughly top
15–25% of customers by value.)

**Target-cohort capture rate** = of the customers a given campaign / adset / segment acquired,
what share land in the target cohort.

This gives every section a single spine: *how well is each Meta choice acquiring **this** person.*
The punchline of a report reads like:

> "Reels prospecting to 35–44 women has a weaker day-1 ROAS but a 22% target-cohort capture rate
> vs 9% blended, 2.1× the blended LTV:CAC, and pays back in 2.3 months. Shift budget here and
> rebuild the lookalike from this segment's matured customers."

Weekly = *predicted* capture rate (from early signals like 2 orders in first 30 days).
Monthly = *realized* capture rate for matured cohorts, plus grading of past predictions.

---

## 7. How it ties back to Meta

Every Shopify customer carries `acquisition_campaign_id` (+ adset / ad where attribution allows).
In reality this comes from UTM params and/or a post-purchase "how did you hear about us" survey —
standard for skincare DTC.

That lets us roll **realized + projected CM-LTV** up by:

- **Campaign** and **strategy tag** (prospecting / lookalike / broad / retargeting)
- **Creative theme** (ads tagged in fixtures)
- **Meta breakdown dimensions** — age, gender, region, placement, platform — *where the customer
  record also carries that dimension* (age / gender / region usually yes; placement / platform
  only knowable via campaign structure)

Meta gives **spend & CAC** by segment; Shopify gives **LTV** by segment; the join gives
**LTV:CAC by segment**.

### Meta levers the reports drive (the "so what")

Every report ends in decisions someone makes in Ads Manager:

1. **Budget reallocation** between campaigns/adsets ranked by LTV:CAC, not ROAS.
2. **Lookalike seed refresh** — export matured high-LTV / target-cohort customers → new Custom
   Audience → new LAL.
3. **Targeting shifts** toward high-LTV age / geo / placement segments; exclusions on chronically
   low-LTV ones.
4. **Creative** — which themes bring repeat buyers vs one-and-done.
5. **Optimization event / target ROAS** — set Meta's value-optimization target from the *required*
   LTV:CAC rather than a guess.

---

## 8. Repo layout

```
meta-ads-ltv-reporting/
├── src/meta_reporting/
│   ├── sources/
│   │   ├── meta/
│   │   │   ├── client.py         # real Insights API request building + typed responses
│   │   │   ├── mock_client.py    # deterministic synthetic data, same interface
│   │   │   └── types.py          # Pydantic: Insights fields, breakdowns, response shapes
│   │   └── shopify/
│   │       ├── client.py         # real Shopify orders/customers (stub, contract only)
│   │       ├── mock_client.py    # reads seeded fixtures
│   │       └── types.py
│   ├── ingest.py                 # raw pulls → normalized DataFrames (meta_daily, orders, customers)
│   ├── transform/
│   │   ├── acquisition.py        # CAC, new-customer attribution, spend by segment
│   │   ├── cohorts.py            # monthly cohorts, repeat-purchase curve fit, CM-LTV realized+projected
│   │   ├── ltv_cac.py            # LTV:CAC + payback by segment
│   │   └── target_cohort.py      # target-cohort membership + capture rate (realized + predicted)
│   ├── report/
│   │   ├── weekly.html
│   │   ├── monthly.html
│   │   ├── styles.css
│   │   ├── charts.py
│   │   └── render.py             # context dict → HTML → PDF
│   ├── deliver.py                # deliver() interface + Local / Drive / Email impls
│   ├── emit.py                   # writes data/report_<date>.json for the dashboard
│   ├── config.py                 # env-driven; mock vs live per source
│   └── pipeline.py               # weekly | monthly entrypoints: pull → transform → render → emit → deliver
├── dashboard/                    # Next.js App Router app (Vercel)
├── fixtures/
│   ├── meta/                     # Insights API-shaped JSON, time_increment=1
│   └── shopify/                  # orders.json, customers.json
├── scripts/
│   ├── generate_meta_fixtures.py
│   └── generate_shopify_fixtures.py
├── reports/                      # generated PDFs (committed — repo shows output)
├── data/                         # emitted dashboard JSON (committed)
├── tests/
├── .github/workflows/
│   ├── weekly-report.yml         # cron, Mondays
│   └── monthly-report.yml        # cron, 1st of month
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 9. Mock data

Two seeded generators. Deterministic (fixed seed) so every report run is reproducible.

**Meta fixtures** — ~8–10 campaigns over ~15 months (need history for mature cohorts), daily
granularity, in exact `GET /{ad-account}/insights` shape with `time_increment=1`. Strategy tags:
prospecting, 2–3 lookalikes, broad, retargeting. Breakdowns: age, gender, region, placement,
platform. Deliberate story: weekend delivery dips, one lookalike scaling efficiently, one
prospecting campaign with rising CPA / creative fatigue, a mid-period creative refresh that
recovers CTR, stable always-on retargeting.

**Shopify fixtures** — customers with `acquisition_campaign_id`, `acquisition_date`, age / gender /
region; orders with line items, SKUs (premium vs core lines), margins, returns. Repeat-purchase
behavior **correlated with acquisition segment** so the target-cohort analysis has real signal:
the efficient lookalike and the 35–44 Reels segment over-index on the target cohort; retargeting
and one broad campaign under-index (they reacquire existing-adjacent low-LTV buyers).

---

## 10. Config / real-vs-mock

`META_REPORTING_MODE=mock|live` (default `mock`), independently per source:
`META_SOURCE=mock|live`, `SHOPIFY_SOURCE=mock|live`.

Live Meta requires: `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_API_VERSION`.
Live Shopify requires: `SHOPIFY_STORE`, `SHOPIFY_ADMIN_TOKEN`.
Delivery: off unless `DELIVER_CHANNEL=drive|email` set; then channel-specific secrets.
No secrets committed; `.env.example` documents everything.

---

## 11. Automation

- `.github/workflows/weekly-report.yml` — `cron` Mondays 06:00 UTC + `workflow_dispatch`.
- `.github/workflows/monthly-report.yml` — `cron` 1st of month 06:00 UTC + `workflow_dispatch`.
- Steps: checkout → setup `uv` → `python -m meta_reporting.pipeline {weekly|monthly}` →
  upload PDF as workflow artifact → commit PDF to `reports/` and JSON to `data/` →
  (if `DELIVER_CHANNEL` set) `deliver()`.
- Vercel auto-deploys the dashboard on push to `data/`.

---

## 12. Milestones

1. Repo scaffold: `pyproject.toml`, `uv`, README skeleton, CI lint/test job, `.env.example`.
2. `sources/meta` types + mock client + `generate_meta_fixtures.py` + fixtures.
3. `sources/shopify` types + mock client + `generate_shopify_fixtures.py` + fixtures.
4. `ingest.py` + `transform/acquisition.py` (CAC, spend by segment) + tests.
5. `transform/cohorts.py` — cohorts, curve fit, realized + projected CM-LTV + tests.
6. `transform/ltv_cac.py` + `transform/target_cohort.py` + tests.
7. `report/` weekly template + charts + WeasyPrint render → first weekly PDF in `reports/`.
8. `report/` monthly template → first monthly PDF in `reports/`.
9. `emit.py` → `data/report_<date>.json`; `deliver.py` interface + Local/Drive/Email impls
   (Drive/Email unit-tested, not wired live).
10. `pipeline.py` weekly + monthly entrypoints, end to end.
11. Next.js dashboard reading the emitted JSON; deploy to Vercel.
12. `weekly-report.yml` + `monthly-report.yml` workflows.
13. Real `sources/meta/client.py` against the live Insights contract; `sources/shopify/client.py`
    stub fleshed out. Keep mock/real interfaces in lockstep.
14. README polish: architecture diagram, sample PDFs, dashboard screenshots/link, "how to point
    at a real account".

---

## 13. Decisions made during the build

- **Repo:** `halo-skin-case-study` (github.com/vwvw25/halo-skin-case-study).
- **Target-cohort definition:** ≥3 orders in first 90 days, AOV ≥ $62, ≥1 premium SKU — lands
  ~20% of customers. Constants in `meta_reporting/domain.py`.
- **Margin model:** per-SKU COGS from `meta_reporting/catalog.py`, plus a flat shipping +
  payment-fee stack in `domain.py`.
- **Maturation curve:** empirical pooled — mean cumulative CM per customer by tenure month over
  the whole order history, with a small decayed tail past the last well-observed month. No
  parametric retention model (more defensible, easier to show). BG/NBD noted as a possible
  upgrade only.
- **Cohort projection:** multiplicative — `realized_cm * curve(12) / curve(observed_age)` — so a
  cohort keeps its over/under-index through the projection.
- **Attribution rate:** 0.82 (18% of Meta-acquired customers untagged); measured CAC is "cost
  per attributed new customer" and runs slightly high — appendix notes this.

## Still open

- Dashboard: confirm Vercel deploy (vs local-only + screenshots in README).
