"""File upload endpoints.

Replaces the Streamlit ``st.file_uploader`` calls scattered across the
original app with Django views that accept multipart POSTs, push payloads
through the shared ``apps.core.storage`` / ``apps.core.session_store``
layer, and return JSON so HTMX/Alpine front-ends can react.
"""

from __future__ import annotations

import base64
from typing import Any

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

try:  # pragma: no cover - real module provided by Unit 3 at merge time
    from apps.core.storage.ccp_file_importer import load_ccp_file
except ImportError:  # pragma: no cover
    from apps.core._stubs.ccp_file_importer import load_ccp_file

try:  # pragma: no cover
    from apps.core.session_store import (
        get_session,
        new_session_id,
        set_session,
    )
except ImportError:  # pragma: no cover
    from apps.core._stubs.session_store import (
        get_session,
        new_session_id,
        set_session,
    )


_DEFAULT_MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB, matching Streamlit.


def _max_upload_size() -> int:
    return int(getattr(settings, "CCP_MAX_UPLOAD_SIZE", _DEFAULT_MAX_UPLOAD_SIZE))


def _too_large(request: HttpRequest) -> JsonResponse | None:
    limit = _max_upload_size()
    length = request.META.get("CONTENT_LENGTH")
    if length:
        try:
            if int(length) > limit:
                return JsonResponse(
                    {"error": "file too large", "limit": limit},
                    status=413,
                )
        except ValueError:
            pass
    return None


def _require_file(
    request: HttpRequest, field: str = "file"
) -> tuple[Any | None, JsonResponse | None]:
    too_big = _too_large(request)
    if too_big is not None:
        return None, too_big
    upload = request.FILES.get(field)
    if upload is None:
        return None, JsonResponse(
            {"error": f"missing file field '{field}'"}, status=400
        )
    if upload.size > _max_upload_size():
        return None, JsonResponse(
            {"error": "file too large", "limit": _max_upload_size()},
            status=413,
        )
    return upload, None


@csrf_exempt
@require_POST
def upload_ccp(request: HttpRequest) -> JsonResponse:
    """Accept a ``.ccp`` archive and persist it as a new session.

    Returns
    -------
    JsonResponse
        ``{"session_id": str, "keys": [..]}`` on success.
    """
    upload, err = _require_file(request)
    if err is not None:
        return err
    try:
        state = load_ccp_file(upload)
    except Exception as exc:  # pragma: no cover - defensive
        return JsonResponse({"error": f"invalid .ccp file: {exc}"}, status=400)

    session_id = new_session_id()
    state.setdefault("name", upload.name)
    set_session(session_id, state)
    return JsonResponse(
        {
            "session_id": session_id,
            "name": upload.name,
            "keys": sorted(k for k in state.keys() if isinstance(k, str)),
        }
    )


@csrf_exempt
@require_POST
def upload_csv(request: HttpRequest) -> JsonResponse:
    """Accept an engauge CSV export and return its parsed text.

    The real parsing lives in Unit 7's curves-conversion services; this
    endpoint simply decodes the upload, stashes it on an optional
    session, and echoes it back so the caller can display a preview.
    """
    upload, err = _require_file(request)
    if err is not None:
        return err
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return JsonResponse({"error": "csv must be utf-8"}, status=400)

    session_id = request.POST.get("session_id")
    if session_id:
        state = get_session(session_id)
        state.setdefault("engauge_csvs", {})[upload.name] = text
        set_session(session_id, state)

    return JsonResponse(
        {
            "name": upload.name,
            "bytes": upload.size,
            "content": text,
            "session_id": session_id,
        }
    )


@csrf_exempt
@require_POST
def upload_curve_png(request: HttpRequest) -> JsonResponse:
    """Accept a PNG image of a curve and store it on the session state.

    Parameters
    ----------
    request : HttpRequest
        The POST must carry a ``file`` field (the PNG) and a
        ``session_id`` form field identifying the target session. An
        optional ``key`` field selects the session-state slot;
        otherwise the file name is used.
    """
    upload, err = _require_file(request)
    if err is not None:
        return err
    session_id = request.POST.get("session_id") or new_session_id()
    key = request.POST.get("key") or upload.name
    payload = upload.read()

    state = get_session(session_id)
    state.setdefault("curve_pngs", {})[key] = base64.b64encode(payload).decode("ascii")
    set_session(session_id, state)

    return JsonResponse(
        {
            "session_id": session_id,
            "key": key,
            "bytes": len(payload),
            "url": f"/core/download/curve-png/{session_id}/{key}/",
        }
    )
