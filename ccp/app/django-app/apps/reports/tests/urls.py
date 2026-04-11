"""Root URL conf used by :mod:`apps.reports` isolated tests."""

from django.urls import include, path

urlpatterns = [
    path("reports/", include("apps.reports.urls", namespace="reports")),
]
