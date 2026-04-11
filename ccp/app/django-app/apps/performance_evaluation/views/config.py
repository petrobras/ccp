"""Config page + HTMX partial endpoints for the Performance Evaluation app.

This view owns the input side: design cases, PI configuration, tag
mappings, date range, AI options, and .ccp file loading. Computation,
monitoring, and results belong to Unit 9.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.decorators.http import require_http_methods

from .. import forms
from .._compat import load_ccp_file, session_store


@lru_cache(maxsize=1)
def _base_template() -> str:
    """Return Unit 1's base.html when available, else our local fallback."""
    try:
        get_template("base.html")
        return "base.html"
    except TemplateDoesNotExist:
        return "performance_evaluation/_base_fallback.html"


def _session_id(request) -> str:
    """Return a stable session id for the current Django session."""
    key = request.session.session_key
    if key:
        return key
    try:
        request.session.save()
    except Exception:
        pass
    return request.session.session_key or "anonymous"


def _load_state(request) -> dict:
    return session_store.get_session(_session_id(request))


def _save_state(request, state: dict) -> None:
    session_store.set_session(_session_id(request), state)


def _default_dates() -> tuple[datetime, datetime]:
    end = datetime.now().replace(microsecond=0)
    start = end - timedelta(days=30)
    return start, end


def _initial_design_cases(state: dict) -> list[dict]:
    return [
        {
            "case": case,
            "gas": state.get(f"gas_case_{case}", ""),
            "suc_p": state.get(f"suc_p_case_{case}", 0.0),
            "suc_p_unit": state.get("design_suc_p_unit", "bar"),
            "suc_T": state.get(f"suc_T_case_{case}", 0.0),
            "suc_T_unit": state.get("design_suc_T_unit", "degC"),
        }
        for case in forms.CASES
    ]


def _build_forms(state: dict, data=None):
    start, end = _default_dates()
    date_initial = {
        "start_date": state.get("eval_start_date", start.date()),
        "start_time": state.get("eval_start_time", start.time()),
        "end_date": state.get("eval_end_date", end.date()),
        "end_time": state.get("eval_end_time", end.time()),
    }
    return {
        "design_formset": forms.DesignCaseFormSet(
            data=data,
            prefix="design",
            initial=_initial_design_cases(state),
        ),
        "pi_form": forms.PIServerConfigForm(
            data=data,
            prefix="pi",
            initial={
                "pi_server_name": state.get("pi_server_name", ""),
                "pi_auth_method": state.get("pi_auth_method", "kerberos"),
                "pi_username": state.get("pi_username", ""),
            },
        ),
        "flow_form": forms.FlowMethodForm(
            data=data,
            prefix="flow",
            initial={
                "flow_method": state.get("flow_method", "Direct"),
                "orifice_tappings": state.get("orifice_tappings", "flange"),
                "orifice_D": state.get("orifice_D", 0.0),
                "orifice_d": state.get("orifice_d", 0.0),
            },
        ),
        "fluid_source_form": forms.FluidSourceForm(
            data=data,
            prefix="fluid",
            initial={
                "fluid_source": state.get("fluid_source", "Fixed Operation Fluid"),
                "operation_fluid_gas": state.get("operation_fluid_gas", ""),
            },
        ),
        "date_form": forms.DateRangeForm(
            data=data, prefix="date", initial=date_initial
        ),
        "ai_form": forms.AIOptionsForm(
            data=data,
            prefix="ai",
            initial={
                "ai_enabled": state.get("ai_enabled", False),
                "ai_provider": state.get("ai_provider", "gemini"),
                "ai_api_key": state.get("ai_api_key", ""),
                "ai_azure_endpoint": state.get("ai_azure_endpoint", ""),
                "ai_azure_deployment": state.get("ai_azure_deployment", ""),
            },
        ),
        "curves_units_form": forms.CurvesUnitsForm(
            data=data,
            prefix="curves",
            initial={
                "loaded_curves_speed_units": state.get(
                    "loaded_curves_speed_units", "rpm"
                ),
                "loaded_curves_flow_units": state.get(
                    "loaded_curves_flow_units", "m³/h"
                ),
                "loaded_curves_head_units": state.get(
                    "loaded_curves_head_units", "J/kg"
                ),
                "loaded_curves_power_units": state.get(
                    "loaded_curves_power_units", "kW"
                ),
            },
        ),
        "session_form": forms.SessionMetaForm(
            prefix="session",
            initial={"session_name": state.get("session_name", "")},
        ),
    }


def _tag_rows(state: dict, flow_method: str) -> list[dict]:
    rows = []
    for key, label, units in forms.tag_parameters_for(flow_method):
        rows.append(
            {
                "parameter": key,
                "label": label,
                "units": units,
                "tag_1": state.get(f"{key}_tag", ""),
                "tag_2": state.get(f"{key}_tag_2", ""),
                "unit_1": state.get(f"{key}_unit", units[0] if units else ""),
                "unit_2": state.get(f"{key}_unit_2", units[0] if units else ""),
            }
        )
    return rows


def _render_config(request, state: dict, forms_dict: dict, status: int = 200):
    flow_method = forms_dict["flow_form"]["flow_method"].value() or "Direct"
    context = {
        "forms": forms_dict,
        "cases": forms.CASES,
        "tag_rows": _tag_rows(state, flow_method),
        "flow_method": flow_method,
        "fluid_components": forms.default_fluid_components(),
        "state": state,
        "base_template": _base_template(),
    }
    return render(
        request,
        "performance_evaluation/config.html",
        context,
        status=status,
    )


