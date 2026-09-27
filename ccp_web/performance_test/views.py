"""Straight-through and back-to-back pages."""

import threading
from collections import OrderedDict

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from ccp_web.core import jobs
from ccp_web.core.models import Case, Job
from ccp_web.core.state import gas_matrix, save_post, update_state
from ccp_web.core.views import get_case, workspace_context
from ccp_web.services import gas, schemas, units
from ccp_web.services import performance_test as pt

APP_TYPES = (Case.STRAIGHT_THROUGH, Case.BACK_TO_BACK)
TITLES = {
    Case.STRAIGHT_THROUGH: "Straight-through",
    Case.BACK_TO_BACK: "Back-to-back",
}
DESCRIPTIONS = {
    Case.STRAIGHT_THROUGH: (
        "Performance test of a straight-through compressor per ASME PTC 10: "
        "test points "
        "converted to the guarantee conditions, similarity checks and "
        "performance curves."
    ),
    Case.BACK_TO_BACK: (
        "Performance test of a back-to-back compressor per ASME PTC 10, with "
        "division wall "
        "and end seal leakage between the two sections."
    ),
}
CURVE_LABELS = {
    "head": "Head",
    "eff": "Efficiency",
    "discharge_pressure": "Discharge Pressure",
    "power": "Gas Power",
}


# --------------------------------------------------------------------------
# Compressor cache (TOML artifact -> object), per process
# --------------------------------------------------------------------------

_cache = OrderedDict()
_cache_lock = threading.Lock()
CACHE_SIZE = 8


def load_compressor(case):
    artifact = case.artifact(case.app_type)
    if artifact is None:
        return None, None
    key = (case.app_type, artifact.sha256)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key], artifact
    with units.state_context(case.state):
        compressor = pt.load_compressor(case.app_type, artifact.read_text())
    with _cache_lock:
        _cache[key] = compressor
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return compressor, artifact


# --------------------------------------------------------------------------
# Layout for the templates
# --------------------------------------------------------------------------


def _toggle(app_type, param):
    """Alpine expression that disables a test-data row (Streamlit behaviour)."""
    if app_type == Case.STRAIGHT_THROUGH:
        return "!opt.seal" if param in schemas.SEAL_GAS_PARAMETERS else ""
    if param in schemas.SEAL_GAS_PARAMETERS:
        return "!opt.seal || !opt.leak"
    if param in schemas.LEAKAGE_PARAMETERS:
        return "!opt.leak"
    return ""


def layout(app_type):
    secs = pt.sections(app_type)
    P = schemas.PARAMETERS
    data_sheet = [
        {
            "param": P[p],
            "unit_key": secs[0].ds_unit(p),
            "keys": [sec.ds_value(p) for sec in secs],
        }
        for p in schemas.DATA_SHEET_PARAMETERS
    ]
    test = []
    curves = []
    for sec in secs:
        rows = [
            {
                "param": P[p],
                "unit_key": sec.tp_unit(p),
                "keys": [sec.tp_value(p, i) for i in range(1, schemas.N_POINTS + 1)],
                "toggle": _toggle(app_type, p),
            }
            for p in sec.test_parameters
        ]
        orifice = [
            {
                "param": P[p],
                "unit_key": None if p == "tappings_fo" else sec.fo_unit(p),
                "keys": [sec.fo_value(p, i) for i in range(1, schemas.N_POINTS + 1)],
                "select": p == "tappings_fo",
            }
            for p in schemas.ORIFICE_PARAMETERS
        ]
        test.append(
            {
                "id": sec.sec or "st",
                "title": sec.title if sec.name else "Test points",
                "gas_keys": [sec.tp_gas(i) for i in range(1, schemas.N_POINTS + 1)],
                "flow": rows[0],
                "rows": rows[1:],
                "orifice": orifice,
                "method_key": sec.flow_method,
            }
        )
        curves.append(
            {
                "id": sec.sec or "st",
                "title": sec.title if sec.name else "Curves",
                "rows": [
                    {
                        "curve": c,
                        "label": CURVE_LABELS[c],
                        "image_key": f"fig_{sec.curve_prefix(c)}",
                        "prefix": sec.curve_prefix(c),
                        "y_units": P[c].units,
                    }
                    for c in schemas.CURVES
                ],
            }
        )
    return {
        "sections": secs,
        "flow_m_units": units.flow_m_units,
        "section_titles": [s.title for s in secs],
        "data_sheet": data_sheet,
        "test": test,
        "curves": curves,
        "points": list(range(1, schemas.N_POINTS + 1)),
    }


