"""Django views for the curves conversion page.

Mirrors the UX of ``ccp/app/pages/3_curves_conversion.py``: a single page with
HTMX-driven "Load Original Curves" and "Convert Curves" actions, CSV uploads,
and ``.ccp`` save / load endpoints. All session state lives in the Redis-
backed store provided by ``apps.core.session_store`` (stubbed locally until
Unit 3 lands).
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.curves_conversion.forms import (
    ConversionParamsForm,
    ConvertedSuctionForm,
    CurvesCSVUploadForm,
    OriginalSuctionForm,
)
from apps.curves_conversion.services import CurveFile, run_conversion

try:
    from apps.core import session_store
except ImportError:  # pragma: no cover
    from apps.curves_conversion._stubs import session_store  # type: ignore

try:
    from apps.core.storage.ccp_file_importer import load_ccp_file
    from apps.core.storage.ccp_file_exporter import export_ccp_file
except ImportError:  # pragma: no cover
    from apps.curves_conversion._stubs.ccp_file_importer import load_ccp_file
    from apps.curves_conversion._stubs.ccp_file_exporter import export_ccp_file

logger = logging.getLogger(__name__)

SESSION_KEY = "curves_conversion"


def _session_id(request: HttpRequest) -> str:
    """Return a stable session identifier, creating one if necessary."""
    if not request.session.session_key:
        request.session.save()
    return f"{SESSION_KEY}:{request.session.session_key}"


def _get_state(request: HttpRequest) -> dict[str, Any]:
    return session_store.get_session(_session_id(request))


def _set_state(request: HttpRequest, state: dict[str, Any]) -> None:
    session_store.set_session(_session_id(request), state)


def page(request: HttpRequest) -> HttpResponse:
    """Render the curves conversion landing page."""
    state = _get_state(request)
    context = {
        "original_form": OriginalSuctionForm(),
        "converted_form": ConvertedSuctionForm(),
        "params_form": ConversionParamsForm(),
        "upload_form": CurvesCSVUploadForm(),
        "has_original": bool(state.get("original_impeller")),
        "has_converted": bool(state.get("converted_impeller")),
        "convert_url": reverse("curves_conversion:convert"),
        "upload_url": reverse("curves_conversion:upload_csv"),
        "save_url": reverse("curves_conversion:save_ccp"),
        "load_url": reverse("curves_conversion:load_ccp"),
    }
    return render(request, "curves_conversion/page.html", context)


@require_http_methods(["POST"])
def upload_csv(request: HttpRequest) -> HttpResponse:
    """Persist uploaded Engauge CSV files to the session store."""
    form = CurvesCSVUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    state = _get_state(request)
    for field in ("curves_file_1", "curves_file_2"):
        uploaded = form.cleaned_data.get(field)
        if uploaded is not None:
            state[field] = {"name": uploaded.name, "content": uploaded.read()}
    _set_state(request, state)
    return JsonResponse(
        {"ok": True, "stored": sorted(k for k in state if k.startswith("curves_file_"))}
    )


def _collect_curve_files(state: dict[str, Any]) -> list[CurveFile]:
    return [
        CurveFile(name=entry["name"], content=entry["content"])
        for index in (1, 2)
        if (entry := state.get(f"curves_file_{index}"))
    ]


@require_http_methods(["POST"])
def convert(request: HttpRequest) -> HttpResponse:
    """Run the full conversion pipeline and return a plots partial."""
    original_form = OriginalSuctionForm(request.POST, prefix="original")
    converted_form = ConvertedSuctionForm(request.POST, prefix="converted")
    params_form = ConversionParamsForm(request.POST, prefix="params")

    if not (
        original_form.is_valid()
        and converted_form.is_valid()
        and params_form.is_valid()
    ):
        return render(
            request,
            "curves_conversion/_errors.html",
            {
                "original_errors": original_form.errors,
                "converted_errors": converted_form.errors,
                "params_errors": params_form.errors,
            },
            status=400,
        )

    state = _get_state(request)
    curve_files = _collect_curve_files(state)
    if not curve_files:
        return render(
            request,
            "curves_conversion/_errors.html",
            {
                "global_error": "Nenhum arquivo CSV carregado. Envie as curvas antes de converter."
            },
            status=400,
        )

    try:
        result = run_conversion(
            original_data={
                "pressure": original_form.cleaned_data["pressure"],
                "pressure_unit": original_form.cleaned_data["pressure_unit"],
                "temperature": original_form.cleaned_data["temperature"],
                "temperature_unit": original_form.cleaned_data["temperature_unit"],
                "gas_composition": state.get(
                    "original_gas_composition", {"methane": 1.0}
                ),
            },
            converted_data={
                "pressure": converted_form.cleaned_data["pressure"],
                "pressure_unit": converted_form.cleaned_data["pressure_unit"],
                "temperature": converted_form.cleaned_data["temperature"],
                "temperature_unit": converted_form.cleaned_data["temperature_unit"],
                "gas_composition": state.get(
                    "converted_gas_composition", {"methane": 1.0}
                ),
            },
            curves_files=curve_files,
            conversion_params=params_form.cleaned_data,
        )
    except Exception as exc:
        logger.exception("curves conversion failed")
        return render(
            request,
            "curves_conversion/_errors.html",
            {"global_error": f"Erro durante a conversão: {exc}"},
            status=500,
        )

    state["original_impeller"] = result["original_impeller"]
    state["converted_impeller"] = result["converted_impeller"]
    _set_state(request, state)

    return render(
        request,
        "curves_conversion/_plots.html",
        {
            "original_figures": result["original_figures"],
            "converted_figures": result["converted_figures"],
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def load_ccp(request: HttpRequest) -> HttpResponse:
    """Load a ``.ccp`` archive into the session state."""
    uploaded = request.FILES.get("ccp_file")
    if uploaded is None:
        return JsonResponse({"ok": False, "error": "Arquivo .ccp ausente."}, status=400)
    try:
        state = load_ccp_file(uploaded)
    except Exception as exc:
        logger.exception("failed to load .ccp file")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    existing = _get_state(request)
    existing.update(state)
    _set_state(request, existing)
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def save_ccp(request: HttpRequest) -> HttpResponse:
    """Download the current session state as a ``.ccp`` archive."""
    state = _get_state(request)
    payload = export_ccp_file(state)
    response = HttpResponse(payload, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="curves_conversion.ccp"'
    return response


@require_http_methods(["GET"])
def download_csv(request: HttpRequest, case: str) -> HttpResponse:
    """Re-download an originally uploaded CSV from the session store."""
    state = _get_state(request)
    entry = state.get(f"curves_file_{case}")
    if entry is None:
        return JsonResponse({"ok": False, "error": "CSV não encontrado."}, status=404)
    response = HttpResponse(entry["content"], content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{entry["name"]}"'
    return response
