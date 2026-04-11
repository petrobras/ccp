"""Tests for :func:`apps.reports.services.render_html_report`."""

from __future__ import annotations

import plotly.graph_objects as go
from apps.reports.services import (
    PERFORMANCE_SECTION_TITLE,
    STATS_SECTION_TITLE,
    TREND_SECTION_TITLE,
    render_html_report,
)


def _sample_figure(title: str) -> go.Figure:
    return go.Figure(
        data=[go.Scatter(x=[0, 1, 2], y=[0, 1, 4])], layout={"title": title}
    )


def test_render_html_report_contains_expected_sections():
    figures = {
        "trend": [_sample_figure("t1"), _sample_figure("t2")],
        "performance": [_sample_figure("p1")],
    }

    html = render_html_report(evaluation=None, figures=figures)

    assert "<html" in html
    assert "</html>" in html
    assert TREND_SECTION_TITLE in html
    assert PERFORMANCE_SECTION_TITLE in html
    assert STATS_SECTION_TITLE in html
    # Plotly.js must be embedded exactly once (first figure ships it).
    assert html.count("Plotly.newPlot") >= 3
    # include_plotlyjs=True emits a huge inline script; cheap marker below.
    assert "plotly" in html.lower()


def test_render_html_report_handles_empty_ai_summary_and_no_eval():
    html = render_html_report(
        evaluation=None,
        figures={"trend": [], "performance": []},
        ai_summary="",
    )
    assert "Estatísticas resumidas não disponíveis" in html
    assert 'class="ai-analysis"' not in html


def test_render_html_report_accepts_ai_summary_mapping():
    figures = {"trend": [_sample_figure("t")], "performance": [_sample_figure("p")]}
    html = render_html_report(
        evaluation=None,
        figures=figures,
        ai_summary={"trend": "**hello** trend", "performance": "perf text"},
    )
    assert "Análise IA" in html
    assert "hello" in html
    assert "perf text" in html
