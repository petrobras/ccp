"""Workspace views shared by every page: projects, cases, files and jobs."""

import mimetypes
import re

from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ccp_web.services import ccpfile, schemas

from . import jobs, storage
from .models import Case, CaseFile, Job, Project
from .state import base_revision, save_post, update_state

APP_TITLES = dict(Case.APP_TYPES)
CURVE_IMAGE_KEY = re.compile(r"^fig_(head|eff|discharge_pressure|power)(_sec[12])?$")
ENGAUGE_KEY = re.compile(r"^curves_file_[12]_case_[A-E]$")
PLANT_DATA_KEY = "plant_data"
CURVE_PDF_KEY = "curve_pdf"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def current_project(request):
    """The project selected in the session, creating a default one."""
    project = None
    pid = request.session.get("project_id")
    if pid:
        project = Project.objects.for_user(request.user).filter(pk=pid).first()
    if project is None:
        project = default_project(request.user)
    request.session["project_id"] = project.pk
    return project


def default_project(user):
    """The user's oldest project, creating a "Default" one if there is none."""
    project = Project.objects.for_user(user).order_by("created").first()
    if project is None:
        project = Project.objects.create(owner=user, name="Default")
    return project


def get_case(request, pk, app_types=None):
    case = get_object_or_404(Case.objects.for_user(request.user), pk=pk)
    if app_types and case.app_type not in app_types:
        raise Http404("Wrong page for this case")
    if request.session.get("project_id") != case.project_id:
        request.session["project_id"] = case.project_id
    return case


def new_case(project, app_type, name=None, state=None):
    count = Case.objects.filter(project=project, app_type=app_type).count()
    name = name or f"{APP_TITLES[app_type]} {count + 1}"
    base = schemas.default_state(app_type)
    if state:
        base.update(state)
    base["session_name"] = base.get("session_name") or name
    return Case.objects.create(
        owner=project.owner,
        project=project,
        app_type=app_type,
        name=name,
        state=schemas.normalize(app_type, base),
    )


def workspace_context(request, case=None):
    """Context for the app shell: nav counts, project list, recent cases."""
    project = current_project(request)
    cases = Case.objects.for_user(request.user).filter(project=project)
    counts = {t: 0 for t, _ in Case.APP_TYPES}
    for app_type in cases.values_list("app_type", flat=True):
        counts[app_type] += 1
    nav_cases = cases.filter(app_type=case.app_type)[:12] if case else []
    return {
        "project": project,
        "projects": Project.objects.for_user(request.user),
        "nav_counts": counts,
        "nav_cases": nav_cases,
        "case": case,
        "app_titles": APP_TITLES,
    }


def is_htmx(request):
    return bool(getattr(request, "htmx", False))


def refresh_response():
    """Ask htmx to reload the page: an agent changed the case since it rendered.

    The stale-form guard (``core.state.save_post``) already dropped the keys
    the agent changed; the reload shows the user the agent's values (and a
    calculation is not started on values the user has not seen).
    """
    response = HttpResponse("The agent changed this case; reloading.")
    response["HX-Refresh"] = "true"
    return response


# --------------------------------------------------------------------------
# Home and projects
# --------------------------------------------------------------------------


@require_GET
def home(request):
    ctx = workspace_context(request)
    project = ctx["project"]
    ctx["cases"] = Case.objects.for_user(request.user).filter(project=project)
    ctx["recent_jobs"] = (
        Job.objects.for_user(request.user)
        .filter(case__project=project)
        .select_related("case")[:8]
    )
    ctx["page"] = "home"
    return render(request, "core/home.html", ctx)


@require_POST
def project_create(request):
    name = (request.POST.get("name") or "").strip() or "New project"
    project = Project.objects.create(owner=request.user, name=name)
    request.session["project_id"] = project.pk
    return redirect("core:home")


@require_POST
def project_select(request, pk):
    project = get_object_or_404(Project.objects.for_user(request.user), pk=pk)
    request.session["project_id"] = project.pk
    return redirect(request.POST.get("next") or "core:home")


@require_POST
def project_rename(request, pk):
    project = get_object_or_404(Project.objects.for_user(request.user), pk=pk)
    name = (request.POST.get("name") or "").strip()
    if name:
        project.name = name
        project.save(update_fields=["name", "updated"])
    return redirect("core:home")


