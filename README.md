# Halo Skin — Meta Ads LTV:CAC Reporting

A portfolio case study: an automated pipeline that answers the question performance marketers
actually care about — **which Meta ad choices acquire customers worth more over time than they
cost to acquire** — not just "what was our ROAS this week."

"Halo Skin" is a fictional DTC skincare brand. The pipeline joins **Meta Marketing API** spend
against **Shopify** customer revenue, builds contribution-margin LTV by monthly acquisition
cohort, attributes it back to the campaign / audience / placement that acquired each customer,
and produces:

- a **weekly** operational PDF (spend, CAC, leading LTV indicators, tactical actions),
- a **monthly** strategic PDF (cohort maturation, realized LTV:CAC by segment, budget moves),
- an always-on **Next.js dashboard**.

It is built against the real API contracts but ships with **mock data providers**, so it runs
end to end with no credentials. Point it at a real ad account and Shopify store by setting a few
environment variables. See [docs/data-sources.md](docs/data-sources.md) for how the
mock/real seam works and what it does and doesn't guarantee.

> **Status:** early build. See [PLAN.md](PLAN.md) for the full design and the milestone list.

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
uv run python -m meta_reporting.report   # or use the pipeline once wired (milestone 10)
```

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
| 9–10. Emit, delivery, pipeline wiring | ⬜ |
| 11. Next.js dashboard | ⬜ |
| 12. GitHub Actions automation | ⬜ |
| 13–14. Live API clients, README polish | ⬜ |

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```

## License

MIT
