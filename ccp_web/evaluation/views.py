"""Performance evaluation page: plant data against the converted design curves.

The buttons' job starts (``start_run``, ``start_report``, ``start_monitoring``)
are plain functions shared with the agent adapter (``agent.py``), so a run
started by an agent is validated exactly as one started from the page. Secrets
are arguments: the views pass what the user typed or remembered, the agent
never passes any.
"""

import json
import threading
from collections import OrderedDict

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from ccp_web.core import jobs, secrets
from ccp_web.core.models import Case, Job
from ccp_web.core.state import base_revision, save_post
from ccp_web.core.views import get_case, refresh_response, workspace_context
from ccp_web.curves.views import design_context
from ccp_web.services import evaluation as ev
from ccp_web.services import plant_data, schemas, units

from .jobs import ANALYSIS_KEY, REPORT_KEY, TABLE_KEY

APP_TYPES = (Case.PERFORMANCE_EVALUATION,)
TABLE_ROWS = 200
FIELDS_MESSAGE = "Check the highlighted fields."
NO_EVALUATION = "Run a performance evaluation first to enable online monitoring."

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


def ensure_analysis(case):
    """Start building the plots of an imported evaluation; the job or None.

    An evaluation imported from a .ccp file has no plots yet. They are built
    by a job (``Evaluation.load`` takes seconds), once: not while a run is
    active and not again after the build failed.
    """
    if (
        case.artifact("evaluation") is not None
        and case.artifact(ANALYSIS_KEY) is None
        and not jobs.active_jobs(case, ["analysis", "evaluation"]).exists()
        and not Job.objects.filter(
            case=case, kind="analysis", status=Job.FAILED
        ).exists()
    ):
        return jobs.start_job(case, "analysis")
    return None


@require_GET
def case_view(request, pk):
    case = get_case(request, pk, APP_TYPES)
    ensure_analysis(case)
    return render(request, "evaluation/page.html", page_context(request, case))


def _error_job(case, kind, errors, message=FIELDS_MESSAGE):
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


def source_errors(case):
    """Field errors of the data source (file uploaded, PI usable and tagged)."""
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


def run_errors(case):
    """Field errors that keep the evaluation from running (none: ``{}``)."""
    errors = {}
    if not any(case.artifact(f"impeller_case_{c}") for c in schemas.CASES):
        errors["suc_p_case_A"] = (
            "No design cases loaded. Load curves for at least one case."
        )
    errors.update(source_errors(case))
    try:
        with units.state_context(case.state):
            ev.operation_fluid(case.state)
            ev.orifice_geometry(case.state)
    except units.InputError as exc:
        errors.update(exc.errors)
    return errors


def start_run(case, mode="run", pi_password=""):
    """Validate and start the evaluation job (the page's Run button).

    ``mode`` is ``"run"`` (append new data to the saved evaluation) or
    ``"full_rebuild"``. Raises ``units.InputError`` with the field errors;
    a running evaluation or plot build is cancelled first.
    """
    errors = run_errors(case)
    if errors:
        raise units.InputError(errors)
    jobs.active_jobs(case, ["evaluation", "analysis"]).update(cancel_requested=True)
    return jobs.start_job(
        case,
        "evaluation",
        {"mode": mode},
        secrets={"pi_password": pi_password} if pi_password else None,
    )


@require_POST
def run(request, pk):
    case = get_case(request, pk, APP_TYPES)
    if save_post(case, request.POST, base_revision(request)).stale:
        return refresh_response()
    mode = "full_rebuild" if request.POST.get("mode") == "full_rebuild" else "run"
    try:
        job = start_run(case, mode, _pi_password(request))
    except units.InputError as exc:
        job = _error_job(case, "evaluation", exc.errors)
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
    from ccp_web.core.state import merge_state

    # A view setting, not an input: keep ``Case.updated``, which tells the
    # agent whether the inputs changed after the evaluation. The page loads
    # this panel on every view.
    if (
        case.state.get("eval_cluster_idx") != cluster
        or bool(case.state.get("eval_show_similarity")) != similarity
    ):
        merge_state(
            case,
            {"eval_cluster_idx": cluster, "eval_show_similarity": similarity},
            touch=False,
        )
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


def start_report(case, ai_api_key=""):
    """Start the HTML report job; the AI analysis needs ``ai_api_key``.

    Without a key the report is built without the AI analysis, whatever
    ``ai_enabled`` says.
    """
    return jobs.start_job(
        case,
        "report",
        secrets={"ai_api_key": ai_api_key} if ai_api_key else None,
    )


@require_POST
def report(request, pk):
    case = get_case(request, pk, APP_TYPES)
    if save_post(case, request.POST, base_revision(request)).stale:
        return refresh_response()
    api_key = request.POST.get("ai_api_key_input") or secrets.remembered("ai_api_key")
    job = start_report(case, api_key)
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


def stop_monitoring(case):
    for job in jobs.active_jobs(case, ["monitoring"]):
        jobs.cancel_job(job)


def start_monitoring(case, pi_password=""):
    """Restart online monitoring (the page's Start button).

    The running monitoring job is stopped first, even when the new one cannot
    start. Raises ``units.InputError``: without field errors (``errors ==
    {}``) when there is no evaluation to monitor against.
    """
    stop_monitoring(case)
    if case.artifact("evaluation") is None:
        raise units.InputError({}, NO_EVALUATION)
    errors = source_errors(case)
    if errors:
        raise units.InputError(errors)
    return jobs.start_job(
        case,
        "monitoring",
        secrets={"pi_password": pi_password} if pi_password else None,
    )


@require_POST
def monitoring_start(request, pk):
    case = get_case(request, pk, APP_TYPES)
    if save_post(case, request.POST, base_revision(request)).stale:
        return refresh_response()
    try:
        monitor = start_monitoring(case, _pi_password(request))
    except units.InputError as exc:
        monitor = _error_job(
            case,
            "monitoring",
            exc.errors,
            FIELDS_MESSAGE if exc.errors else str(exc),
        )
    return render(
        request,
        "evaluation/partials/monitoring.html",
        {"case": case, "monitor": monitor, "state": case.state},
    )


@require_POST
def monitoring_stop(request, pk):
    case = get_case(request, pk, APP_TYPES)
    stop_monitoring(case)
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
