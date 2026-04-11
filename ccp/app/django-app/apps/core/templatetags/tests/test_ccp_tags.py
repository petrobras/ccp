"""Tests for custom template tags/filters in ``apps.core.templatetags.ccp_tags``."""

from __future__ import annotations

import plotly.graph_objects as go
from django.template import Context, Template

from apps.core.templatetags.ccp_tags import format_quantity


def _render(source: str, context: dict | None = None) -> str:
    return Template(source).render(Context(context or {}))


def test_plotly_figure_tag_returns_inline_html():
    fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[4, 5, 6])])
    html = _render(
        "{% plotly_figure fig div_id='my-plot' %}",
        {"fig": fig},
    )
    assert 'id="my-plot"' in html
    assert "plotly" in html.lower()
    assert "<html" not in html  # full_html=False


def test_parameter_row_inclusion_tag_renders_partial():
    html = _render(
        "{% parameter_row key='flow' value=100 units=units selected_unit='kg/s' help='Fluxo' %}",
        {"units": ["kg/s", "kg/h"]},
    )
    assert "ccp-param-row" in html
    assert 'name="flow"' in html
    assert "Fluxo" in html


def test_expander_inclusion_tag_renders_title():
    html = _render(
        "{% expander title='Opções' body_id='opts' expanded=True %}",
    )
    assert "ccp-expander" in html
    assert "Opções" in html
    assert 'id="opts"' in html


def test_format_quantity_with_pint():
    try:
        import pint
    except ImportError:  # pragma: no cover - pint is a hard dep of ccp
        return
    ureg = pint.UnitRegistry()
    q = 2.5 * ureg.bar
    rendered = format_quantity(q)
    assert "2.5" in rendered
    assert "bar" in rendered


def test_format_quantity_falls_back_to_str():
    assert format_quantity(42) == "42"
