"""Views for the back-to-back compressor page."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.back_to_back.forms import (
    CurveUploadForm,
    FirstSectionTestPointFormSet,
    GasCompositionForm,
    GuaranteePointForm,
    SecondSectionTestPointFormSet,
    SidebarOptionsForm,
)
from apps.back_to_back import services

try:  # pragma: no cover - Unit 3 replaces at merge time
    from apps.core.session_store import get_session, set_session
except Exception:  # noqa: BLE001
    _memory: dict[str, dict] = {}

    def get_session(session_id: str) -> dict:  # type: ignore[no-redef]
        return _memory.get(session_id, {})

    def set_session(session_id: str, state: dict) -> None:  # type: ignore[no-redef]
        _memory[session_id] = dict(state)


try:
    from apps.core.storage.ccp_file_importer import load_ccp_file
except Exception:  # noqa: BLE001

    def load_ccp_file(fp):  # type: ignore[no-redef]
        return {}


try:
    from apps.core.storage.ccp_file_exporter import export_ccp_file
except Exception:  # noqa: BLE001

    def export_ccp_file(state):  # type: ignore[no-redef]
        return b""


SESSION_KEY_PREFIX = "back_to_back:"


def _session_id(request: HttpRequest) -> str:
    """Return a stable session identifier.

    Uses Django's session framework when available (Unit 1 wires it up); when
    the app runs in isolation the session middleware may be disabled, in
    which case we fall back to a per-request anonymous key.
    """
    session = getattr(request, "session", None)
    if session is None:
        return f"{SESSION_KEY_PREFIX}anonymous"
    if not session.session_key:
        try:
            session.save()
        except Exception:  # noqa: BLE001
            return f"{SESSION_KEY_PREFIX}anonymous"
    return f"{SESSION_KEY_PREFIX}{session.session_key}"


def _context(request: HttpRequest, **extra) -> dict:
    """Build the default template context, merging *extra*."""
    ctx = {
        "sidebar_form": SidebarOptionsForm(),
        "gas_form": GasCompositionForm(),
        "guarantee_section_1_form": GuaranteePointForm(
            initial={"section": "section_1"}
        ),
        "guarantee_section_2_form": GuaranteePointForm(
            initial={"section": "section_2"}
        ),
        "first_section_formset": FirstSectionTestPointFormSet(prefix="sec1"),
        "second_section_formset": SecondSectionTestPointFormSet(prefix="sec2"),
        "curve_form": CurveUploadForm(),
        "saved_state": get_session(_session_id(request)),
    }
    ctx.update(extra)
    return ctx


def index(request: HttpRequest) -> HttpResponse:
    """Render the main back-to-back configuration page."""
    return render(request, "back_to_back/index.html", _context(request))


def _split_values_units(form_cleaned: dict) -> tuple[dict, dict]:
    values: dict = {}
    units: dict = {}
    for key, value in form_cleaned.items():
        if key.endswith("_value"):
            values[key[: -len("_value")]] = value
        elif key.endswith("_units"):
            units[key[: -len("_units")]] = value
    return values, units


def _point_payload(form_cleaned: dict) -> dict:
    """Transform a single form's cleaned data into a services payload entry."""
    values, units = _split_values_units(form_cleaned)
    return {"values": values, "units": units, "fluid": {"methane": 1.0}}


def _build_section_payload(formset_cleaned_list) -> list[dict]:
    return [_point_payload(cd) for cd in formset_cleaned_list if cd]


@require_http_methods(["POST"])
def compute(request: HttpRequest) -> HttpResponse:
    """Run the compressor computation and return the results partial."""
    sidebar = SidebarOptionsForm(request.POST)
    guarantee_sec1 = GuaranteePointForm(request.POST, prefix="guarantee_sec1")
    guarantee_sec2 = GuaranteePointForm(request.POST, prefix="guarantee_sec2")
    first_formset = FirstSectionTestPointFormSet(request.POST, prefix="sec1")
    second_formset = SecondSectionTestPointFormSet(request.POST, prefix="sec2")

    if not (
        sidebar.is_valid()
        and guarantee_sec1.is_valid()
        and guarantee_sec2.is_valid()
        and first_formset.is_valid()
        and second_formset.is_valid()
    ):
        return render(
            request,
            "back_to_back/_results.html",
            {
                "error": "Please correct the highlighted fields.",
                "sidebar_errors": sidebar.errors,
            },
            status=400,
        )

    payload = {
        "options": sidebar.cleaned_data,
        "guarantee": {
            "section_1": _point_payload(guarantee_sec1.cleaned_data),
            "section_2": _point_payload(guarantee_sec2.cleaned_data),
        },
        "test_points_first": _build_section_payload(
            [f.cleaned_data for f in first_formset]
        ),
        "test_points_second": _build_section_payload(
            [f.cleaned_data for f in second_formset]
        ),
        "calculate_speed": request.POST.get("action") == "calculate_speed",
    }

    try:
        context = services.run_back_to_back(payload)
    except Exception as exc:  # noqa: BLE001
        return render(
            request,
            "back_to_back/_results.html",
            {"error": f"Compute failed: {exc}"},
            status=500,
        )

    set_session(
        _session_id(request),
        {
            "speed_operational_rpm": context["speed_operational_rpm"],
            "results_sec1": context["results_sec1"],
            "results_sec2": context["results_sec2"],
        },
    )
    return render(request, "back_to_back/_results.html", context)


@require_http_methods(["POST"])
def upload_curve(request: HttpRequest) -> HttpResponse:
    """Store an uploaded curve PNG in the session state."""
    form = CurveUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    state = get_session(_session_id(request))
    key = f"fig_{form.cleaned_data['curve']}_{form.cleaned_data['section']}"
    image = form.cleaned_data.get("image")
    if image is not None:
        state[key] = image.read()
    state.setdefault("plot_limits", {}).setdefault(
        form.cleaned_data["curve"], {}
    )[form.cleaned_data["section"]] = {
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
    set_session(_session_id(request), state)
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def save_ccp(request: HttpRequest) -> HttpResponse:
    """Download the current session as a ``.ccp`` archive."""
    state = get_session(_session_id(request))
    payload = export_ccp_file(state)
    response = HttpResponse(payload, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="back_to_back.ccp"'
    return response


@require_http_methods(["POST"])
def load_ccp(request: HttpRequest) -> HttpResponse:
    """Load a ``.ccp`` archive into the session."""
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"ok": False, "error": "no file"}, status=400)
    state = load_ccp_file(uploaded)
    set_session(_session_id(request), state)
    return render(request, "back_to_back/index.html", _context(request))