def _filled_points(state, app_type):
    n = 0
    for sec in pt.sections(app_type):
        for i in range(1, schemas.N_POINTS + 1):
            if str(state.get(sec.tp_value("flow", i), "")).strip():
                n += 1
    return n


def steps(case, state, has_results, job):
    names = gas.gas_names(state)
    gases_ok = any(gas.composition(state, n) for n in names)
    secs = pt.sections(case.app_type)
    ds_ok = all(
        str(state.get(sec.ds_value(p), "")).strip()
        for sec in secs
        for p in [
            "flow",
            "suction_pressure",
            "suction_temperature",
            "discharge_pressure",
            "speed",
        ]
    )
    n_points = _filled_points(state, case.app_type)
    items = [
        (
            "gas",
            "Gas",
            f"{sum(1 for n in names if gas.composition(state, n))} defined",
            gases_ok,
        ),
        ("datasheet", "Data sheet", "guarantee point", ds_ok),
        (
            "test",
            "Test data",
            f"{n_points} point{'s' if n_points != 1 else ''}",
            n_points > 0,
        ),
        ("run", "Calculate", "PTC 10", has_results),
        ("results", "Results", "tables · curves", has_results),
    ]
    current = next(
        (i for i, (*_, done) in enumerate(items) if not done), len(items) - 1
    )
    return [
        {
            "anchor": a,
            "label": label,
            "hint": hint,
            "done": done,
            "current": i == current,
            "n": i + 1,
        }
        for i, (a, label, hint, done) in enumerate(items)
    ]


def page_context(request, case, errors=None):
    state = case.state
    last_job = (
        Job.objects.filter(case=case, kind="calculate").order_by("-created").first()
    )
    has_results = case.artifact(case.app_type) is not None
    if errors is None and last_job and last_job.status == Job.FAILED:
        errors = last_job.result.get("errors")
    files = {f.key: f for f in case.files.all()}
    ctx = workspace_context(request, case)
    ctx.update(
        {
            "page": case.app_type,
            "app_type": case.app_type,
            "title": TITLES[case.app_type],
            "description": DESCRIPTIONS[case.app_type],
            "state": state,
            "errors": errors or {},
            "layout": layout(case.app_type),
            "gas_init": {
                "names": gas.gas_names(state),
                "rows": gas_matrix(state),
                "fluids": gas.fluid_list(),
            },
            "files": files,
            "job": last_job,
            "has_results": has_results,
            "steps": steps(case, state, has_results, last_job),
            "options": schemas.OPTIONS,
            "polytropic_methods": list(units.polytropic_methods),
            "recent_jobs": Job.objects.filter(case=case).order_by("-created")[:6],
            "is_b2b": case.app_type == Case.BACK_TO_BACK,
        }
    )
    return ctx


# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------


@require_GET
def case_view(request, pk):
    case = get_case(request, pk, APP_TYPES)
    return render(request, "performance_test/page.html", page_context(request, case))


def _save_post(case, request):
    """Save the form; return the sections whose flow method changed."""
    old = dict(case.state)
    save_post(case, request.POST)
    updates = pt.switch_flow_method(case.app_type, old, case.state)
    if updates:
        update_state(case, **updates)
    return {
        s.name
        for s in pt.sections(case.app_type)
        if old.get(s.flow_method) != case.state.get(s.flow_method)
    }


@require_POST
def calculate(request, pk):
    """Save the form, validate, and start the calculation job."""
    case = get_case(request, pk, APP_TYPES)
    _save_post(case, request)
    try:
        errors = _store_orifice_flows(case, strict=True)
        try:
            with units.state_context(case.state):
                pt.read_inputs(case.app_type, case.state)
        except units.InputError as exc:
            errors = {**exc.errors, **errors}
        if errors:
            raise units.InputError(errors)
    except units.InputError as exc:
        fake = Job(
            owner=case.owner,
            case=case,
            kind="calculate",
            status=Job.FAILED,
            error="Check the highlighted fields.",
            result={"errors": exc.errors},
        )
        return render(request, "core/partials/job.html", {"job": fake, "case": case})
    jobs.active_jobs(case, ["calculate"]).update(cancel_requested=True)
    job = jobs.start_job(
        case,
        "calculate",
        {"calculate_speed": request.POST.get("calculate_speed") == "1"},
    )
    return render(request, "core/partials/job.html", {"job": job, "case": case})


