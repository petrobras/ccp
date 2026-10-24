"""Browser side of the agent API (session auth, CSRF as usual).

The page reports where the user is (presence), polls for agent writes and
notes, and offers Undo. The agent itself never calls these: it uses the
bearer-token API in ``api.py``.
"""

import json
import time

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ccp_web.core.models import Case, Job
from ccp_web.core.views import workspace_context

from . import revisions
from .models import AgentNote, AgentRevision, AgentToken

PRESENCE_KEY = "ccp:agent:presence:{user_id}"
NAVIGATE_KEY = "ccp:agent:navigate:{user_id}"
AGENT_JOB_KEY = "ccp:agent:job:{case_id}"
AGENT_JOB_TIMEOUT = 24 * 3600
PRESENCE_TIMEOUT = 24 * 3600
PANEL_REVISIONS = 20
PANEL_NOTES = 20
MAX_CHANGES = 200
_TEXT_LIMITS = {"page": 80, "section": 120, "url": 2000, "title": 300}


def presence_key(user):
    return PRESENCE_KEY.format(user_id=user.pk)


def navigate_key(user):
    return NAVIGATE_KEY.format(user_id=user.pk)


def agent_job_key(case_id):
    """Cache key of the last job the agent started on a case."""
    return AGENT_JOB_KEY.format(case_id=case_id)


def _agent_job(case):
    """``{id, status, active}`` of the last job the agent started, or None.

    Starting a job does not bump the case revision, so without this the
    page would keep showing the old results after an agent's ``calculate``.
    """
    pk = cache.get(agent_job_key(case.pk))
    job = Job.objects.filter(pk=pk, case=case).first() if pk else None
    if job is None:
        return None
    return {"id": job.pk, "status": job.status, "active": job.is_active}


def get_presence(user):
    """What the user last had open: ``{case, page, section, url, title, seen}``."""
    return cache.get(presence_key(user))


def _int(value, default=None):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _payload(request):
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body or b"{}")
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return request.POST


@require_POST
def presence(request):
    """Store the page the user is looking at, for the agent's ``context``."""
    data = _payload(request)
    pk = _int(data.get("case"))
    if (
        pk is not None
        and not Case.objects.for_user(request.user).filter(pk=pk).exists()
    ):
        pk = None
    value = {
        key: str(data.get(key) or "")[:limit] for key, limit in _TEXT_LIMITS.items()
    }
    value.update({"case": pk, "seen": time.time()})
    cache.set(presence_key(request.user), value, PRESENCE_TIMEOUT)
    return HttpResponse(status=204)


@require_GET
def poll(request):
    """Agent writes after ``rev``, unread notes after ``note``, and navigation.

    ``navigate`` (set by the API's ``context/open``) is handed out once.
    ``agent_job`` is the last job the agent started on the case; the page
    reloads when it changes, to show the job and its results.
    """
    url = cache.get(navigate_key(request.user))
    if url is not None:
        cache.delete(navigate_key(request.user))
    payload = {
        "revision": None,
        "changes": [],
        "notes": [],
        "navigate": url,
        "agent_job": None,
    }
    pk = _int(request.GET.get("case"))
    if pk is not None:
        case = get_object_or_404(Case.objects.for_user(request.user), pk=pk)
        rev = _int(request.GET.get("rev"), case.revision)
        last_note = _int(request.GET.get("note"), 0)
        changes = (
            case.agent_revisions.filter(number__gt=rev)
            .select_related("token")
            .order_by("number")[:MAX_CHANGES]
        )
        notes = case.agent_notes.filter(dismissed=False, pk__gt=last_note).order_by(
            "pk"
        )
        payload.update(
            {
                "revision": case.revision,
                "changes": [r.as_dict() for r in changes],
                "notes": [n.as_dict() for n in notes],
                "agent_job": _agent_job(case),
            }
        )
    return JsonResponse(payload)


@require_POST
def undo(request, pk):
    revision = get_object_or_404(
        AgentRevision.objects.for_user(request.user).select_related("case"), pk=pk
    )
    try:
        result = revisions.undo(revision, request.user)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return JsonResponse(
        {"revision": result.number, "case": result.case_id, "undo": result.as_dict()}
    )


@require_POST
def note_dismiss(request, pk):
    note = get_object_or_404(AgentNote.objects.for_user(request.user), pk=pk)
    if not note.dismissed:
        note.dismissed = True
        note.save(update_fields=["dismissed"])
    return JsonResponse({"ok": True, "id": note.pk})


@require_GET
def panel(request, pk):
    """Drawer partial: the case's recent agent revisions and notes."""
    case = get_object_or_404(Case.objects.for_user(request.user), pk=pk)
    rows = list(
        case.agent_revisions.select_related("token").order_by("-number")[
            :PANEL_REVISIONS
        ]
    )
    flags = revisions.change_flags(list(case.agent_revisions.order_by("number")))
    for rev in rows:
        # The button undoes a change ("Undo") or a plain undo ("Redo").
        rev.offers_undo = flags.get(rev.pk, True)
    notes = case.agent_notes.order_by("-created", "-pk")[:PANEL_NOTES]
    return render(
        request,
        "agent/panel.html",
        {"case": case, "revisions": rows, "notes": notes},
    )


@require_http_methods(["GET", "POST"])
def tokens(request):
    """Personal agent tokens: list, create (plaintext shown once), revoke."""
    created = None
    if request.method == "POST":
        scope = request.POST.get("scope")
        if scope not in {AgentToken.READ, AgentToken.WRITE}:
            scope = AgentToken.WRITE
        name = (request.POST.get("name") or "").strip() or "agent"
        row, plaintext = AgentToken.issue(request.user, name, scope=scope)
        created = {"token": row, "plaintext": plaintext}
    ctx = workspace_context(request)
    rows = AgentToken.objects.for_user(request.user)
    ctx.update(
        {
            "page": "agent_tokens",
            "personal": rows.filter(kind=AgentToken.PERSONAL),
            "desktop": rows.filter(kind=AgentToken.DESKTOP),
            "created": created,
            "scopes": AgentToken.SCOPES,
            "api_url": request.build_absolute_uri("/api/agent/v1/"),
        }
    )
    response = render(request, "agent/tokens.html", ctx)
    # The plaintext is shown once; keep it out of every cache.
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def token_revoke(request, pk):
    row = get_object_or_404(
        AgentToken.objects.for_user(request.user).filter(kind=AgentToken.PERSONAL),
        pk=pk,
    )
    row.delete()
    return redirect("agent:tokens")