@require_POST
def project_delete(request, pk):
    project = get_object_or_404(Project.objects.for_user(request.user), pk=pk)
    if Project.objects.for_user(request.user).count() <= 1:
        messages.error(request, "The last project cannot be deleted.")
        return redirect("core:home")
    for case in project.cases.all():
        storage.delete_case_storage(case)
    project.delete()
    request.session.pop("project_id", None)
    return redirect("core:home")


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------


@require_GET
def app_index(request, app_type):
    """Open the most recent case of a page type, creating one if none exists."""
    if app_type not in APP_TITLES:
        raise Http404()
    project = current_project(request)
    case = (
        Case.objects.for_user(request.user)
        .filter(project=project, app_type=app_type)
        .order_by("-updated")
        .first()
    )
    if case is None:
        case = new_case(project, app_type)
    return redirect(case.get_absolute_url())


@require_POST
def case_create(request, app_type):
    if app_type not in APP_TITLES:
        raise Http404()
    project = current_project(request)
    name = (request.POST.get("name") or "").strip() or None
    case = new_case(project, app_type, name=name)
    return redirect(case.get_absolute_url())


def import_ccp(project, name, content, expected_app_type=None):
    """Create a case from ``.ccp`` bytes (files and artifacts included)."""
    parsed = ccpfile.read_ccp(content, expected_app_type=expected_app_type)
    return create_from_ccp(project, name, parsed)


def create_from_ccp(project, name, parsed):
    """Create a case from a parsed ``ccpfile.CcpFile``."""
    state = dict(parsed.state)
    state["session_name"] = name
    with transaction.atomic():
        case = Case.objects.create(
            owner=project.owner,
            project=project,
            app_type=parsed.app_type,
            name=name,
            state=state,
            source_version=parsed.version[:40],
        )
        for key, (kind, fname, data) in parsed.files.items():
            storage.save_case_file(case, key, kind, fname, data)
        for key, (fname, data) in parsed.artifacts.items():
            storage.save_artifact(case, key, fname, data)
    return case


@require_POST
def case_import(request):
    upload = request.FILES.get("file")
    if upload is None:
        messages.error(request, "Choose a .ccp file to open.")
        return redirect(request.POST.get("next") or "core:home")
    name = re.sub(r"\.ccp$", "", upload.name, flags=re.I) or "Imported"
    expected = request.POST.get("app_type") or None
    try:
        case = import_ccp(current_project(request), name, upload.read(), expected)
    except ccpfile.CcpFileError as exc:
        messages.error(request, str(exc))
        return redirect(request.POST.get("next") or "core:home")
    messages.success(request, f"Opened {upload.name}.")
    return redirect(case.get_absolute_url())


def case_ccp_bytes(case):
    files = [
        (f.key, f.kind, f.name, f.read())
        for f in case.files.all()
        if f.kind in ("curve_image", "engauge_csv", "curve_pdf")
    ]
    artifacts = [
        (a.key, a.name, a.read())
        for a in case.artifacts.all()
        if a.name.endswith(".toml")
        or a.key == "evaluation"
        or a.key in ccpfile.DIGITIZER_ARTIFACTS
    ]
    state = dict(case.state)
    state["session_name"] = case.name
    return ccpfile.write_ccp(case.app_type, state, files=files, artifacts=artifacts)


def ccp_filename(case):
    return f"{slugify(case.name) or 'session'}.ccp"


