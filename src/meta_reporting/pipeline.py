"""Pipeline entrypoints.

``main`` is the console-script target (``halo-report weekly|monthly``). The transform, render,
emit and deliver stages land in later milestones; for now this wires argument parsing to a
config load so the scaffold is runnable end to end.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from meta_reporting.config import Config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="halo-report", description=__doc__)
    parser.add_argument(
        "cadence",
        choices=["weekly", "monthly"],
        help="which report to build",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = Config.from_env()
    print(
        f"halo-report {args.cadence}: meta={config.meta.mode.value} "
        f"shopify={config.shopify.mode.value} "
        f"delivery={config.delivery.value if config.delivery else 'off'}"
    )
    print("pipeline stages not implemented yet — see PLAN.md milestones 4-10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
