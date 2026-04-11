"""Re-export of the core ``ccp_tags`` library.

At merge time Unit 4 provides ``apps.core.templatetags.ccp_tags``. This shim
imports from there when available and falls back to the local stub
implementation so the back-to-back page can be loaded in isolation.

# STUB: replaced by Unit 4's ``apps.core.templatetags.ccp_tags`` at merge time
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

try:  # pragma: no cover - real implementation lives in Unit 4
    from apps.core.templatetags.ccp_tags import (  # type: ignore
        expander as _expander,
        parameter_row as _parameter_row,
        plotly_figure as _plotly_figure,
    )
except Exception:  # noqa: BLE001
    _expander = None
    _parameter_row = None
    _plotly_figure = None


@register.simple_tag
def plotly_figure(fig, div_id=None):
    """Render a Plotly figure as inline HTML (no full page)."""
    if _plotly_figure is not None:
        return _plotly_figure(fig, div_id=div_id)
    if fig is None:
        return ""
    try:
        import plotly.io as pio

        return mark_safe(pio.to_html(fig, full_html=False, include_plotlyjs=False))
    except Exception:  # noqa: BLE001
        return ""


@register.inclusion_tag("core/partials/expander.html")
def expander(title, body_id, expanded=False):
    """Collapsible section tag matching the Streamlit expander look."""
    if _expander is not None:
        return _expander(title, body_id, expanded)
    return {"title": title, "body_id": body_id, "expanded": expanded}


@register.inclusion_tag("core/partials/parameter_row.html")
def parameter_row(key, value, unit_choices):
    """Render a single labelled parameter row."""
    if _parameter_row is not None:
        return _parameter_row(key, value, unit_choices)
    return {"key": key, "value": value, "unit_choices": unit_choices}
