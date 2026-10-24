"""Agent HTTP API (``api/agent/v1/``): JSON in and out, bearer-token auth.

An AI coding agent reads what the user has open, edits the open case (every
write is an undoable ``AgentRevision``), starts the page's calculation and
posts notes. It authenticates with an ``AgentToken``
(``Authorization: Bearer ccpa_...`` or ``X-CCP-Token``), never with the
session: the desktop server logs every browser request in automatically, so
a session would let any local process act as the user. ``request.user`` is
replaced by the token owner and every query goes through ``for_user``.

Per-page work (calculate, results, figures) is delegated to the adapters in
``adapters.py``. Secrets (PI password, AI key) are never accepted, stored or
returned: they are not in the state, and job results are filtered.
"""

import difflib
import functools
import json
import logging
import re
import time

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

import ccp
from ccp_web.core import jobs
from ccp_web.core.models import Case, Job, Project
from ccp_web.core.state import ValuesError, apply_values
from ccp_web.core.views import (
    APP_TITLES,
    case_ccp_bytes,
    ccp_filename,
    create_from_ccp,
    default_project,
    duplicate_case,
    new_case,
)
from ccp_web.services import ccpfile, schemas, units

from . import adapters, revisions
from .models import AgentNote, AgentRevision, AgentToken
from .views import AGENT_JOB_TIMEOUT, agent_job_key, get_presence, navigate_key

log = logging.getLogger("ccp_web.agent")

API_VERSION = 1
# One long-poll holds one of the server's request threads (8 on the
# desktop), which the user's page shares: keep each wait short. Clients
# continue a longer wait on ``jobs/<id>``.
MAX_CALCULATE_WAIT = 60
MAX_JOB_WAIT = 60
# A monitoring job runs until it is stopped: waiting for it to finish would
# hold the request for the whole wait.
MONITORING_WAIT = 5
_TRUE = {"1", "true", "yes", "on"}
POLL_STEP = 0.5
PRESENCE_STALE_S = 120
# The browser polls every 2 s; a navigation nobody picks up should not move
# the page hours later.
NAVIGATE_TIMEOUT = 120
RECENT_CASES = 10
REVISIONS_LIMIT = 50
NOTES_LIMIT = 100
MAX_NOTE = 20_000
MAX_WRITE_NOTE = 2_000
_SECRET_KEY = re.compile(r"password|api_key|secret|token", re.I)
# Waits are module attributes so tests can drive the long-poll loop.
_sleep = time.sleep
_clock = time.monotonic

ENDPOINTS = [
    "GET  (root)",
    "GET  context",
    "POST context/open {case}",
    "GET  projects",
    "GET  cases ?project=&app_type=",
    "POST cases {app_type, name?, project?, state?} | multipart file=<.ccp>",
    "GET  cases/<id> ?keys=k1,k2",
    "POST cases/<id>/duplicate {name?}",
    "GET  cases/<id>/export",
    "GET  cases/<id>/state ?keys=k1,k2",
    "POST cases/<id>/state {values, note}",
    "POST cases/<id>/calculate {params?, wait?}",
    "GET  cases/<id>/results",
    "GET  cases/<id>/figures",
    "GET  cases/<id>/figures/<fig> ?format=data|plotly|png",
    "GET  cases/<id>/revisions",
    "POST cases/<id>/undo {revision_id?}",
    "GET  cases/<id>/notes",
    "POST cases/<id>/notes {body}",
    "GET  jobs/<id> ?wait=",
    "POST jobs/<id>/cancel",
    "GET  schema/<app_type> ?filter=",
]


