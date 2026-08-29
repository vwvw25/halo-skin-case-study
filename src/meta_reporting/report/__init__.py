"""Report layer — transforms to a designed PDF (weekly operational, monthly strategic)."""

from meta_reporting.report.context import ReportContext, build_context
from meta_reporting.report.render import build_report, render_html, render_pdf

__all__ = ["ReportContext", "build_context", "build_report", "render_html", "render_pdf"]
