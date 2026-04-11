# STUB: replaced by Unit 10 at merge time
"""Placeholder HTML report renderer used until Unit 10 lands."""

from __future__ import annotations

from typing import Any


def render_html_report(
    evaluation: Any,
    figures: dict[str, Any],
    ai_summary: str = "",
) -> str:
    """Return a minimal HTML document describing ``evaluation``."""
    title = "ccp Performance Report"
    count = len(figures or {})
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title></head><body>"
        f"<h1>{title}</h1><p>Figures: {count}</p>"
        f"<pre>{ai_summary}</pre></body></html>"
    )