class ApiError(Exception):
    """An error response: ``{"error": message, "details": details}``."""

    def __init__(self, status, message, details=None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def error_response(status, message, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    response = JsonResponse(body, status=status)
    if status == 401:
        response["WWW-Authenticate"] = 'Bearer realm="ccp-agent"'
    return response


def _token_from(request):
    header = request.headers.get("Authorization") or ""
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return (request.headers.get("X-CCP-Token") or "").strip() or None


def agent_endpoint(methods=("GET",), write=False):
    """Make a view an agent API endpoint.

    ``methods`` are the allowed HTTP methods; ``write`` is True (every method
    needs a write-scope token) or the subset of methods that do. The view
    runs as the token owner; errors become JSON (``ApiError``, ``ValuesError``
    and ``InputError`` with details, ``ValueError`` 400, missing rows 404, no
    adapter 501).
    """
    allowed = {m.upper() for m in methods}
    if write is True:
        writes = allowed
    elif write:
        writes = {m.upper() for m in write}
    else:
        writes = set()

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method not in allowed:
                response = error_response(
                    405, f"method {request.method} not allowed; use {sorted(allowed)}"
                )
                response["Allow"] = ", ".join(sorted(allowed))
                return response
            plaintext = _token_from(request)
            if plaintext is None:
                return error_response(
                    401,
                    "missing token: send 'Authorization: Bearer ccpa_...'",
                )
            token = AgentToken.authenticate(plaintext)
            if token is None:
                return error_response(401, "invalid or expired token")
            if request.method in writes and not token.can_write:
                return error_response(403, "this token is read-only")
            request.agent_token = token
            # Never the session user: the token decides who this is.
            request.user = token.owner
            try:
                return view(request, *args, **kwargs)
            except ApiError as exc:
                return error_response(exc.status, exc.message, exc.details)
            except ValuesError as exc:
                return error_response(400, str(exc), exc.details)
            except units.InputError as exc:
                return error_response(400, str(exc), {"errors": exc.errors})
            except adapters.AdapterMissing as exc:
                return error_response(501, str(exc))
            except (Http404, ObjectDoesNotExist) as exc:
                return error_response(404, str(exc) or "not found")
            except PermissionError as exc:
                if exc.errno is None:  # ours ("not your revision")
                    return error_response(403, str(exc))
                # A file the server cannot read: a server error, not the token.
                log.exception("Agent API error in %s", view.__name__)
                return error_response(500, f"{type(exc).__name__}: {exc}")
            except ValueError as exc:
                # Adapters raise ValueError for bad params, but one from deep
                # inside ccp or pandas is a data problem: keep its traceback.
                log.warning("Agent API 400 in %s", view.__name__, exc_info=True)
                return error_response(400, str(exc))
            except Exception as exc:
                log.exception("Agent API error in %s", view.__name__)
                return error_response(500, f"{type(exc).__name__}: {exc}")

        return login_not_required(csrf_exempt(wrapper))

    return decorator


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _body(request):
    """The JSON object sent with the request (``{}`` for an empty body)."""
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except ValueError as exc:
        raise ApiError(400, f"invalid JSON body: {exc}") from None
    if not isinstance(data, dict):
        raise ApiError(400, "the JSON body must be an object")
    return data


def _json(data, status=200):
    """A JSON response; lists are allowed and NaN/inf become null."""
    return JsonResponse(adapters.json_safe(data), status=status, safe=False)


def _iso(value):
    return value.isoformat() if value else None


def _int(value, name):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ApiError(400, f"{name} must be an integer, got {value!r}") from None


def _seconds(value, limit, name="wait"):
    if value in (None, ""):
        return 0.0
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        raise ApiError(400, f"{name} must be a number of seconds") from None
    return max(0.0, min(float(limit), seconds))


def _cases(request):
    return Case.objects.for_user(request.user).select_related("project")


def _case(request, pk):
    return get_object_or_404(_cases(request), pk=pk)


def case_summary(request, case):
    return {
        "id": case.pk,
        "name": case.name,
        "app_type": case.app_type,
        "app_title": APP_TITLES.get(case.app_type, case.app_type),
        "project": {"id": case.project_id, "name": case.project.name},
        "revision": case.revision,
        "updated": _iso(case.updated),
        "url": request.build_absolute_uri(case.get_absolute_url()),
    }


def _without_secrets(value):
    """``value`` without keys that look like secrets, recursively."""
    if isinstance(value, dict):
        return {
            k: _without_secrets(v)
            for k, v in value.items()
            if not _SECRET_KEY.search(str(k))
        }
    if isinstance(value, list):
        return [_without_secrets(v) for v in value]
    return value


def _compact_result(job):
    """``job.result`` for the agent: a monitoring view lists its figure ids.

    The monitoring view holds four full plotly figures (~60 KB); the agent
    reads them with ``figures/monitoring_<name>`` (``results`` lists them).
    """
    result = job.result or {}
    view = result.get("view")
    if job.kind == "monitoring" and isinstance(view, dict):
        figures = view.get("figures")
        if isinstance(figures, dict):
            view = {**view, "figures": [f"monitoring_{name}" for name in figures]}
            result = {**result, "view": view}
    return result


def job_dict(job):
    return {
        "id": job.pk,
        "case": job.case_id,
        "kind": job.kind,
        "status": job.status,
        "active": job.is_active,
        "progress": job.progress,
        "message": job.message,
        "error": job.error,
        "warnings": list(job.warnings or []),
        "params": _without_secrets(job.params or {}),
        "result": adapters.json_safe(_without_secrets(_compact_result(job))),
        "created": _iso(job.created),
        "started": _iso(job.started),
        "finished": _iso(job.finished),
    }


def _wait_for(job, seconds):
    """Re-read ``job`` every ``POLL_STEP`` until it is done or time is up."""
    deadline = _clock() + seconds
    while job.is_active and _clock() < deadline:
        _sleep(max(0.0, min(POLL_STEP, deadline - _clock())))
        job.refresh_from_db()
    return job


def _wanted(keys):
    return [k.strip() for k in (keys or "").split(",") if k.strip()]


def _units_keys(app_type, keys):
    """``{key: units key}`` of the requested keys that have one."""
    fields = schemas.get_schema(app_type).fields
    return {
        k: fields[k].units_key
        for k in _wanted(keys)
        if k in fields and fields[k].units_key
    }


def _public_state(state, keys=None):
    state = _without_secrets(state or {})
    if keys:
        wanted = _wanted(keys)
        missing = [k for k in wanted if k not in state]
        if missing:
            schema_keys = list(state)
            raise ApiError(
                400,
                "unknown key(s): " + ", ".join(missing),
                {
                    "unknown": {
                        k: difflib.get_close_matches(k, schema_keys, n=5, cutoff=0.6)
                        for k in missing
                    }
                },
            )
        state = {k: state[k] for k in wanted}
    return state


def _units_out(case, keys):
    """``{"units_keys": ...}`` when ``keys`` asks for values that have units."""
    found = _units_keys(case.app_type, keys) if keys else {}
    return {"units_keys": found} if found else {}


def _project(request, value):
    if value in (None, ""):
        presence = get_presence(request.user) or {}
        if presence.get("case"):
            case = _cases(request).filter(pk=presence["case"]).first()
            if case is not None:
                return case.project
        return default_project(request.user)
    pk = _int(value, "project")
    return get_object_or_404(Project.objects.for_user(request.user), pk=pk)


# --------------------------------------------------------------------------
# Root, context, projects
# --------------------------------------------------------------------------


@agent_endpoint()
def root(request):
    token = request.agent_token
    return _json(
        {
            "api": "ccp-agent",
            "version": API_VERSION,
            "ccp_version": ccp.__version__,
            "profile": settings.CCP_PROFILE,
            "user": request.user.get_username(),
            "token": {"name": token.name, "scope": token.scope, "kind": token.kind},
            "app_types": {
                app_type: {"title": title, "adapter": adapters.has_adapter(app_type)}
                for app_type, title in Case.APP_TYPES
            },
            "endpoints": ENDPOINTS,
        }
    )


@agent_endpoint()
def context(request):
    """What the user has open (from the page's presence reports)."""
    presence = get_presence(request.user) or {}
    case = None
    if presence.get("case"):
        case = _cases(request).filter(pk=presence["case"]).first()
    seen = presence.get("seen")
    age = round(time.time() - seen, 1) if seen else None
    recent = _cases(request).order_by("-updated")[:RECENT_CASES]
    return _json(
        {
            "presence": {
                "case": case_summary(request, case) if case else None,
                "page": presence.get("page") or None,
                "section": presence.get("section") or None,
                "url": presence.get("url") or None,
                "title": presence.get("title") or None,
                "seen": seen,
                "age_s": age,
                "stale": age is None or age > PRESENCE_STALE_S,
            },
            "recent_cases": [case_summary(request, c) for c in recent],
        }
    )


@agent_endpoint(methods=("POST",), write=True)
def context_open(request):
    """Make the user's browser open a case (picked up by the page's poll)."""
    data = _body(request)
    if "case" not in data:
        raise ApiError(400, "send {case: <id>}")
    case = _case(request, _int(data["case"], "case"))
    cache.set(navigate_key(request.user), case.get_absolute_url(), NAVIGATE_TIMEOUT)
    return _json(
        {
            "ok": True,
            "url": request.build_absolute_uri(case.get_absolute_url()),
            "case": case_summary(request, case),
        }
    )


@agent_endpoint()
def projects(request):
    rows = (
        Project.objects.for_user(request.user)
        .annotate(n_cases=Count("cases"))
        .order_by("name")
    )
    return _json(
        [
            {
                "id": p.pk,
                "name": p.name,
                "description": p.description,
                "cases": p.n_cases,
                "created": _iso(p.created),
                "updated": _iso(p.updated),
            }
            for p in rows
        ]
    )


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------


@agent_endpoint(methods=("GET", "POST"), write=("POST",))
def cases(request):
    if request.method == "POST":
        return _case_create(request)
    rows = _cases(request).order_by("-updated")
    project = request.GET.get("project")
    if project:
        rows = rows.filter(project_id=_int(project, "project"))
    app_type = request.GET.get("app_type")
    if app_type:
        rows = rows.filter(app_type=app_type)
    return _json([case_summary(request, c) for c in rows])


def _case_create(request):
    upload = request.FILES.get("file")
    if upload is not None:
        project = _project(request, request.POST.get("project"))
        name = (request.POST.get("name") or "").strip() or (
            re.sub(r"\.ccp$", "", upload.name, flags=re.I) or "Imported"
        )
        expected = request.POST.get("app_type") or None
        try:
            parsed = ccpfile.read_ccp(upload.read(), expected_app_type=expected)
        except ccpfile.CcpFileError as exc:
            raise ApiError(400, str(exc)) from None
        # Where a remembered secret is sent stays the user's choice, in a
        # file as in ``state``: those keys go back to their defaults.
        default = schemas.default_state(parsed.app_type)
        reset = sorted(
            k
            for k in revisions.AGENT_READONLY_KEYS
            if k in parsed.state and parsed.state[k] != default.get(k)
        )
        for k in reset:
            parsed.state[k] = default.get(k)
        case = create_from_ccp(project, name, parsed)
        body = case_summary(request, case)
        if reset:
            body["warnings"] = [
                f"{k} reset to its default: " + revisions.READONLY_MESSAGE.format(key=k)
                for k in reset
            ]
        return _json(body, status=201)
    data = _body(request)
    app_type = data.get("app_type")
    if app_type not in APP_TITLES:
        raise ApiError(
            400, f"app_type must be one of {list(APP_TITLES)}", {"app_type": app_type}
        )
    project = _project(request, data.get("project"))
    name = str(data.get("name") or "").strip()[:200] or None
    state = None
    if data.get("state"):
        default = schemas.default_state(app_type)
        state, _ = apply_values(app_type, default, data["state"])
        revisions.check_readonly(default, state)
    case = new_case(project, app_type, name=name, state=state)
    return _json(case_summary(request, case), status=201)


@agent_endpoint()
def case_detail(request, pk):
    case = _case(request, pk)
    latest = {}
    for job in Job.objects.filter(case=case).order_by("-created"):
        latest.setdefault(job.kind, job)
    return _json(
        {
            "case": case_summary(request, case),
            "state": _public_state(case.state, request.GET.get("keys")),
            **_units_out(case, request.GET.get("keys")),
            "files": [
                {"key": f.key, "name": f.name, "kind": f.kind} for f in case.files.all()
            ],
            "artifacts": [
                {"key": a.key, "name": a.name, "created": _iso(a.created)}
                for a in case.artifacts.all()
            ],
            "jobs": [job_dict(j) for j in latest.values()],
            "results_available": adapters.has_results(case),
        }
    )


@agent_endpoint(methods=("POST",), write=True)
def case_duplicate(request, pk):
    case = _case(request, pk)
    name = str(_body(request).get("name") or "").strip()[:200] or None
    copy = duplicate_case(case, name=name)
    return _json(case_summary(request, copy), status=201)


@agent_endpoint()
def case_export(request, pk):
    case = _case(request, pk)
    response = HttpResponse(
        case_ccp_bytes(case), content_type="application/octet-stream"
    )
    response["Content-Disposition"] = f'attachment; filename="{ccp_filename(case)}"'
    return response


@agent_endpoint(methods=("GET", "POST", "PATCH"), write=("POST", "PATCH"))
def case_state(request, pk):
    """Read the state, or write values as one undoable revision."""
    case = _case(request, pk)
    if request.method == "GET":
        return _json(
            {
                "revision": case.revision,
                "state": _public_state(case.state, request.GET.get("keys")),
                **_units_out(case, request.GET.get("keys")),
            }
        )
    data = _body(request)
    if "values" not in data:
        raise ApiError(400, 'send {"values": {key: value}, "note": "why"}')
    note = str(data.get("note") or "").strip()
    if len(note) > MAX_WRITE_NOTE:
        raise ApiError(400, f"note is longer than {MAX_WRITE_NOTE} characters")
    warnings = []
    revision = revisions.record_agent_write(
        case,
        data["values"],
        note=note,
        token=request.agent_token,
        warnings=warnings,
    )
    # The case written, so an agent that resolved it from presence can tell
    # when the user switched cases between its calls.
    written = {"id": case.pk, "name": case.name}
    if revision is None:
        return _json(
            {
                "case": written,
                "revision": case.revision,
                "changed": {},
                "warnings": warnings,
                "revision_id": None,
            }
        )
    return _json(
        {
            "case": written,
            "revision": case.revision,
            "changed": {k: [old, new] for k, old, new in revision.changes()},
            "warnings": warnings,
            "revision_id": revision.pk,
        }
    )


@agent_endpoint(methods=("POST",), write=True)
def case_calculate(request, pk):
    """Start the page's calculation; optionally wait for it to finish."""
    case = _case(request, pk)
    data = _body(request)
    params = data.get("params") or {}
    if not isinstance(params, dict):
        raise ApiError(400, "params must be an object")
    wait = _seconds(data.get("wait"), MAX_CALCULATE_WAIT)
    adapter = adapters.get_adapter(case.app_type)
    job = adapter.start(case, params)
    # The open page picks this up and reloads to show the job and its result.
    cache.set(agent_job_key(case.pk), job.pk, AGENT_JOB_TIMEOUT)
    if job.kind == "monitoring":
        wait = min(wait, MONITORING_WAIT)
    return _json(job_dict(_wait_for(job, wait)))


@agent_endpoint()
def case_results(request, pk):
    case = _case(request, pk)
    adapter = adapters.get_adapter(case.app_type)
    return _json(adapters.json_safe(adapter.results(case)))


@agent_endpoint()
def case_figures(request, pk):
    case = _case(request, pk)
    adapter = adapters.get_adapter(case.app_type)
    return _json(
        [
            {"id": f["id"], "title": f.get("title"), "section": f.get("section")}
            for f in adapter.figures(case)
        ]
    )


@agent_endpoint()
def case_figure(request, pk, figure_id):
    case = _case(request, pk)
    adapter = adapters.get_adapter(case.app_type)
    fmt = (request.GET.get("format") or "data").lower()
    if fmt not in ("data", "plotly", "png"):
        raise ApiError(400, "format must be data, plotly or png")
    if fmt == "png" and not adapters.kaleido_available():
        return error_response(
            501,
            "PNG export needs the optional 'kaleido' package",
            {"hint": "pip install kaleido, or use format=data or format=plotly"},
        )
    try:
        fig = adapter.figure(case, figure_id)
    except KeyError:
        ids = [f["id"] for f in adapter.figures(case)]
        raise ApiError(404, f"unknown figure {figure_id!r}", {"figures": ids}) from None
    if fmt == "png":
        return HttpResponse(adapters.figure_png(fig), content_type="image/png")
    if fmt == "plotly":
        return _json(
            adapters.figure_json(
                fig, template=(request.GET.get("template") or "").lower() in _TRUE
            )
        )
    data = adapters.figure_data(fig)
    if not data.get("title"):
        # Some figures carry no layout title; the listing names them all.
        data["title"] = next(
            (f["title"] for f in adapter.figures(case) if f["id"] == figure_id), None
        )
    return _json({"id": figure_id, **data})


@agent_endpoint()
def case_revisions(request, pk):
    case = _case(request, pk)
    rows = case.agent_revisions.select_related("token").order_by("-number")[
        :REVISIONS_LIMIT
    ]
    return _json([r.as_dict() for r in rows])


@agent_endpoint(methods=("POST",), write=True)
def case_undo(request, pk):
    """Undo an agent revision (default: the newest one not undone)."""
    case = _case(request, pk)
    data = _body(request)
    if data.get("revision_id") not in (None, ""):
        revision = get_object_or_404(
            AgentRevision.objects.for_user(request.user).filter(case=case),
            pk=_int(data["revision_id"], "revision_id"),
        )
    else:
        revision = revisions.latest_undoable(case)
        if revision is None:
            raise ApiError(404, "nothing to undo")
    try:
        result = revisions.undo(revision, request.agent_token)
    except ValueError as exc:
        raise ApiError(409, str(exc)) from None
    return _json(result.as_dict())


@agent_endpoint(methods=("GET", "POST"), write=("POST",))
def case_notes(request, pk):
    case = _case(request, pk)
    if request.method == "GET":
        rows = case.agent_notes.order_by("-created", "-pk")[:NOTES_LIMIT]
        return _json([n.as_dict() for n in rows])
    body = _body(request).get("body")
    if not isinstance(body, str) or not body.strip():
        raise ApiError(400, 'send {"body": "text"}')
    if len(body) > MAX_NOTE:
        raise ApiError(400, f"body is longer than {MAX_NOTE} characters")
    note = AgentNote.objects.create(
        owner=request.user,
        case=case,
        body=body,
        author=(request.agent_token.name or "Agent")[:80],
    )
    return _json(note.as_dict(), status=201)


# --------------------------------------------------------------------------
# Jobs and schemas
# --------------------------------------------------------------------------


def _job(request, pk):
    return get_object_or_404(Job.objects.for_user(request.user), pk=pk)


@agent_endpoint()
def job_detail(request, pk):
    job = _job(request, pk)
    wait = _seconds(request.GET.get("wait"), MAX_JOB_WAIT)
    if job.kind == "monitoring":
        wait = min(wait, MONITORING_WAIT)
    return _json(job_dict(_wait_for(job, wait)))


@agent_endpoint(methods=("POST",), write=True)
def job_cancel(request, pk):
    job = _job(request, pk)
    jobs.cancel_job(job)
    job.refresh_from_db()
    return _json(job_dict(job))


_PARAM_SUFFIX = re.compile(r"^(_units?|_section_[12]|_point|_\d|$)")


def _param_for(key):
    """The ``schemas.PARAMETERS`` entry a state key belongs to, or None.

    ``suction_pressure_point_1``, ``suction_pressure_units_section_1`` and
    ``suction_pressure_section_1_point_guarantee`` all map to
    ``suction_pressure``; the longest parameter name wins (``flow_v`` over
    ``flow``), and ``flow_method`` maps to nothing.
    """
    best = None
    for name in schemas.PARAMETERS:
        if key.startswith(name) and _PARAM_SUFFIX.match(key[len(name) :]):
            if best is None or len(name) > len(best):
                best = name
    return schemas.PARAMETERS[best] if best else None


@agent_endpoint()
def schema(request, app_type):
    if app_type not in APP_TITLES:
        raise ApiError(404, f"unknown app type; one of {list(APP_TITLES)}")
    text = (request.GET.get("filter") or "").strip().lower()
    fields = []
    for key, f in schemas.get_schema(app_type).fields.items():
        if _SECRET_KEY.search(key):
            continue
        param = _param_for(key)
        haystack = [key, f.label or "", *map(str, f.options)]
        if param is not None:
            haystack.append(param.label)
        if text and not any(text in h.lower() for h in haystack):
            continue
        item = {
            "key": key,
            "kind": f.kind,
            "default": adapters.json_safe(f.default),
            "options": list(f.options),
            "label": f.label,
            "export": f.export,
        }
        if f.units_key:
            # The key holding this value's unit (not always the "matching"
            # name: back-to-back guarantees share section 1's units key).
            item["units_key"] = f.units_key
        if param is not None:
            item["param"] = {
                "label": param.label,
                "units": list(param.units),
                "help": param.help,
            }
        fields.append(item)
    out = {"app_type": app_type, "fields": fields}
    try:
        adapter = adapters.get_adapter(app_type)
    except adapters.AdapterMissing:
        out["calculate_params"] = None
    else:
        out["calculate_params"] = getattr(adapter, "PARAMS", {})
    return _json(out)


@login_not_required
@csrf_exempt
def not_found(request, path=""):
    """Unknown API paths get the API's JSON error, not the HTML 404 page."""
    return error_response(
        404, f"no such endpoint: {request.path}", {"endpoints": ENDPOINTS}
    )
