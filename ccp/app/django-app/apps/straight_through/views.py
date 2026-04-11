"""Views for the straight-through compressor page.

Endpoints
---------
``/`` (``index``)
    Render the full page, hydrated from the Redis-backed session store.
``/compute/``
    HTMX POST that runs the calculation and returns the ``_results.html``
    partial for inline replacement.
``/upload-curve/``
    HTMX POST that stores an uploaded curve PNG on the session.
``/save.ccp``
    Download the current session state as a ``.ccp`` archive.
``/load.ccp``
    Upload a ``.ccp`` archive, hydrate the session, and redirect to ``/``.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.straight_through import services
from apps.straight_through.forms import (
    CurveUploadForm,
    GuaranteePointForm,
    SidebarOptionsForm,
)

try:
    from apps.core.session_store import get_session, set_session  # type: ignore
except Exception:  # pragma: no cover - stub fallback
    from apps.straight_through._stubs.session_store import get_session, set_session

try:
    from apps.core.storage import ccp_file_importer, ccp_file_exporter  # type: ignore

    def _load_ccp(fp):
        return ccp_file_importer.load_ccp_file(fp)

    def _export_ccp(state):
        return ccp_file_exporter.export_ccp_file(state)

except Exception:  # pragma: no cover - stub fallback
    from apps.straight_through._stubs.storage import export_ccp_file as _export_ccp
    from apps.straight_through._stubs.storage import load_ccp_file as _load_ccp


LOG = logging.getLogger(__name__)


def _session_id(request: HttpRequest) -> str:
    """Return a stable key for the Redis session store."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or "anonymous"


def _collect_form_data(request: HttpRequest) -> dict[str, Any]:
    """Flatten POST data into the structure :mod:`services` expects."""
    data: dict[str, Any] = {}
    units: dict[str, dict[str, str]] = {"data_sheet_units": {}, "test_units": {}}
    for key, value in request.POST.items():
        if key.endswith("_unit_data_sheet"):
            units["data_sheet_units"][key.removesuffix("_unit_data_sheet")] = value
        elif key.endswith("_unit_test"):
            units["test_units"][key.removesuffix("_unit_test")] = value
        else:
            data[key] = value
    data.update(units)
    return data


def _sidebar_options(request: HttpRequest) -> dict[str, Any]:
    """Build a sidebar-options dict from the POSTed form or sensible defaults."""
    form = SidebarOptionsForm(request.POST or None)
    if not form.is_valid():
        form = SidebarOptionsForm()
        form.is_valid()
    return dict(form.cleaned_data)


def index(request: HttpRequest) -> HttpResponse:
    """Render the straight-through page from session state."""
    state = get_session(_session_id(request))
    context = {
        "state": state,
        "sidebar_form": SidebarOptionsForm(initial=state.get("sidebar", {})),
        "guarantee_form": GuaranteePointForm(initial=state.get("guarantee", {})),
        "curve_form": CurveUploadForm(),
        "test_point_indices": list(range(1, 7)),
        "curves": services.CURVES,
        "test_parameters": services.TEST_PARAMETERS,
        "result": state.get("last_result"),
    }
    return render(request, "straight_through/index.html", context)


@require_http_methods(["POST"])
def compute(request: HttpRequest) -> HttpResponse:
    """Run :func:`services.run_straight_through` and return the results partial."""
    form_data = _collect_form_data(request)
    options = _sidebar_options(request)
    options["calculate_speed"] = request.POST.get("action") == "calculate_speed"

    session_id = _session_id(request)
    state = get_session(session_id)
    state.update({"form_data": form_data, "sidebar": options})

    try:
        result = services.run_straight_through(form_data, options)
    except Exception as exc:
        LOG.exception("run_straight_through failed")
        context = {
            "error": str(exc),
            "traceback": traceback.format_exc() if request.POST.get("debug") else None,
        }
        return render(request, "straight_through/_results.html", context, status=400)

    state["last_result"] = {
        "speed_operational_rpm": result["speed_operational_rpm"],
        "results": result["results"],
    }
    set_session(session_id, state)

    context = {
        "result": result,
        "figures": result["figures"],
        "speed": result["speed_operational_rpm"],
        "curves": services.CURVES,
    }
    return render(request, "straight_through/_results.html", context)


@require_http_methods(["POST"])
def upload_curve(request: HttpRequest) -> HttpResponse:
    """Store an uploaded curve PNG on the session."""
    form = CurveUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)
    session_id = _session_id(request)
    state = get_session(session_id)
    curve = form.cleaned_data["curve"]
    state[f"fig_{curve}"] = form.cleaned_data["image"].read()
    state.setdefault("plot_limits", {})[curve] = {
        "x": {
            "lower_limit": form.cleaned_data.get("x_lower"),
            "upper_limit": form.cleaned_data.get("x_upper"),
            "units": form.cleaned_data.get("x_units"),
        },
        "y": {
            "lower_limit": form.cleaned_data.get("y_lower"),
            "upper_limit": form.cleaned_data.get("y_upper"),
            "units": form.cleaned_data.get("y_units"),
        },
    }
    set_session(session_id, state)
    return render(request, "straight_through/_curves.html", {"curve": curve})


def save_ccp(request: HttpRequest) -> HttpResponse:
    """Return the current session state as a ``.ccp`` archive download."""
    state = get_session(_session_id(request))
    blob = _export_ccp(state)
    response = HttpResponse(blob, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="session.ccp"'
    return response


@csrf_exempt
@require_http_methods(["POST"])
def load_ccp(request: HttpRequest) -> HttpResponse:
    """Hydrate the session from an uploaded ``.ccp`` archive."""
    uploaded = request.FILES.get("file")
    if not uploaded:
        return HttpResponse("missing file", status=400)
    state = _load_ccp(uploaded)
    set_session(_session_id(request), state)
    return HttpResponseRedirect(reverse("straight_through:index"))
