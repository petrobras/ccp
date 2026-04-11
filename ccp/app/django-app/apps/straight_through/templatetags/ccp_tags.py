# STUB: replaced by Unit 4 at merge time
"""Minimal ``ccp_tags`` template library local to the straight-through app.

Exists so ``{% load ccp_tags %}`` works in isolation. Unit 4 will ship the
canonical implementation under ``apps.core.templatetags``; Django's template
tag loader resolves library names lexically, so once Unit 4 is merged this
file becomes redundant and can be deleted.
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def plotly_figure(fig, div_id: str | None = None):
    """Render a Plotly figure inline, reusing the shared ``plotly.js`` bundle."""
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
