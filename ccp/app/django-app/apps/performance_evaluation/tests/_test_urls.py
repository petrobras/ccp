"""Test URL conf - mounts only the performance_evaluation app."""

from django.urls import include, path

urlpatterns = [
    path(
        "performance-evaluation/",
        include("apps.performance_evaluation.urls", namespace="performance_evaluation"),
    ),
]
