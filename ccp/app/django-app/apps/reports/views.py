"""Views for :mod:`apps.reports`.

Two endpoints are exposed:

* ``GET /reports/<session_id>/`` — render the HTML report inline.
* ``GET /reports/<session_id>/download/`` — same payload, served as an
  ``attachment`` so browsers save it to disk.
"""

from __future__ import annotations

from typing import Any

from django.http import Http404, HttpRequest, HttpResponse

from .services import render_html_report

try:
    from apps.core.session_store import get_session
except ImportError:  # pragma: no cover - stub fallback
    from apps.reports._stubs.session_store import get_session

try:
    from apps.core.storage import ccp_file_importer  # noqa: F401
except ImportError:  # pragma: no cover - stub fallback
    from apps.reports._stubs import ccp_file_importer  # noqa: F401


def _load_report_payload(session_id: str) -> tuple[Any, dict, Any]:
    """Load evaluation, figures and AI summary from the session store."""
    state = get_session(session_id)
    if state is None:
        raise Http404(f"Session {session_id!r} not found")
    evaluation = state.get("evaluation")
    figures = state.get("figures") or {}
    ai_summary = state.get("ai_summary", "")
    return evaluation, figures, ai_summary


def _build_response(session_id: str, *, attachment: bool) -> HttpResponse:
    """Render the report and wrap it in an ``HttpResponse``."""
    evaluation, figures, ai_summary = _load_report_payload(session_id)
    html = render_html_report(evaluation, figures, ai_summary=ai_summary)
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    if attachment:
        filename = f"ccp_report_{session_id}.html"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def report_view(request: HttpRequest, session_id: str) -> HttpResponse:
    """Render the HTML performance report for ``session_id``."""
    return _build_response(session_id, attachment=False)


def report_download(request: HttpRequest, session_id: str) -> HttpResponse:
    """Return the HTML report as a downloadable attachment."""
    return _build_response(session_id, attachment=True)
