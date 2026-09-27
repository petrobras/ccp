"""Performance evaluation page: plant data against the converted design curves."""

import json
import threading
from collections import OrderedDict

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from ccp_web.core import jobs, secrets
from ccp_web.core.models import Case, Job
from ccp_web.core.state import save_post
from ccp_web.core.views import get_case, workspace_context
from ccp_web.curves.views import design_context
from ccp_web.services import evaluation as ev
from ccp_web.services import plant_data, schemas, units

from .jobs import ANALYSIS_KEY, REPORT_KEY, TABLE_KEY

APP_TYPES = (Case.PERFORMANCE_EVALUATION,)
TABLE_ROWS = 200

_cache = OrderedDict()
_cache_lock = threading.Lock()


def load_analysis(case):
    artifact = case.artifact(ANALYSIS_KEY)
    if artifact is None:
        return None
    with _cache_lock:
        if artifact.sha256 in _cache:
            _cache.move_to_end(artifact.sha256)
            return _cache[artifact.sha256]
    analysis = json.loads(artifact.read())
    with _cache_lock:
        _cache[artifact.sha256] = analysis
        while len(_cache) > 4:
            _cache.popitem(last=False)
    return analysis


def _latest(case, kind):
    return Job.objects.filter(case=case, kind=kind).order_by("-created").first()


def tag_rows():
    rows = [(p, label, list(opts)) for p, label, opts in schemas.TAG_PARAMETERS]
    return rows


def page_context(request, case, errors=None):
    state = case.state
    ctx = workspace_context(request, case)
    ctx.update(design_context(case))
    eval_job = _latest(case, "evaluation")
    analysis_job = _latest(case, "analysis")
    last_job = max(
        [j for j in (eval_job, analysis_job) if j is not None],
        key=lambda j: j.created,
        default=None,
    )
    if errors is None and last_job and last_job.status == Job.FAILED:
        errors = last_job.result.get("errors")
    has_evaluation = case.artifact("evaluation") is not None
    has_analysis = case.artifact(ANALYSIS_KEY) is not None
    loaded = [r for r in ctx["design_cases"] if r["info"]]
    start, end = ev.evaluation_window(state)
    monitor = _latest(case, "monitoring")
    source = state.get("data_source") or "pi"
    ctx.update(
        {
            "page": case.app_type,
            "app_type": case.app_type,
            "state": state,
            "errors": errors or {},
            "job": last_job,
            "has_evaluation": has_evaluation,
            "has_analysis": has_analysis,
            "report": case.artifact(REPORT_KEY),
            "report_job": _latest(case, "report"),
            "monitor": monitor,
            "tag_rows": tag_rows(),
            "flow_rows": list(schemas.FLOW_TAG_PARAMETERS),
            "orifice_rows": list(schemas.ORIFICE_TAG_PARAMETERS),
            "fluid_rows": list(range(schemas.N_FLUID_TAGS)),
            "fluid_list": ctx["gas_init"]["fluids"],
            "data_sources": schemas.DATA_SOURCES,
            "source": source,
            "has_pandaspi": plant_data.has_pandaspi(),
            "plant_file": case.file("plant_data"),
            "window_start": start.strftime("%Y-%m-%dT%H:%M"),
            "window_end": end.strftime("%Y-%m-%dT%H:%M"),
            "keyring": secrets.keyring_available(),
            "pi_password_saved": bool(secrets.remembered("pi_password")),
            "ai_key_saved": bool(secrets.remembered("ai_api_key")),
            "recent_jobs": Job.objects.filter(case=case).order_by("-created")[:6],
            "loaded_letters": [r["letter"] for r in loaded],
        }
    )
    steps = [
        (
            "gas",
            "Gas",
            "compositions",
            any(True for _ in loaded) or bool(state.get("gas_compositions_table")),
        ),
        ("design", "Design curves", f"{len(loaded)} loaded", bool(loaded)),
        (
            "tags",
            "Data source",
            dict(schemas.DATA_SOURCES).get(source, source),
            source != "pi" or bool(state.get("suc_p_tag")),
        ),
        ("run", "Run", "evaluation", has_evaluation),
        ("results", "Report", "trends · export", ctx["report"] is not None),
    ]
    current = next((i for i, s in enumerate(steps) if not s[3]), len(steps) - 1)
    ctx["steps"] = [
        {
            "anchor": a,
            "label": lb,
            "hint": h,
            "done": d,
            "n": i + 1,
            "current": i == current,
        }
        for i, (a, lb, h, d) in enumerate(steps)
    ]
    return ctx


