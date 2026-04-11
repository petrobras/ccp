"""Template tags and filters for the ccp Django app.

Exposes helpers for rendering shared UI partials (parameter row,
expander) and embedding Plotly figures produced by the ``ccp`` library.
"""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def plotly_figure(fig, div_id: str | None = None) -> str:
    """Render a plotly figure as an inline HTML fragment.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        Figure to serialise. ``base.html`` is expected to load
        ``plotly.min.js`` exactly once, so this tag never inlines
        the library.
    div_id : str, optional
        Explicit ``id`` for the generated ``<div>``.

    Returns
    -------
    str
        Safe HTML ready to be injected into a Django template.
    """
    import plotly.io as pio

    html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
    )
    return mark_safe(html)


@register.inclusion_tag("core/partials/parameter_row.html")
def parameter_row(
    key: str,
    value=None,
    units=None,
    selected_unit: str | None = None,
    label: str | None = None,
    help: str = "",
):
    """Render a labeled parameter input row."""
    return {
        "key": key,
        "label": label or key,
        "value": value,
        "units": units or [],
        "selected_unit": selected_unit,
        "help": help,
    }


@register.inclusion_tag("core/partials/expander.html")
def expander(title: str, body_id: str, expanded: bool = False):
    """Render an expander header. Body is injected via a ``body`` context variable."""
    return {
        "title": title,
        "body_id": body_id,
        "expanded": expanded,
        "body": "",
    }


@register.filter
def format_quantity(q) -> str:
    """Render a :class:`pint.Quantity` as ``"<magnitude> <units>"``.

    Falls back to ``str(q)`` when the input is not a pint quantity.
    """
    magnitude = getattr(q, "magnitude", None)
    units = getattr(q, "units", None)
    if magnitude is None or units is None:
        return str(q)
    return f"{magnitude} {units}"
