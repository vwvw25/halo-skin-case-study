# Next project — a conversational analytics platform

> This repo (Halo Skin — Meta Ads LTV:CAC Reporting) is milestone one. It builds the hard part:
> a trustworthy cross-source model that joins ad spend to downstream customer value. **The next
> project turns that engine into a platform you talk to.**

## The idea

An entire platform where a brand operator asks questions in plain English and gets back
**grounded answers, generated reports, and visualisations built on the fly** — not a fixed set
of dashboards.

- **Natural-language conversation** over the blended data ("How did last month go across ads &
  revenue — and where am I wasting spend?" / "Which cohorts have the best LTV?" / "What should I
  restock this week?").
- **On-the-fly report generation** — every answer can become a shareable report or a scheduled
  delivery (Slack, email) without anyone building a template first.
- **On-the-fly visualisation** — the model picks the right chart or table for the question and
  renders it inline, with the numbers behind it.

The current project's transform layer (`cohorts`, `ltv_cac`, `target_cohort`, `acquisition`,
`spend`) becomes the tool surface the conversational layer calls. The PDF renderer and the
dashboard become two of several output formats, not the product itself.

## Reference: Datadrew

The clearest existing expression of this vision is **[Datadrew](https://datadrew.io)** (Shopify
App Store: <https://apps.shopify.com/customer-lifetime-value>). Their marketing screenshots are
saved under [`reference/`](next-project/reference/) — see the manifest there for what each shows.

What Datadrew demonstrates that's directly relevant:

| Their feature | What it maps to here |
|---|---|
| "Drew AI" — ask across Shopify, Meta, Google Ads, GA4, Klaviyo | the conversational layer over our blended model |
| Charts & tables generated per answer | on-the-fly visualisation |
| "Ends with the move" — every answer closes with a recommended action | our reports already do this (narrative + recommendations); make it conversational |
| LTV Cohorts view (cumulative revenue per customer, heat table) | **already built** — `dashboard/components/CohortTable.tsx`, modelled on their layout |
| Product Intelligence / Creative Intelligence dashboards | new transform modules + views |
| "In your Slack. In your inbox. Every Monday." | our `deliver.py` (Local / Drive / Email) extended with Slack + scheduling |
| Datadrew MCP — live store data piped into Claude / ChatGPT | expose the transform layer as an MCP server |
| 1-click OAuth to 15+ sources | replace the mock/live env-var switch with real OAuth connectors |

## What this project already contributes

- A **defensible analytical core** — contribution-margin cohort LTV, a transparent maturation
  curve, target-cohort capture, LTV:CAC + payback by segment — all tested against deterministic
  fixtures ([docs/testing.md](testing.md)).
- The **built-for-real-APIs / runs-on-mock-data** pattern ([docs/data-sources.md](data-sources.md))
  — the conversational platform needs the same seam so it can be demoed without a connected store.
- Two **output renderers** (PDF via WeasyPrint, static dashboard via Next.js) and a
  **delivery interface** — the conversational layer routes answers to these.

## Rough shape of the next build

1. **MCP server** exposing the transform layer as typed tools (`cohort_ltv`, `ltv_cac_by_segment`,
   `capture_rate`, `weekly_topline`, …), each returning structured data + a renderable spec.
2. **Conversation orchestrator** — an LLM that plans which tools to call, composes the answer,
   and picks a visualisation. Grounded: every number traces to a tool result.
3. **On-the-fly renderer** — takes a spec (`{kind: "heat_table", ...}` / `{kind: "line", ...}`)
   and produces SVG/HTML for chat, plus a PDF/Slack variant.
4. **Real connectors** — OAuth for Shopify, Meta, Google Ads, Klaviyo; a warehouse/store layer
   replacing the fixture files.
5. **Scheduling + delivery** — "every Monday, post the weekly diagnosis to #growth-reports."
6. **Multi-store / agency workspaces** — one account, many brands' full stacks.
