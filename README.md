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
environment variables.

> **Status:** early build. See [PLAN.md](PLAN.md) for the full design and the milestone list.

## Quick start

```bash
uv sync --extra dev
uv run halo-report weekly     # fully mock, no credentials needed
uv run pytest
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
| 2–3. Mock Meta + Shopify sources & fixtures | ⬜ |
| 4–6. Ingest & transform (CAC, cohorts, LTV:CAC, target cohort) | ⬜ |
| 7–8. Weekly & monthly PDF reports | ⬜ |
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
