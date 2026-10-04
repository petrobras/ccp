"""Curves conversion page (and the design-case sections shared with the
performance evaluation page)."""

import threading
from collections import OrderedDict

from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ccp_web.core import jobs
from ccp_web.core.models import Case, Job
from ccp_web.core.state import gas_matrix, save_post
from ccp_web.core.views import get_case, workspace_context
from ccp_web.services import curves, gas, schemas, units

DESIGN_APP_TYPES = (Case.CURVES_CONVERSION, Case.PERFORMANCE_EVALUATION)

_cache = OrderedDict()
_cache_lock = threading.Lock()
CACHE_SIZE = 16


def load_impeller(case, key):
    """Impeller from the ``key`` TOML artifact, cached per process."""
    artifact = case.artifact(key)
    if artifact is None:
        return None
    cache_key = artifact.sha256
    with _cache_lock:
        if cache_key in _cache:
            _cache.move_to_end(cache_key)
            return _cache[cache_key]
    with units.state_context(case.state):
        impeller = curves.load_impeller(artifact.read_text())
    with _cache_lock:
        _cache[cache_key] = impeller
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return impeller


def design_cases(case):
    """Per design case: keys, files, loaded impeller info, last load job."""
    files = {f.key: f for f in case.files.all()}
    artifacts = {a.key: a for a in case.artifacts.all()}
    last_jobs = {}
    for job in Job.objects.filter(case=case, kind="load_curves").order_by("-created")[
        :20
    ]:
        last_jobs.setdefault(job.params.get("case"), job)
    rows = []
    for letter in schemas.CASES:
        info = None
        if f"impeller_case_{letter}" in artifacts:
            imp = load_impeller(case, f"impeller_case_{letter}")
            info = curves.impeller_info(imp) if imp is not None else None
        rows.append(
            {
                "letter": letter,
                "gas_key": f"gas_case_{letter}",
                "p_key": f"suc_p_case_{letter}",
                "T_key": f"suc_T_case_{letter}",
                "slots": [
                    {
                        "key": f"curves_file_{n}_case_{letter}",
                        "file": files.get(f"curves_file_{n}_case_{letter}"),
                    }
                    for n in (1, 2)
                ],
                "info": info,
                "job": last_jobs.get(letter),
                "curve_name": case.state.get(f"curve_name_case_{letter}"),
            }
        )
    return rows


LOADED_UNITS = [
    ("loaded_curves_speed_units", "Speed"),
    ("loaded_curves_flow_units", "Flow"),
    ("loaded_curves_head_units", "Head"),
    ("loaded_curves_power_units", "Power"),
    ("loaded_curves_disch_p_units", "Disch. pres."),
    ("loaded_curves_disch_T_units", "Disch. temp."),
]
PLOT_UNITS = [
    ("plot_curves_speed_units", "Speed"),
    ("plot_curves_flow_units", "Flow"),
    ("plot_curves_disch_p_units", "Disch. pres."),
    ("plot_curves_disch_T_units", "Disch. temp."),
    ("plot_curves_head_units", "Head"),
    ("plot_curves_power_units", "Power"),
]


def design_context(case):
    state = case.state
    return {
        "design_cases": design_cases(case),
        "loaded_units": LOADED_UNITS,
        "gas_init": {
            "names": gas.gas_names(state),
            "rows": gas_matrix(state),
            "fluids": gas.fluid_list(),
        },
    }


def page_context(request, case, errors=None):
    ctx = workspace_context(request, case)
    last_convert = (
        Job.objects.filter(case=case, kind="convert_curves")
        .order_by("-created")
        .first()
    )
    if errors is None and last_convert and last_convert.status == Job.FAILED:
        errors = last_convert.result.get("errors")
    has_converted = case.artifact("converted_impeller") is not None
    ctx.update(design_context(case))
    loaded = [r for r in ctx["design_cases"] if r["info"]]
    ctx.update(
        {
            "page": case.app_type,
            "app_type": case.app_type,
            "state": case.state,
            "errors": errors or {},
            "job": last_convert,
            "has_converted": has_converted,
            "plot_units": PLOT_UNITS,
            "loaded_letters": [r["letter"] for r in loaded],
            "recent_jobs": Job.objects.filter(case=case).order_by("-created")[:6],
            "steps": [
                {
                    "anchor": "gas",
                    "label": "Gas",
                    "hint": "compositions",
                    "done": any(
                        gas.composition(case.state, n)
                        for n in gas.gas_names(case.state)
                    ),
                },
                {
                    "anchor": "design",
                    "label": "Design cases",
                    "hint": f"{len(loaded)} loaded",
                    "done": bool(loaded),
                },
                {
                    "anchor": "new",
                    "label": "New suction",
                    "hint": "target",
                    "done": float(case.state.get("new_suc_p") or 0) > 0,
                },
                {
                    "anchor": "run",
                    "label": "Convert",
                    "hint": case.state.get("conv_find_method"),
                    "done": has_converted,
                },
                {
                    "anchor": "results",
                    "label": "Results",
                    "hint": "plots",
                    "done": has_converted,
                },
            ],
        }
    )
    current = next(
        (i for i, s in enumerate(ctx["steps"]) if not s["done"]), len(ctx["steps"]) - 1
    )
    for i, s in enumerate(ctx["steps"]):
        s["n"] = i + 1
        s["current"] = i == current
    return ctx


