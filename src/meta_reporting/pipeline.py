"""Pipeline entrypoint: pull -> transform -> render -> emit -> deliver.

    halo-report weekly   [--as-of 2026-07-31] [--out reports] [--deliver]
    halo-report monthly

Sources are mock or live per the environment (see meta_reporting.config). Delivery only runs
with ``--deliver`` and a ``DELIVER_CHANNEL`` set.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from meta_reporting.config import Config
from meta_reporting.deliver import get_deliverer
from meta_reporting.emit import build_dashboard_data, write_dashboard_data
from meta_reporting.report.render import build_report
from meta_reporting.sources.meta.base import get_meta_source
from meta_reporting.sources.shopify.base import get_shopify_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="halo-report", description=__doc__)
    parser.add_argument("cadence", choices=["weekly", "monthly"], help="which report to build")
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date(2026, 7, 31),
        help="report date (YYYY-MM-DD); defaults to the end of the mock data",
    )
    parser.add_argument("--out", type=Path, default=Path("reports"), help="output directory")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="dashboard data dir")
    parser.add_argument(
        "--deliver", action="store_true", help="deliver via DELIVER_CHANNEL after rendering"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = Config.from_env()
    meta = get_meta_source(config.meta)
    shopify = get_shopify_source(config.shopify)

    print(
        f"halo-report {args.cadence} as of {args.as_of} — "
        f"meta={config.meta.mode.value} shopify={config.shopify.mode.value}"
    )

    pdf = build_report(meta, shopify, as_of=args.as_of, cadence=args.cadence, out_dir=args.out)
    print(f"  report  {pdf}")

    data = build_dashboard_data(meta, shopify, as_of=args.as_of)
    dashboard = write_dashboard_data(data, args.data_dir)
    print(f"  data    {dashboard}")

    if args.deliver:
        result = get_deliverer(config).deliver(
            pdf, subject=f"Halo Skin {args.cadence} report — {args.as_of}"
        )
        status = "ok" if result.ok else "FAILED"
        print(f"  deliver {result.channel} -> {result.destination} [{status}] {result.detail}")
    elif config.delivery is not None:
        print(
            f"  deliver skipped (DELIVER_CHANNEL={config.delivery.value}, pass --deliver to send)"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
