"""Render a :class:`ReportContext` to HTML and then to PDF bytes via WeasyPrint."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from meta_reporting.report._weasyprint import HTML
from meta_reporting.report.context import ReportContext, build_context
from meta_reporting.sources.meta import MetaSource
from meta_reporting.sources.shopify import ShopifySource

_TEMPLATES = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(_TEMPLATES),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
_env.filters["safe_svg"] = lambda s: s  # svg strings are ours, not user input


def render_html(ctx: ReportContext) -> str:
    template = _env.get_template(f"{ctx.cadence}.html")
    return template.render(ctx=ctx, **asdict(ctx))


def render_pdf(ctx: ReportContext) -> bytes:
    return HTML(string=render_html(ctx), base_url=str(_TEMPLATES)).write_pdf()


def build_report(
    meta: MetaSource,
    shopify: ShopifySource,
    *,
    as_of: date,
    cadence: str,
    out_dir: Path,
) -> Path:
    ctx = build_context(meta, shopify, as_of=as_of, cadence=cadence)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"halo-skin-{cadence}-{as_of.isoformat()}.pdf"
    path.write_bytes(render_pdf(ctx))
    return path
