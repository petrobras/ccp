"""Tests for the :mod:`apps.reports.views` endpoints."""

from __future__ import annotations

import plotly.graph_objects as go
from apps.reports._stubs import session_store
from django.test import Client


def _seed_session(session_id: str) -> None:
    session_store.set_session(
        session_id,
        {
            "evaluation": None,
            "figures": {
                "trend": [go.Figure(data=[go.Scatter(x=[0, 1], y=[0, 1])])],
                "performance": [go.Figure(data=[go.Scatter(x=[0, 1], y=[1, 0])])],
            },
            "ai_summary": "",
        },
    )


def test_report_view_returns_html_for_seeded_session():
    session_id = "abc123"
    _seed_session(session_id)

    response = Client().get(f"/reports/{session_id}/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    body = response.content.decode()
    assert "<html" in body
    assert "Relatório de Avaliação de Desempenho" in body


def test_report_view_returns_404_when_session_missing():
    response = Client().get("/reports/nonexistent/")
    assert response.status_code == 404


def test_report_download_sets_attachment_header():
    session_id = "dl42"
    _seed_session(session_id)

    response = Client().get(f"/reports/{session_id}/download/")

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    assert f"ccp_report_{session_id}.html" in response["Content-Disposition"]
