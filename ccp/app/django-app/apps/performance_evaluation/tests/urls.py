"""Dedicated URLconf used by the performance evaluation test suite."""

from django.urls import path

from apps.performance_evaluation.views.compute import compute_view
from apps.performance_evaluation.views.monitoring import (
    poll_view,
    start_monitoring_view,
    stop_monitoring_view,
)

urlpatterns = [
    path("performance-evaluation/compute/", compute_view, name="compute"),
    path(
        "performance-evaluation/monitoring/start/",
        start_monitoring_view,
        name="mon_start",
    ),
    path(
        "performance-evaluation/monitoring/stop/",
        stop_monitoring_view,
        name="mon_stop",
    ),
    path(
        "performance-evaluation/monitoring/poll/",
        poll_view,
        name="mon_poll",
    ),
]
