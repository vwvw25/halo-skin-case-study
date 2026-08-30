# Halo Skin — Meta Ads LTV:CAC Reporting

[![CI](https://github.com/vwvw25/halo-skin-case-study/actions/workflows/ci.yml/badge.svg)](https://github.com/vwvw25/halo-skin-case-study/actions/workflows/ci.yml)

A portfolio case study: an automated pipeline that answers the question performance marketers
actually care about — **which Meta ad choices acquire customers worth more over time than they
cost to acquire** — not just "what was our ROAS this week."

"Halo Skin" is a fictional DTC skincare brand. The pipeline joins **Meta Marketing API** spend
against **Shopify** customer revenue, builds contribution-margin LTV by monthly acquisition
cohort, attributes it back to the campaign / audience / placement that acquired each customer,
and produces:

- a **weekly** operational PDF (spend, CAC, leading LTV indicators, tactical actions),
- a **monthly** strategic PDF (cohort maturation, realized LTV:CAC by segment, budget moves),
- an always-on **Next.js dashboard** → **[halo-skin-dashbaord.vercel.app](https://halo-skin-dashbaord.vercel.app)**.

It is built against the real API contracts but ships with **mock data providers**, so it runs
end to end with no credentials. Point it at a real ad account and Shopify store by setting a few
environment variables. See [docs/data-sources.md](docs/data-sources.md) for how the
mock/real seam works and what it does and doesn't guarantee.

> **Status:** functional end to end (pipeline → PDFs → dashboard, all under CI). See
> [PLAN.md](PLAN.md) for the design and remaining polish.

## Quick start

```bash
uv sync --extra dev
uv run halo-report weekly     # fully mock, no credentials needed
uv run pytest
```

PDF rendering uses WeasyPrint, which needs Pango/Cairo:

```bash
# macOS
brew install pango gdk-pixbuf
# Debian/Ubuntu
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0
```

Then generate the sample reports (into `reports/`):

```bash
uv run halo-report weekly              # → reports/*.pdf + data/dashboard.json
uv run halo-report monthly --as-of 2026-06-30
uv run halo-report monthly --deliver   # also send via DELIVER_CHANNEL
```

### Dashboard

`dashboard/` is a Next.js app (prerendered, no runtime backend) that reads `data/dashboard.json`.
Deployed on Vercel with Root Directory `dashboard`; a `prebuild` step syncs the data file in.

```bash
cd dashboard && npm install && npm run dev
```

### Automated reports

Two scheduled GitHub Actions run the pipeline and publish the result:

| Workflow | Schedule | Output |
|---|---|---|
| [`weekly-report.yml`](.github/workflows/weekly-report.yml) | Mondays 06:00 UTC | weekly PDF as a run artifact |
| [`monthly-report.yml`](.github/workflows/monthly-report.yml) | 1st of month 06:00 UTC | monthly PDF as a run artifact |

Both also refresh `data/dashboard.json` (which redeploys the dashboard) and, if a
`DELIVER_CHANNEL` repo variable is set, deliver the PDF via `deliver.py`. `workflow_dispatch`
triggers either by hand with an optional `--as-of` date. Against the mock sources the data is
deterministic so the commit is usually a no-op; the PDF artifact is produced every run.

## Configuration

Everything defaults to `mock`. Copy [`.env.example`](.env.example) to `.env` and set only what
you need:

| Variable | Purpose |
|---|---|
| `META_REPORTING_MODE` | global default mode for all sources: `mock` (default) or `live` |
| `META_SOURCE` / `SHOPIFY_SOURCE` | per-source override |
| `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_API_VERSION` | required when the Meta source is `live` |
| `SHOPIFY_STORE`, `SHOPIFY_ADMIN_TOKEN` | required when the Shopify source is `live` |
| `DELIVER_CHANNEL` | `local` / `drive` / `email`; delivery is off when unset |

## What's here so far

| Milestone | Status |
|---|---|
| 1. Scaffold (`pyproject`, config, CI) | ✅ |
| 2. Meta source — real + mock client, Insights types, seeded fixtures | ✅ |
| 3. Shopify source — orders/customers, real + mock client, seeded fixtures | ✅ |
| 4. Ingest layer — sources → tidy pandas frames, per-order contribution margin | ✅ |
| 5. Transform — maturation curve, cohort CM-LTV (realized + projected), LTV:CAC + payback | ✅ |
| 6. Transform — weekly acquisition topline, target-cohort capture (predicted + realized) | ✅ |
| 7. Weekly PDF — operational report (Jinja + WeasyPrint, matplotlib charts) | ✅ |
| 8. Monthly PDF — strategic deep-dive (cohort maturation, LTV:CAC, capture) | ✅ |
| 9. `emit.py` (dashboard JSON) + `deliver.py` (Local / Drive / Email) | ✅ |
| 10. `pipeline.py` — pull → transform → render → emit → deliver | ✅ |
| 11. Next.js dashboard (Recharts, deployed on Vercel) | ✅ |
| 12. GitHub Actions weekly/monthly report workflows | ✅ |
| 13. Live API client polish (kept in lockstep with the mocks) | ⬜ |
| 14. README previews (architecture diagram, sample PDF/dashboard shots) | ⬜ |

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

The suite runs against deterministic mock fixtures — no live API calls. See
[docs/testing.md](docs/testing.md) for what it covers and why.

## Docs

- [docs/data-sources.md](docs/data-sources.md) — the built-for-real-APIs / runs-on-mock-data seam
- [docs/testing.md](docs/testing.md) — what the test suite covers and why
- [docs/loyal-core-spec.md](docs/loyal-core-spec.md) — spec for the next feature: the
  retrospective "Loyal Core" cohort and the signal-vs-outcome analysis (designed, not built)
- [docs/next-project.md](docs/next-project.md) — where this goes next: a conversational
  analytics platform built on this transform layer

## License

MIT
