# Data sources: built for the real APIs, runs on mock data

The pipeline is written against the real **Meta Marketing API** and **Shopify Admin API**
contracts, but every default run uses local mock data. This document explains how that works and
what it does and doesn't guarantee.

## One interface, two implementations per source

Each external system is defined by a `Protocol`. Two classes implement it: a real client and a
mock client.

```
MetaSource (Protocol)
├── MetaClient        — real: builds Meta Marketing API /insights requests, parses responses,
│                        handles cursor pagination, retries, and error envelopes
└── MockMetaClient    — reads fixtures/meta/*.json, filters by date range / level / breakdowns,
                         returns the same typed objects

ShopifySource (Protocol)
├── ShopifyClient       — real: Shopify Admin API orders + customers, Link-header pagination
└── MockShopifyClient   — reads fixtures/shopify/*.json
```

Everything downstream — `ingest`, `transform`, `report`, `emit`, `deliver` — depends only on the
`Protocol`. It never knows or cares which implementation it received. This is the seam that keeps
tests and demos hermetic while leaving a real integration one config flag away.

## How the implementation is chosen

`config.py` resolves the mode from environment variables, independently per source:

| Variable | Effect |
|---|---|
| `META_REPORTING_MODE` | global default for every source — `mock` (default) or `live` |
| `META_SOURCE` / `SHOPIFY_SOURCE` | per-source override of the global default |
| `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_API_VERSION` | required when the Meta source is `live` |
| `SHOPIFY_STORE`, `SHOPIFY_ADMIN_TOKEN` | required when the Shopify source is `live` |

With nothing set, both sources are `mock` and the pipeline runs fully offline. Setting a source to
`live` without its credentials raises `ConfigError` at startup rather than failing mid-run.

## What "built for the API" actually means

It is not a simplified stand-in that would need rewriting for real use. Specifically:

1. **Types match the real payloads.** The Pydantic models use the actual API field names and
   response envelopes — Meta's `{ "data": [...], "paging": { "cursors": {...} } }`, Shopify's
   `{ "orders": [...] }` with cursor/Link pagination — not a convenient flattened shape.

2. **Fixtures are stored in that same shape.** `fixtures/meta/*.json` contains what
   `GET /{ad-account}/insights?time_increment=1&level=campaign&breakdowns=age,gender` would
   actually return, date range by date range. The mock client does real filtering and
   deserialization over it; it does not return a hand-tailored answer per call.

3. **The real client's logic is complete and unit-tested.** Request building, parameter
   encoding, cursor pagination, rate-limit/backoff handling, and error-envelope parsing are all
   implemented and covered by tests that feed the client synthetic/recorded responses.

## The honest caveat

The real clients are tested **to the documented contract and against fixtures**, not against a
live account in production. Unless real credentials are supplied, no request has actually hit
Meta or Shopify. Going live is a configuration change — set the mode and the credentials — with
no code changes, but the first live run is where real-world quirks (undocumented nulls,
deprecations, account-specific permissions) would first surface. The README states this plainly.

## Why the project is built this way

Designing to an external contract while keeping the test and demo path hermetic is what real
integration work looks like. A portfolio project that only runs when someone hands it API keys
demonstrates less than one that runs anywhere, ships realistic data, and has a clearly marked
seam where the real API takes over.
