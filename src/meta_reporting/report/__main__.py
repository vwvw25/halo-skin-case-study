"""``python -m meta_reporting.report`` — render both sample reports against the mock sources."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from meta_reporting.report.render import build_report
from meta_reporting.sources.meta import MockMetaClient
from meta_reporting.sources.shopify import MockShopifyClient

_AS_OF = date(2026, 7, 31)


def main() -> None:
    out = Path("reports")
    for cadence in ("weekly", "monthly"):
        built = build_report(
            MockMetaClient(), MockShopifyClient(), as_of=_AS_OF, cadence=cadence, out_dir=out
        )
        print(f"wrote {built}")


if __name__ == "__main__":
    main()