def _store_orifice_flows(case, strict):
    """Calculate the orifice-mode test flows and store them; return the errors."""
    with units.state_context(case.state):
        updates, errors = pt.orifice_flows(case.app_type, case.state, strict=strict)
    if updates:
        update_state(case, **updates)
    return errors


@require_POST
def test_data(request, pk):
    """Autosave of the test data; refreshes the calculated orifice flows.

    Returns the save status plus, out of band, the Flow row of every section
    in orifice mode or whose flow method just changed.
    """
    case = get_case(request, pk, APP_TYPES)
    switched = _save_post(case, request)
    errors = _store_orifice_flows(case, strict=False)
    ctx = page_context(request, case, errors=errors)
    names = switched | {s.name for s in pt.orifice_sections(case.app_type, case.state)}
    ctx["flow_rows"] = [
        t
        for t, sec in zip(ctx["layout"]["test"], ctx["layout"]["sections"])
        if sec.name in names
    ]
    response = render(request, "performance_test/partials/test_data_saved.html", ctx)
    response["HX-Trigger"] = "ccp:saved"
    return response


def _figure_payload(case, compressor, sec, files):
    with units.state_context(case.state):
        pi = pt.interpolated_point(compressor, sec)
        figs, limits = pt.figures(
            case.app_type, compressor, case.state, sec, point_interpolated=pi
        )
    for curve in schemas.CURVES:
        image = files.get(f"fig_{sec.curve_prefix(curve)}")
        if image is not None:
            url = reverse("core:case_file", args=[case.pk, image.key])
            pt.add_background_image(figs[curve], limits[curve], url)
    return figs


@require_GET
def results(request, pk):
    case = get_case(request, pk, APP_TYPES)
    compressor, artifact = load_compressor(case)
    if compressor is None:
        return render(
            request,
            "performance_test/partials/results.html",
            {"case": case, "empty": True},
        )
    files = {f.key: f for f in case.files.all()}
    with units.state_context(case.state):
        tables = pt.results(case.app_type, compressor, case.state)
    sections = []
    for sec, table in zip(pt.sections(case.app_type), tables):
        checks = {(c["row"], c["column"]): c["ok"] for c in table["checks"]}
        rows = []
        for r in table["rows"]:
            cells = []
            for col, value in zip(table["columns"], r["values"]):
                fmt = (
                    "percent"
                    if col in pt.PERCENT_COLUMNS
                    else "scientific"
                    if col in pt.SCIENTIFIC_COLUMNS
                    else ""
                )
                ok = checks.get((r["label"], col))
                cells.append({"value": value, "fmt": fmt, "ok": ok})
            rows.append({"label": r["label"], "cells": cells})
        sections.append(
            {
                "id": sec.sec or "st",
                "title": table["title"],
                "columns": table["columns"],
                "rows": rows,
                "checks": table["checks"],
                "figures": _figure_payload(case, compressor, sec, files),
            }
        )
    ctx = {
        "case": case,
        "sections": sections,
        "speed_rpm": compressor.speed_operational.to("rpm").m,
        "artifact": artifact,
        "all_ok": all(c["ok"] for s in sections for c in s["checks"]),
    }
    return render(request, "performance_test/partials/results.html", ctx)


@require_GET
def excel(request, pk, sec):
    case = get_case(request, pk, APP_TYPES)
    compressor, _ = load_compressor(case)
    if compressor is None:
        raise Http404()
    with units.state_context(case.state):
        tables = pt.results(case.app_type, compressor, case.state)
    table = next(
        (
            t
            for t in tables
            if t["key"] == sec or (sec == "st" and t["key"] == "results")
        ),
        None,
    )
    if table is None:
        raise Http404()
    name = "results.xlsx" if case.app_type == Case.STRAIGHT_THROUGH else f"{sec}.xlsx"
    response = HttpResponse(
        pt.table_to_excel(table),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response
