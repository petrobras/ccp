"""HTMX endpoint that runs an evaluation and returns the results partial.

Unit 8 owns the URL wiring; this module only exposes the callables.
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.performance_evaluation.services.run_evaluation import run_evaluation

try:  # pragma: no cover
    from apps.reports.views import render_html_report
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.reports import render_html_report

try:  # pragma: no cover
    from apps.core.session_store import get_session
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.session_store import get_session


logger = logging.getLogger(__name__)


def _form_data_from_request(request: HttpRequest) -> dict[str, Any]:
    """Build a minimal ``form_data`` dict for the run_evaluation service.

    Unit 8's ``PerformanceEvaluationForm`` is expected to populate most
    of these fields via ``request.session`` / hidden inputs; this
    fallback lets the endpoint still function when called directly from
    a test or curl.
    """
    session_state = {}
    try:
        session_state = get_session(request.session.session_key or "anonymous") or {}
    except Exception:
        session_state = {}

    form_data: dict[str, Any] = dict(session_state)
    for key, value in request.POST.items():
        form_data[key] = value
    return form_data


@require_http_methods(["GET", "POST"])
def compute_view(request: HttpRequest) -> HttpResponse:
    """Run an evaluation and return the ``results.html`` partial.

    GET is accepted so operators can sanity-check the endpoint without
    going through HTMX.
    """
    session_id = request.session.session_key or request.GET.get("sid", "anonymous")

    if request.method == "GET":
        result: dict[str, Any] = {
            "evaluation": None,
            "figures": {},
            "trend": {"figures": {}, "regression": {}, "empty": True},
            "performance": {
                "figures": {},
                "empty": True,
                "cluster_idx": 0,
                "n_clusters": 0,
            },
            "summary_df": None,
            "ai_summary": "",
            "error": None,
        }
    else:
        form_data = _form_data_from_request(request)
        result = run_evaluation(form_data, session_id)

    context = {
        "result": result,
        "trend_figures": result.get("trend", {}).get("figures", {}),
        "perf_figures": result.get("performance", {}).get("figures", {}),
        "summary_df": result.get("summary_df"),
        "summary_html": (
            result["summary_df"].to_html(classes="ccp-summary", border=0)
            if result.get("summary_df") is not None
            else ""
        ),
        "ai_summary": result.get("ai_summary", ""),
        "error": result.get("error"),
        "n_clusters": result.get("performance", {}).get("n_clusters", 0),
    }
    return render(
        request,
        "performance_evaluation/results.html",
        context,
    )


@require_http_methods(["POST"])
def download_report_view(request: HttpRequest) -> HttpResponse:
    """Regenerate the HTML report and stream it as an attachment."""
    session_id = request.session.session_key or "anonymous"
    form_data = _form_data_from_request(request)
    result = run_evaluation(form_data, session_id)
    html = render_html_report(
        result.get("evaluation"),
        result.get("figures", {}),
        result.get("ai_summary", ""),
    )
    response = HttpResponse(html, content_type="text/html")
    response["Content-Disposition"] = (
        'attachment; filename="ccp_performance_report.html"'
    )
    return response


__all__ = ["compute_view", "download_report_view"]