@require_GET
def case_view(request, pk):
    case = get_case(request, pk, [Case.CURVES_CONVERSION])
    return render(request, "curves/page.html", page_context(request, case))


def _save_post(case, request):
    save_post(case, request.POST)


def _error_job(case, kind, errors, message="Check the highlighted fields."):
    return Job(
        owner=case.owner,
        case=case,
        kind=kind,
        status=Job.FAILED,
        error=message,
        result={"errors": errors},
    )


@require_POST
def load_case(request, pk, letter):
    """Start loading the Engauge curves of one design case."""
    case = get_case(request, pk, DESIGN_APP_TYPES)
    if letter not in schemas.CASES:
        raise Http404()
    _save_post(case, request)
    missing = [
        k
        for k in (f"curves_file_1_case_{letter}", f"curves_file_2_case_{letter}")
        if case.file(k) is None
    ]
    try:
        if missing:
            raise units.InputError(
                {
                    k: f"Please upload both curve files for Case {letter}"
                    for k in missing
                }
            )
        with units.state_context(case.state):
            curves.design_suction_state(case.state, letter)
    except units.InputError as exc:
        job = _error_job(case, "load_curves", exc.errors)
    else:
        job = jobs.start_job(case, "load_curves", {"case": letter})
    return render(request, "core/partials/job.html", {"job": job, "case": case})


@require_POST
def convert(request, pk):
    case = get_case(request, pk, [Case.CURVES_CONVERSION])
    _save_post(case, request)
    try:
        if not any(case.artifact(f"impeller_case_{c}") for c in schemas.CASES):
            raise units.InputError(
                {
                    "suc_p_case_A": (
                        "Please load at least one design case before converting."
                    )
                }
            )
        with units.state_context(case.state):
            curves.new_suction_state(case.state)
    except units.InputError as exc:
        job = _error_job(case, "convert_curves", exc.errors)
    else:
        jobs.active_jobs(case, ["convert_curves"]).update(cancel_requested=True)
        job = jobs.start_job(case, "convert_curves")
    return render(request, "core/partials/job.html", {"job": job, "case": case})


PANELS = {"converted": ("converted_impeller", "Converted")}
PANELS.update(
    {
        f"orig_case_{c}": (f"impeller_case_{c}", f"Design Case {c}")
        for c in schemas.CASES
    }
)


@require_http_methods(["GET", "POST"])
def plots(request, pk, prefix):
    """Plots and point summary of one impeller; POST updates its controls."""
    case = get_case(request, pk, [Case.CURVES_CONVERSION])
    if prefix not in PANELS:
        raise Http404()
    _save_post(case, request)
    key, label = PANELS[prefix]
    impeller = load_impeller(case, key)
    if impeller is None:
        return render(
            request,
            "curves/partials/plots.html",
            {"case": case, "prefix": prefix, "label": label, "missing": True},
        )
    error = None
    figs, summary = {}, None
    try:
        with units.state_context(case.state):
            figs, summary = curves.impeller_view(impeller, case.state, prefix)
            info = curves.impeller_info(impeller)
    except Exception as exc:  # e.g. a point outside the curves
        error = str(exc)
        info = curves.impeller_info(impeller)
    state = dict(case.state)
    if summary:
        # Show the flow and speed the plots were drawn at when none was typed.
        state.setdefault(f"{prefix}_flow_input", None)
        state.setdefault(f"{prefix}_speed_input", None)
        if state[f"{prefix}_flow_input"] in (None, ""):
            state[f"{prefix}_flow_input"] = round(summary["flow"], 4)
        if state[f"{prefix}_speed_input"] in (None, ""):
            state[f"{prefix}_speed_input"] = round(summary["speed"], 2)
    ctx = {
        "case": case,
        "state": state,
        "app_type": case.app_type,
        "prefix": prefix,
        "label": label,
        "figs": figs,
        "summary": summary,
        "info": info,
        "error": error,
        "flow_key": f"{prefix}_flow_input",
        "speed_key": f"{prefix}_speed_input",
        "sim_key": f"{prefix}_show_similarity",
    }
    return render(request, "curves/partials/plots.html", ctx)


@require_GET
def results(request, pk):
    case = get_case(request, pk, [Case.CURVES_CONVERSION])
    ctx = page_context(request, case)
    return render(request, "curves/partials/results.html", ctx)