@require_GET
def case_view(request, pk):
    case = get_case(request, pk, APP_TYPES)
    # An evaluation imported from a .ccp file has no plots yet: build them.
    if (
        case.artifact("evaluation") is not None
        and case.artifact(ANALYSIS_KEY) is None
        and not jobs.active_jobs(case, ["analysis", "evaluation"]).exists()
        and not Job.objects.filter(
            case=case, kind="analysis", status=Job.FAILED
        ).exists()
    ):
        jobs.start_job(case, "analysis")
    return render(request, "evaluation/page.html", page_context(request, case))


def _error_job(case, kind, errors, message="Check the highlighted fields."):
    return Job(
        owner=case.owner,
        case=case,
        kind=kind,
        status=Job.FAILED,
        error=message,
        result={"errors": errors},
    )


def _pi_password(request):
    return request.POST.get("pi_password_input") or secrets.remembered("pi_password")


def _validate_source(case):
    state = case.state
    source = state.get("data_source") or "pi"
    errors = {}
    if source == "file" and case.file("plant_data") is None:
        errors["plant_data"] = "Upload a plant data file (CSV or Parquet)."
    if source == "pi":
        if not plant_data.has_pandaspi():
            errors["data_source"] = (
                "The PI source needs pandaspi (Petrobras network). Use File or Mock."
            )
        tm = plant_data.tag_mappings(state)
        if not plant_data.build_pi_query(tm)[0]:
            errors["suc_p_tag"] = "No PI tags configured. Please fill in the tag names."
    return errors


@require_POST
def run(request, pk):
    case = get_case(request, pk, APP_TYPES)
    save_post(case, request.POST)
    mode = "full_rebuild" if request.POST.get("mode") == "full_rebuild" else "run"
    errors = {}
    if not any(case.artifact(f"impeller_case_{c}") for c in schemas.CASES):
        errors["suc_p_case_A"] = (
            "No design cases loaded. Load curves for at least one case."
        )
    errors.update(_validate_source(case))
    try:
        with units.state_context(case.state):
            ev.operation_fluid(case.state)
            ev.orifice_geometry(case.state)
    except units.InputError as exc:
        errors.update(exc.errors)
    if errors:
        job = _error_job(case, "evaluation", errors)
    else:
        jobs.active_jobs(case, ["evaluation", "analysis"]).update(cancel_requested=True)
        job = jobs.start_job(
            case,
            "evaluation",
            {"mode": mode},
            secrets={"pi_password": _pi_password(request)},
        )
    return render(request, "core/partials/job.html", {"job": job, "case": case})


@require_GET
def results(request, pk):
    case = get_case(request, pk, APP_TYPES)
    analysis = load_analysis(case)
    ctx = page_context(request, case)
    ctx["analysis"] = analysis
    if analysis:
        table_artifact = case.artifact(TABLE_KEY)
        if table_artifact is not None:
            df = ev.table_from_parquet(table_artifact.read())
            ctx["table_columns"] = list(df.columns)
            ctx["table_rows"] = [
                (str(idx), [None if v != v else v for v in row])
                for idx, row in zip(
                    df.index[:TABLE_ROWS], df.head(TABLE_ROWS).itertuples(index=False)
                )
            ]
            ctx["table_total"] = len(df)
        summary = ev.summary_frame(analysis)
        if summary is not None:
            ctx["summary_columns"] = list(summary.columns)
            ctx["summary_rows"] = [
                (idx, list(row))
                for idx, row in zip(summary.index, summary.itertuples(index=False))
            ]
        ctx["clusters"] = list(range(analysis.get("n_clusters", 0)))
    return render(request, "evaluation/partials/results.html", ctx)


