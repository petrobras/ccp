"""Curves digitizer page: upload a vendor curve PDF, digitize it in the
background, review every plot with the traced points over the vendor image,
edit the points, and hand the curves to the curves conversion page."""

import json
import threading
from collections import OrderedDict

from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_POST

from ccp_web.core import jobs, storage
from ccp_web.core.models import Case, Job
from ccp_web.core.state import save_post
from ccp_web.core.views import (
    current_project,
    get_case,
    is_htmx,
    new_case,
    workspace_context,
)
from ccp_web.services import digitizer, units

APP_TYPES = [Case.CURVES_DIGITIZER]

_doc_cache = OrderedDict()
_img_cache = OrderedDict()
_lock = threading.Lock()


def _cached(cache, key, build, size):
    with _lock:
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
    value = build()
    with _lock:
        cache[key] = value
        while len(cache) > size:
            cache.popitem(last=False)
    return value


def load_data(case, key="digitized"):
    """The digitized document dict (cached per artifact content)."""
    artifact = case.artifact(key)
    if artifact is None:
        return None
    data = _cached(
        _doc_cache, artifact.sha256, lambda: json.loads(artifact.read()), size=8
    )
    # callers may edit it: hand out a copy
    return json.loads(json.dumps(data))


def save_data(case, data):
    storage.save_artifact(case, "digitized", "digitized.json", digitizer.dumps(data))


