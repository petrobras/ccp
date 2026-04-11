"""Stub template tag library for offline tests.

Provides a trivial :func:`plotly_figure` implementation so the templates
render to plain HTML without loading the real Unit 4 partials.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def plotly_figure(fig, div_id=None):
    """Return a placeholder ``<div>`` for a plotly figure."""
    name = div_id or getattr(fig, "layout", None)
    title = ""
    if fig is not None and hasattr(fig, "layout"):
        title = getattr(fig.layout, "title", None)
        if title is not None:
            title = getattr(title, "text", "") or ""
    return mark_safe(f'<div class="ccp-plotly">{title}</div>')
