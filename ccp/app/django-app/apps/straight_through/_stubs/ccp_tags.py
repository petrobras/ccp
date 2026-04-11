# STUB: replaced by Unit 4 at merge time
"""Local template tag library mirroring the Unit 4 public API."""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def plotly_figure(fig, div_id: str | None = None):
    """Render a Plotly figure inline without re-embedding ``plotly.js``."""
    if fig is None or fig == "":
        return ""
    try:
        import plotly.io as pio
    except ImportError:
        return ""
    html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
    )
    return mark_safe(html)


@register.inclusion_tag("straight_through/_expander.html")
def expander(title: str, body_id: str, expanded: bool = False):
    """Render a collapsible section header."""
    return {"title": title, "body_id": body_id, "expanded": expanded}


@register.inclusion_tag("straight_through/_parameter_row.html")
def parameter_row(key: str, value: str, unit_choices: list[str]):
    """Render a labelled input row with unit selector."""
    return {"key": key, "value": value, "unit_choices": unit_choices}