@require_GET
def case_export(request, pk):
    case = get_case(request, pk)
    content = case_ccp_bytes(case)
    filename = ccp_filename(case)
    response = HttpResponse(content, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_POST
def case_rename(request, pk):
    case = get_case(request, pk)
    name = (request.POST.get("name") or "").strip()
    if name:
        # Under the row lock: saving the state read above could put back
        # values an agent wrote meanwhile.
        update_state(case, session_name=name)
        case.name = name
        case.save(update_fields=["name", "updated"])
    return redirect(case.get_absolute_url())


def duplicate_case(case, name=None):
    """A copy of ``case`` in its project, with its files and artifacts."""
    copy = new_case(
        case.project,
        case.app_type,
        name=name or f"{case.name} (copy)",
        state=case.state,
    )
    for f in case.files.all():
        storage.save_case_file(copy, f.key, f.kind, f.name, f.read())
    for a in case.artifacts.all():
        storage.save_artifact(copy, a.key, a.name, a.read())
    return copy


@require_POST
def case_duplicate(request, pk):
    copy = duplicate_case(get_case(request, pk))
    return redirect(copy.get_absolute_url())


@require_POST
def case_delete(request, pk):
    case = get_case(request, pk)
    app_type = case.app_type
    jobs.active_jobs(case).update(cancel_requested=True)
    storage.delete_case_storage(case)
    case.delete()
    messages.success(request, "Case deleted.")
    others = Case.objects.for_user(request.user).filter(
        project_id=request.session.get("project_id"), app_type=app_type
    )
    if others.exists():
        return redirect(others.first().get_absolute_url())
    return redirect("core:home")


@require_POST
def case_state(request, pk):
    """Autosave: merge the submitted form fields into the case state."""
    case = get_case(request, pk)
    save_post(case, request.POST, base_revision(request))
    response = render(request, "core/partials/saved.html", {"case": case})
    response["HX-Trigger"] = "ccp:saved"
    if case.stale:
        response["HX-Refresh"] = "true"
    return response


# --------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------


def _file_kind(key):
    if CURVE_IMAGE_KEY.match(key):
        return CaseFile.CURVE_IMAGE
    if ENGAUGE_KEY.match(key):
        return CaseFile.ENGAUGE_CSV
    if key == PLANT_DATA_KEY:
        return "plant_data"
    if key == CURVE_PDF_KEY:
        return CaseFile.CURVE_PDF
    return None


@require_http_methods(["GET", "POST", "DELETE"])
def case_file(request, pk, key):
    case = get_case(request, pk)
    if request.method == "GET":
        obj = case.file(key)
        if obj is None:
            raise Http404()
        content_type = mimetypes.guess_type(obj.name)[0] or "application/octet-stream"
        return FileResponse(
            obj.file.open("rb"), content_type=content_type, filename=obj.name
        )
    kind = _file_kind(key)
    if kind is None:
        return HttpResponseBadRequest("Unknown file slot")
    if request.method == "DELETE":
        storage.delete_case_file(case, key)
    else:
        upload = request.FILES.get("file")
        if upload is None:
            return HttpResponseBadRequest("No file")
        allowed = {
            CaseFile.CURVE_IMAGE: (".png", ".jpg", ".jpeg"),
            CaseFile.ENGAUGE_CSV: (".csv",),
            "plant_data": (".csv", ".parquet", ".txt"),
            CaseFile.CURVE_PDF: (".pdf",),
        }[kind]
        if not upload.name.lower().endswith(allowed):
            return HttpResponseBadRequest(f"Expected a {'/'.join(allowed)} file")
        storage.save_case_file(case, key, kind, upload.name, upload.read())
    return render(
        request,
        "core/partials/file_slot.html",
        {"case": case, "slot": key, "file": case.file(key), "kind": kind},
    )


@require_GET
def artifact_download(request, pk, key):
    case = get_case(request, pk)
    obj = case.artifact(key)
    if obj is None:
        raise Http404()
    content_type = mimetypes.guess_type(obj.name)[0] or "application/octet-stream"
    return FileResponse(
        obj.file.open("rb"),
        content_type=content_type,
        filename=obj.name,
        as_attachment=True,
    )


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------


@require_GET
def job_status(request, pk):
    job = get_object_or_404(
        Job.objects.for_user(request.user).select_related("case"), pk=pk
    )
    response = render(request, "core/partials/job.html", {"job": job, "case": job.case})
    if not job.is_active and request.GET.get("was_active"):
        response["HX-Trigger"] = f"ccp:job-done-{job.case_id}"
    return response


@require_POST
def job_cancel(request, pk):
    job = get_object_or_404(Job.objects.for_user(request.user), pk=pk)
    jobs.cancel_job(job)
    job.refresh_from_db()
    return render(request, "core/partials/job.html", {"job": job, "case": job.case})
