"""URL configuration for the Performance Evaluation Django app.

Unit 8 owns ``/`` and ``/config/`` plus HTMX partial endpoints for the
tag-mapping UI. ``/compute/``, ``/monitoring/`` and ``/results/`` are
declared here as placeholder views returning HTTP 204 - Unit 9 replaces
them at merge time.
"""

from django.http import HttpResponse
from django.urls import path

from .views import config as config_views

app_name = "performance_evaluation"


def _placeholder(_request, *_args, **_kwargs):
    """Return HTTP 204 until Unit 9 ships the real view."""
    return HttpResponse(status=204)


urlpatterns = [
    path("", config_views.config_view, name="index"),
    path("config/", config_views.config_view, name="config"),
    path(
        "upload-impeller/<str:case>/",
        config_views.upload_impeller,
        name="upload_impeller",
    ),
    path(
        "upload-curves/<str:case>/",
        config_views.upload_curves,
        name="upload_curves",
    ),
    path(
        "tag-mappings/add/",
        config_views.tag_mapping_add,
        name="tag_mapping_add",
    ),
    path(
        "tag-mappings/remove/<str:parameter>/",
        config_views.tag_mapping_remove,
        name="tag_mapping_remove",
    ),
    path(
        "tag-mappings/flow-method/",
        config_views.flow_method_change,
        name="flow_method_change",
    ),
    path("load-ccp/", config_views.load_ccp_view, name="load_ccp"),
    # Unit 9 placeholders
    path("compute/", _placeholder, name="compute"),
    path("monitoring/", _placeholder, name="monitoring"),
    path("results/", _placeholder, name="results"),
]