def page_context(request, case, errors=None):
    ctx = workspace_context(request, case)
    job = (
        Job.objects.filter(case=case, kind="digitize_pdf").order_by("-created").first()
    )
    if errors is None and job and job.status == Job.FAILED:
        errors = job.result.get("errors")
    pdf = case.file("curve_pdf")
    data = load_data(case)
    rows, unassigned = (
        digitizer.cases_overview(data) if data else ([], {"plots": [], "pages": []})
    )
    n_plots = len(data.get("plots", [])) if data else 0
    n_edited = sum(1 for p in data.get("plots", []) if p.get("edited")) if data else 0
    ctx.update(
        {
            "page": case.app_type,
            "app_type": case.app_type,
            "state": case.state,
            "errors": errors or {},
            "job": job,
            "pdf": pdf,
            "available": digitizer.available(),
            "rows": rows,
            "unassigned": unassigned,
            "n_plots": n_plots,
            "n_edited": n_edited,
            "has_result": data is not None,
            "recent_jobs": Job.objects.filter(case=case).order_by("-created")[:6],
        }
    )
    steps = [
        ("upload", "Vendor PDF", pdf.name if pdf else "upload", pdf is not None),
        (
            "run",
            "Digitize",
            job.get_status_display().lower() if job else "",
            bool(rows),
        ),
        ("cases", "Review", f"{len(rows)} cases" if rows else "", bool(rows)),
        ("editor", "Edit points", f"{n_edited} plots edited", n_edited > 0),
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
    ctx = page_context(request, case)
    plot_id = request.GET.get("plot")
    if plot_id and ctx["has_result"]:
        ctx.update(_editor_context(case, plot_id))
    return render(request, "digitizer/page.html", ctx)


def _error_job(case, errors, message="Check the highlighted fields."):
    return Job(
        owner=case.owner,
        case=case,
        kind="digitize_pdf",
        status=Job.FAILED,
        error=message,
        result={"errors": errors},
    )


@require_POST
def digitize(request, pk):
    case = get_case(request, pk, APP_TYPES)
    save_post(case, request.POST)
    try:
        if case.file("curve_pdf") is None:
            raise units.InputError({"curve_pdf": "Upload a curve PDF first."})
        if not digitizer.available():
            raise units.InputError(
                {
                    "curve_pdf": (
                        "The digitizer needs the 'digitize' extra "
                        "(pip install ccp-performance[digitize]) and Tesseract OCR."
                    )
                }
            )
        digitizer.parse_pages(case.state.get("digitize_pages"))
    except units.InputError as exc:
        job = _error_job(case, exc.errors)
    else:
        jobs.active_jobs(case, ["digitize_pdf"]).update(cancel_requested=True)
        job = jobs.start_job(case, "digitize_pdf")
    return render(request, "core/partials/job.html", {"job": job, "case": case})


@require_GET
def results(request, pk):
    case = get_case(request, pk, APP_TYPES)
    return render(
        request, "digitizer/partials/results.html", page_context(request, case)
    )


def _editor_context(case, plot_id):
    data = load_data(case)
    if data is None:
        raise Http404("Nothing digitized yet")
    try:
        payload = digitizer.editor_payload(data, plot_id)
    except KeyError:
        raise Http404("No such plot") from None
    payload["urls"] = {
        "image": reverse("digitizer:image", args=[case.pk, plot_id]),
        "save": reverse("digitizer:save", args=[case.pk, plot_id]),
    }
    return {"plot": payload, "plot_id": plot_id}


@require_GET
def editor(request, pk, plot_id):
    case = get_case(request, pk, APP_TYPES)
    ctx = {"case": case, **_editor_context(case, plot_id)}
    return render(request, "digitizer/partials/editor.html", ctx)


@require_GET
def plot_image(request, pk, plot_id):
    case = get_case(request, pk, APP_TYPES)
    pdf = case.file("curve_pdf")
    data = load_data(case)
    if pdf is None or data is None:
        raise Http404()
    plot = next((p for p in data["plots"] if p["id"] == plot_id), None)
    if plot is None:
        raise Http404()
    key = (pdf.file.name, plot_id, digitizer.IMAGE_DPI)
    etag = f'"{abs(hash(key)):x}"'
    if request.headers.get("If-None-Match") == etag:
        return HttpResponse(status=304)
    png = _cached(
        _img_cache, key, lambda: digitizer.render_plot_png(pdf.read(), plot), size=48
    )
    response = HttpResponse(png, content_type="image/png")
    response["Cache-Control"] = "private, max-age=86400"
    response["ETag"] = etag
    return response


@require_POST
def plot_save(request, pk, plot_id):
    """Store the edited curves of one plot (JSON body from the editor)."""
    case = get_case(request, pk, APP_TYPES)
    data = load_data(case)
    if data is None:
        raise Http404()
    try:
        body = json.loads(request.body or b"{}")
        notes = digitizer.update_plot(data, plot_id, body.get("curves"))
    except KeyError:
        raise Http404("No such plot") from None
    except (ValueError, units.InputError) as exc:
        errors = getattr(exc, "errors", None) or {"curves": str(exc)}
        return JsonResponse({"ok": False, "errors": errors}, status=400)
    save_data(case, data)
    payload = digitizer.editor_payload(data, plot_id)
    return JsonResponse(
        {"ok": True, "notes": notes, "curves": payload["curves"], "edited": True}
    )


@require_POST
def plot_reset(request, pk, plot_id):
    """Back to the automatic digitization for one plot."""
    case = get_case(request, pk, APP_TYPES)
    data = load_data(case)
    original = load_data(case, "digitized_original")
    if data is None or original is None:
        raise Http404()
    try:
        digitizer.reset_plot(data, original, plot_id)
    except KeyError:
        raise Http404("No such plot") from None
    save_data(case, data)
    ctx = {"case": case, **_editor_context(case, plot_id)}
    response = render(request, "digitizer/partials/editor.html", ctx)
    response["HX-Trigger"] = "ccp:digitized-changed"
    return response


@require_GET
def export(request, pk):
    case = get_case(request, pk, APP_TYPES)
    data = load_data(case)
    if data is None:
        raise Http404()
    content = digitizer.export_zip(data)
    response = HttpResponse(content, content_type="application/zip")
    name = slugify(case.name) or "digitized"
    response["Content-Disposition"] = f'attachment; filename="{name}-curves.zip"'
    return response


@require_POST
def to_conversion(request, pk):
    """New curves conversion case with the selected digitized cases."""
    case = get_case(request, pk, APP_TYPES)
    data = load_data(case)
    if data is None:
        raise Http404()
    slugs = request.POST.getlist("case")
    try:
        state, files = digitizer.conversion_cases(data, slugs)
    except units.InputError as exc:
        messages.error(request, "; ".join(exc.errors.values()))
        target = case.get_absolute_url() + "#sec-cases"
    else:
        conversion = new_case(
            current_project(request),
            Case.CURVES_CONVERSION,
            name=f"{case.name} (digitized)",
            state=state,
        )
        for key, name, content in files:
            storage.save_case_file(conversion, key, "engauge_csv", name, content)
        n = len(files) // 2
        messages.success(
            request,
            f"Created with {n} design case{'s' if n != 1 else ''} from the digitized "
            "curves. Fill in each gas composition, then Load curves.",
        )
        target = conversion.get_absolute_url()
    if is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = target
        return response
    return redirect(target)
