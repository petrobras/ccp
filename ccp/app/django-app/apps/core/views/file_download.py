"""File download endpoints."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from apps.core.exports.to_excel import session_to_excel

try:  # pragma: no cover - real module provided by Unit 3 at merge time
    from apps.core.storage.ccp_file_exporter import export_ccp_file
except ImportError:  # pragma: no cover
    from apps.core._stubs.ccp_file_exporter import export_ccp_file

try:  # pragma: no cover
    from apps.core.session_store import get_session
except ImportError:  # pragma: no cover
    from apps.core._stubs.session_store import get_session


def _load_state(session_id: str) -> dict | None:
    state = get_session(session_id)
    return state or None


@require_GET
def download_ccp(request: HttpRequest, session_id: str) -> HttpResponse:
    """Return the session state packaged as a ``.ccp`` archive."""
    state = _load_state(session_id)
    if state is None:
        return JsonResponse({"error": "unknown session"}, status=404)
    payload = export_ccp_file(state)
    response = HttpResponse(payload, content_type="application/zip")
    name = state.get("name") or f"{session_id}.ccp"
    if not name.endswith(".ccp"):
        name = f"{name}.ccp"
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response


@require_GET
def download_excel(request: HttpRequest, session_id: str) -> HttpResponse:
    """Return the session state as an ``.xlsx`` workbook."""
    state = _load_state(session_id)
    if state is None:
        return JsonResponse({"error": "unknown session"}, status=404)
    payload = session_to_excel(state)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    base = state.get("name") or session_id
    if base.endswith(".ccp"):
        base = base[:-4]
    response["Content-Disposition"] = f'attachment; filename="{base}.xlsx"'
    return response
