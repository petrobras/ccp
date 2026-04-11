"""HTTP-level smoke tests for the compute and monitoring views."""

from __future__ import annotations

from django.test import Client


def test_compute_view_get_returns_results_partial():
    client = Client()
    response = client.get("/performance-evaluation/compute/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Avaliação de Desempenho" in body
    assert "Run Evaluation" in body or "Nenhum dado" in body


def test_monitoring_start_and_stop_endpoints():
    client = Client()
    start = client.post("/performance-evaluation/monitoring/start/")
    assert start.status_code == 200

    stop = client.post("/performance-evaluation/monitoring/stop/")
    assert stop.status_code == 200
    payload = stop.json()
    assert payload["active"] is False


def test_monitoring_poll_returns_trends_partial():
    client = Client()
    response = client.get("/performance-evaluation/monitoring/poll/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "ccp-trends" in body or "Tendências" in body
