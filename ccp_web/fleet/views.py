"""Fleet analysis page: pick the performance-evaluation cases of the units of
one design (and the straight-through case of each shop test), fit the
hierarchical Bayesian fleet model in the background and compare the units:
as-built deviation, current health, degradation, events and instrument
biases."""

import json
import threading
from collections import OrderedDict

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from ccp_web.core import jobs
from ccp_web.core.models import Artifact, Case, Job
from ccp_web.core.state import save_post, update_state
from ccp_web.core.views import get_case, workspace_context
from ccp_web.services import fleet as fl

from .jobs import FLEET_KEY, RESULTS_KEY

APP_TYPES = (Case.FLEET_ANALYSIS,)
MIN_ROWS = 2

_cache = OrderedDict()
_cache_lock = threading.Lock()


def load_results(case):
    artifact = case.artifact(RESULTS_KEY)
    if artifact is None:
        return None
    with _cache_lock:
        if artifact.sha256 in _cache:
            _cache.move_to_end(artifact.sha256)
            return _cache[artifact.sha256]
    data = json.loads(artifact.read())
    with _cache_lock:
        _cache[artifact.sha256] = data
        while len(_cache) > 4:
            _cache.popitem(last=False)
    return data


def _cases(user, app_type, artifact_key):
    """{pk: (name, has the artifact)} and select options of the user's cases."""
    cases = (
        Case.objects.for_user(user)
        .filter(app_type=app_type)
        .select_related("project")
        .order_by("project__name", "name")
    )
    done = set(
        Artifact.objects.for_user(user)
        .filter(key=artifact_key, case__app_type=app_type)
        .values_list("case_id", flat=True)
    )
    info = {c.pk: (c.name, c.pk in done) for c in cases}
    options = [
        {"pk": c.pk, "label": f"{c.project.name} / {c.name}", "ready": c.pk in done}
        for c in cases
    ]
    return info, options


def choices(user):
    evaluations, evaluation_options = _cases(
        user, Case.PERFORMANCE_EVALUATION, "evaluation"
    )
    shops, shop_options = _cases(user, Case.STRAIGHT_THROUGH, Case.STRAIGHT_THROUGH)
    return evaluations, evaluation_options, shops, shop_options


def members_context(request, case, errors=None):
    evaluations, evaluation_options, shops, shop_options = choices(request.user)
    members = fl.members(case.state)
    while len(members) < MIN_ROWS:
        members.append({"evaluation": None, "name": "", "site": "", "shop": None})
    rows = []
    for i, m in enumerate(members):
        evaluation = evaluations.get(m["evaluation"])
        shop = shops.get(m["shop"])
        rows.append(
            {
                **m,
                "i": i,
                "default_name": evaluation[0] if evaluation else "Unit name",
                "missing": m["evaluation"] is not None and evaluation is None,
                "not_run": evaluation is not None and not evaluation[1],
                "shop_not_run": shop is not None and not shop[1],
            }
        )
    return {
        "case": case,
        "members": rows,
        "evaluation_options": evaluation_options,
        "shop_options": shop_options,
        "member_errors": (errors or {}).get("fleet_members"),
        "n_units": sum(1 for m in rows if m["evaluation"] is not None),
    }


def results_context(case):
    data = load_results(case)
    if data is None:
        return {"data": None}
    return {
        "data": data,
        "unit_rows": fl.unit_rows(data),
        "scatter_rows": fl.scatter_rows(data),
        "event_rows": fl.event_rows(data),
        "ranking": fl.ranking_rows(data),
        "diag": fl.diagnostics(data),
        "figures": data.get("figures") or {},
        "forest_height": 160 + 34 * len(data.get("units") or []),
    }


def _latest(case):
    return Job.objects.filter(case=case, kind="fleet").order_by("-created").first()


def page_context(request, case, errors=None):
    ctx = workspace_context(request, case)
    job = _latest(case)
    if errors is None and job and job.status == Job.FAILED:
        errors = job.result.get("errors")
    ctx.update(members_context(request, case, errors))
    ctx.update(results_context(case))
    available = fl.available()
    has_results = ctx["data"] is not None
    ctx.update(
        {
            "page": case.app_type,
            "app_type": case.app_type,
            "state": case.state,
            "errors": errors or {},
            "job": job,
            "available": available,
            "install_hint": fl.INSTALL_HINT,
            "has_results": has_results,
            "fleet_artifact": case.artifact(FLEET_KEY),
            "recent_jobs": Job.objects.filter(case=case).order_by("-created")[:6],
        }
    )
    n = ctx["n_units"]
    steps = [
        ("members", "Units", f"{n} selected", n >= 2),
        ("settings", "Model", f"{case.state.get('fleet_chains')} chains", n >= 2),
        ("run", "Fit", job.get_status_display().lower() if job else "", has_results),
        ("results", "Results", "health · ranking", has_results),
    ]
    current = next((i for i, s in enumerate(steps) if not s[3]), len(steps) - 1)
    ctx["steps"] = [
        {
            "n": i + 1,
            "anchor": a,
            "label": label,
            "hint": hint,
            "done": done,
            "current": i == current,
        }
        for i, (a, label, hint, done) in enumerate(steps)
    ]
    return ctx


@require_GET
def case_view(request, pk):
    case = get_case(request, pk, APP_TYPES)
    return render(request, "fleet/page.html", page_context(request, case))


def _apply_members(case, data):
    """Store the members of the editor form; ``action`` adds or removes a row."""
    members = fl.members_from_post(data)
    action = data.get("action") or ""
    if action == "add":
        members.append({"evaluation": None, "name": "", "site": "", "shop": None})
    elif action.startswith("remove:"):
        try:
            members.pop(int(action.split(":", 1)[1]))
        except (ValueError, IndexError):
            pass
    update_state(case, fleet_members=members)


@require_POST
def members(request, pk):
    case = get_case(request, pk, APP_TYPES)
    _apply_members(case, request.POST)
    if request.POST.get("quiet"):
        response = render(request, "core/partials/saved.html", {"case": case})
    else:
        response = render(
            request, "fleet/partials/members.html", members_context(request, case)
        )
    response["HX-Trigger"] = "ccp:saved"
    return response


def _error_job(case, errors, message="Check the highlighted fields."):
    return Job(
        owner=case.owner,
        case=case,
        kind="fleet",
        status=Job.FAILED,
        error=message,
        result={"errors": errors},
    )


@require_POST
def run(request, pk):
    case = get_case(request, pk, APP_TYPES)
    save_post(case, request.POST)
    if "member_evaluation" in request.POST:
        _apply_members(case, request.POST)
    evaluations, _, shops, _ = choices(request.user)
    errors = fl.validate(case.state, evaluations, shops)
    if errors:
        job = _error_job(case, errors)
    else:
        jobs.active_jobs(case, ["fleet"]).update(cancel_requested=True)
        job = jobs.start_job(case, "fleet")
    return render(request, "core/partials/job.html", {"job": job, "case": case})


@require_GET
def results(request, pk):
    case = get_case(request, pk, APP_TYPES)
    ctx = {"case": case, "state": case.state, **results_context(case)}
    ctx["fleet_artifact"] = case.artifact(FLEET_KEY)
    if ctx["data"] is None:
        return HttpResponse("")
    return render(request, "fleet/partials/results.html", ctx)
