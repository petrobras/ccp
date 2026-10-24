"""Agent HTTP API routes (``api/agent/v1/``), bearer-token authenticated.

Paths have no trailing slash (``cases/3/state``); one is accepted too, so a
client that adds it does not get a redirect it cannot follow with a body.
"""

from django.urls import path, re_path

from . import api

app_name = "agent_api"


def _route(route, view, name):
    """Both ``route`` and ``route/`` (the bare root is only ``""``)."""
    if not route:
        return [path("", view, name=name)]
    return [path(route, view, name=name), path(route + "/", view)]


urlpatterns = [
    *_route("", api.root, "root"),
    *_route("context", api.context, "context"),
    *_route("context/open", api.context_open, "context_open"),
    *_route("projects", api.projects, "projects"),
    *_route("cases", api.cases, "cases"),
    *_route("cases/<int:pk>", api.case_detail, "case"),
    *_route("cases/<int:pk>/duplicate", api.case_duplicate, "case_duplicate"),
    *_route("cases/<int:pk>/export", api.case_export, "case_export"),
    *_route("cases/<int:pk>/state", api.case_state, "case_state"),
    *_route("cases/<int:pk>/calculate", api.case_calculate, "case_calculate"),
    *_route("cases/<int:pk>/results", api.case_results, "case_results"),
    *_route("cases/<int:pk>/figures", api.case_figures, "case_figures"),
    *_route("cases/<int:pk>/figures/<str:figure_id>", api.case_figure, "case_figure"),
    *_route("cases/<int:pk>/revisions", api.case_revisions, "case_revisions"),
    *_route("cases/<int:pk>/undo", api.case_undo, "case_undo"),
    *_route("cases/<int:pk>/notes", api.case_notes, "case_notes"),
    *_route("jobs/<int:pk>", api.job_detail, "job"),
    *_route("jobs/<int:pk>/cancel", api.job_cancel, "job_cancel"),
    *_route("schema/<str:app_type>", api.schema, "schema"),
    # Last: anything else under the API is a JSON 404.
    re_path(r"^(?P<path>.*)$", api.not_found, name="not_found"),
]
