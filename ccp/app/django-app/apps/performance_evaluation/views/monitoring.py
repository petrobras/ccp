"""HTMX poll endpoints for the online monitoring panel.

Unit 8 is responsible for exposing these under concrete URL patterns;
this module ships the callables and an ``additional_urls.py`` hint in
the ``services`` package.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.performance_evaluation.services import figures as _figures
from apps.performance_evaluation.services import monitoring_state

try:  # pragma: no cover
    from apps.integrations.pi_client import fetch_pi_data
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.integrations import fetch_pi_data

try:  # pragma: no cover
    from apps.core.session_store import get_session
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.session_store import get_session


logger = logging.getLogger(__name__)


def _session_id(request: HttpRequest) -> str:
    return request.session.session_key or request.GET.get("sid", "anonymous")


@require_http_methods(["POST"])
def start_monitoring_view(request: HttpRequest) -> HttpResponse:
    """Flip the monitoring flag on and return the trends partial."""
    session_id = _session_id(request)
    monitoring_state.set_active(session_id, True)
    monitoring_state.set_last_fetch(session_id)
    return render(
        request,
        "performance_evaluation/_trends.html",
        {"trend_figures": {}, "monitoring": monitoring_state.snapshot(session_id)},
    )


@require_http_methods(["POST"])
def stop_monitoring_view(request: HttpRequest) -> HttpResponse:
    """Flip the monitoring flag off."""
    session_id = _session_id(request)
    monitoring_state.set_active(session_id, False)
    return JsonResponse(monitoring_state.snapshot(session_id))


@require_http_methods(["GET", "POST"])
def poll_view(request: HttpRequest) -> HttpResponse:
    """Poll endpoint returning the freshly rebuilt trends partial.

    Fetches new data from PI, appends to the Redis-backed accumulator,
    rebuilds the trend figures from the accumulated history and returns
    the ``_trends.html`` partial.
    """
    session_id = _session_id(request)

    session_state = get_session(session_id) or {}
    tag_mappings: dict[str, Any] = session_state.get("tag_mappings", {})

    new_rows: pd.DataFrame
    try:
        new_rows = fetch_pi_data(tag_mappings, testing=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("fetch_pi_data failed: %s", exc)
        new_rows = pd.DataFrame()

    accumulated = monitoring_state.append_accumulated_results(
        session_id, new_rows, keep=5
    )
    monitoring_state.set_last_fetch(session_id)

    class _Snapshot:
        """Lightweight Evaluation-shaped object for figure builders."""

        def __init__(self, df: pd.DataFrame) -> None:
            self.df = df
            self.impellers_new: list[Any] = []

    trend_result = _figures.build_trend_figures(_Snapshot(accumulated))

    return render(
        request,
        "performance_evaluation/_trends.html",
        {
            "trend_figures": trend_result.get("figures", {}),
            "monitoring": monitoring_state.snapshot(session_id),
        },
    )


__all__ = ["poll_view", "start_monitoring_view", "stop_monitoring_view"]