@require_GET
def perf(request, pk):
    """Performance plots of one converted curve (cluster), optional similarity."""
    case = get_case(request, pk, APP_TYPES)
    analysis = load_analysis(case)
    if analysis is None:
        raise Http404()
    cluster = int(request.GET.get("cluster", case.state.get("eval_cluster_idx") or 0))
    similarity = request.GET.get("similarity", "0") in ("1", "true", "on")
    from ccp_web.core.state import update_state

    update_state(case, eval_cluster_idx=cluster, eval_show_similarity=similarity)
    figs = analysis.get("perf", {}).get(f"{cluster}:{int(similarity)}")
    return render(
        request,
        "evaluation/partials/perf.html",
        {
            "case": case,
            "figs": figs,
            "cluster": cluster,
            "similarity": similarity,
            "clusters": list(range(analysis.get("n_clusters", 0))),
        },
    )


@require_GET
def table_excel(request, pk):
    case = get_case(request, pk, APP_TYPES)
    artifact = case.artifact(TABLE_KEY)
    if artifact is None:
        raise Http404()
    response = HttpResponse(
        ev.table_to_excel(ev.table_from_parquet(artifact.read())),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="evaluation_results.xlsx"'
    return response


@require_POST
def report(request, pk):
    case = get_case(request, pk, APP_TYPES)
    save_post(case, request.POST)
    api_key = request.POST.get("ai_api_key_input") or secrets.remembered("ai_api_key")
    job = jobs.start_job(case, "report", secrets={"ai_api_key": api_key})
    return render(
        request,
        "evaluation/partials/report.html",
        {"case": case, "report_job": job, "report": case.artifact(REPORT_KEY)},
    )


@require_GET
def report_status(request, pk):
    case = get_case(request, pk, APP_TYPES)
    return render(
        request,
        "evaluation/partials/report.html",
        {
            "case": case,
            "report_job": _latest(case, "report"),
            "report": case.artifact(REPORT_KEY),
        },
    )


@require_POST
def monitoring_start(request, pk):
    case = get_case(request, pk, APP_TYPES)
    save_post(case, request.POST)
    for job in jobs.active_jobs(case, ["monitoring"]):
        jobs.cancel_job(job)
    if case.artifact("evaluation") is None:
        monitor = _error_job(
            case,
            "monitoring",
            {},
            "Run a performance evaluation first to enable online monitoring.",
        )
    else:
        errors = _validate_source(case)
        if errors:
            monitor = _error_job(case, "monitoring", errors)
        else:
            monitor = jobs.start_job(
                case, "monitoring", secrets={"pi_password": _pi_password(request)}
            )
    return render(
        request,
        "evaluation/partials/monitoring.html",
        {"case": case, "monitor": monitor, "state": case.state},
    )


@require_POST
def monitoring_stop(request, pk):
    case = get_case(request, pk, APP_TYPES)
    for job in jobs.active_jobs(case, ["monitoring"]):
        jobs.cancel_job(job)
    return render(
        request,
        "evaluation/partials/monitoring.html",
        {"case": case, "monitor": _latest(case, "monitoring"), "state": case.state},
    )


@require_GET
def monitoring_panel(request, pk):
    case = get_case(request, pk, APP_TYPES)
    return render(
        request,
        "evaluation/partials/monitoring.html",
        {"case": case, "monitor": _latest(case, "monitoring"), "state": case.state},
    )


@require_POST
def remember_secret(request, pk, name):
    case = get_case(request, pk, APP_TYPES)
    if name not in secrets.NAMES:
        raise Http404()
    value = request.POST.get(f"{name}_input", "")
    if secrets.remember(name, value):
        messages.success(
            request,
            "Saved in the system keyring."
            if value
            else "Removed from the system keyring.",
        )
    else:
        messages.error(
            request,
            "No system keyring is available; the value is used for this run only.",
        )
    return redirect(case.get_absolute_url() + "#sec-tags")