@require_http_methods(["GET", "HEAD", "POST"])
def config_view(request):
    """Render the config page (GET) or persist submitted forms (POST)."""
    state = _load_state(request)

    if request.method in ("GET", "HEAD"):
        forms_dict = _build_forms(state)
        return _render_config(request, state, forms_dict)

    forms_dict = _build_forms(state, data=request.POST)
    all_valid = True
    for key in (
        "design_formset",
        "pi_form",
        "flow_form",
        "fluid_source_form",
        "date_form",
        "ai_form",
        "curves_units_form",
    ):
        form = forms_dict[key]
        if not form.is_valid():
            all_valid = False

    if not all_valid:
        return _render_config(request, state, forms_dict, status=400)

    # Persist cleaned data into the session_store state dict.
    for i, form in enumerate(forms_dict["design_formset"].forms):
        cd = form.cleaned_data
        case = cd.get("case") or forms.CASES[i]
        state[f"gas_case_{case}"] = cd.get("gas", "")
        state[f"suc_p_case_{case}"] = cd.get("suc_p") or 0.0
        state[f"suc_T_case_{case}"] = cd.get("suc_T") or 0.0
        state["design_suc_p_unit"] = cd.get("suc_p_unit", "bar")
        state["design_suc_T_unit"] = cd.get("suc_T_unit", "degC")

    state.update(forms_dict["pi_form"].cleaned_data)
    state.update(forms_dict["flow_form"].cleaned_data)
    state.update(forms_dict["fluid_source_form"].cleaned_data)
    state.update(forms_dict["curves_units_form"].cleaned_data)

    ai = forms_dict["ai_form"].cleaned_data
    state.update(ai)

    date_cd = forms_dict["date_form"].cleaned_data
    state["eval_start_date"] = date_cd.get("start_date")
    state["eval_start_time"] = date_cd.get("start_time")
    state["eval_end_date"] = date_cd.get("end_date")
    state["eval_end_time"] = date_cd.get("end_time")

    # Parse per-parameter tag mapping rows out of the POST body.
    flow_method = state.get("flow_method", "Direct")
    for key, _label, _units in forms.tag_parameters_for(flow_method):
        state[f"{key}_tag"] = request.POST.get(f"tag_{key}_tag_1", "")
        state[f"{key}_tag_2"] = request.POST.get(f"tag_{key}_tag_2", "")
        state[f"{key}_unit"] = request.POST.get(f"tag_{key}_unit_1", "")
        state[f"{key}_unit_2"] = request.POST.get(f"tag_{key}_unit_2", "")

    _save_state(request, state)

    forms_dict = _build_forms(state)
    return _render_config(request, state, forms_dict)


@require_http_methods(["POST"])
def upload_impeller(request, case: str):
    """Store an uploaded impeller TOML file in session state."""
    if case not in forms.CASES:
        return HttpResponseBadRequest("unknown case")
    state = _load_state(request)
    f = request.FILES.get("impeller")
    if f is None:
        return HttpResponseBadRequest("missing file")
    state[f"impeller_case_{case}"] = {"name": f.name, "size": f.size}
    _save_state(request, state)
    return JsonResponse({"case": case, "name": f.name})


@require_http_methods(["POST"])
def upload_curves(request, case: str):
    """Store uploaded Engauge curve CSV files in session state."""
    if case not in forms.CASES:
        return HttpResponseBadRequest("unknown case")
    state = _load_state(request)
    saved = []
    for idx in (1, 2):
        f = request.FILES.get(f"curves_file_{idx}")
        if f is not None:
            state[f"curves_file_{idx}_case_{case}"] = {
                "name": f.name,
                "content": f.read(),
            }
            saved.append(f.name)
    _save_state(request, state)
    return JsonResponse({"case": case, "saved": saved})


@require_http_methods(["POST"])
def tag_mapping_add(request):
    """HTMX endpoint: return an additional tag-mapping row partial."""
    parameter = request.POST.get("parameter", "custom")
    row = {
        "parameter": parameter,
        "label": parameter.replace("_", " ").title(),
        "units": [],
        "tag_1": "",
        "tag_2": "",
        "unit_1": "",
        "unit_2": "",
    }
    return render(
        request,
        "performance_evaluation/_tag_row.html",
        {"row": row},
    )


@require_http_methods(["POST", "DELETE"])
def tag_mapping_remove(request, parameter: str):
    """HTMX endpoint: drop a tag-mapping row from session state."""
    state = _load_state(request)
    for key in (
        f"{parameter}_tag",
        f"{parameter}_tag_2",
        f"{parameter}_unit",
        f"{parameter}_unit_2",
    ):
        state.pop(key, None)
    _save_state(request, state)
    return HttpResponse(status=200)


@require_http_methods(["POST"])
def flow_method_change(request):
    """HTMX endpoint: re-render the tag-mappings block when method changes."""
    flow_method = request.POST.get("flow_method", "Direct")
    state = _load_state(request)
    state["flow_method"] = flow_method
    _save_state(request, state)
    return render(
        request,
        "performance_evaluation/_tag_mappings.html",
        {
            "tag_rows": _tag_rows(state, flow_method),
            "flow_method": flow_method,
        },
    )


@require_http_methods(["POST"])
def load_ccp_view(request):
    """Load a .ccp session archive into session state."""
    f = request.FILES.get("ccp_file")
    if f is None:
        return HttpResponseBadRequest("missing file")
    try:
        loaded = load_ccp_file(f)
    except Exception as exc:
        return HttpResponseBadRequest(f"invalid .ccp file: {exc}")
    state = _load_state(request)
    state.update(loaded)
    state["session_name"] = f.name.replace(".ccp", "")
    _save_state(request, state)
    forms_dict = _build_forms(state)
    return _render_config(request, state, forms_dict)
