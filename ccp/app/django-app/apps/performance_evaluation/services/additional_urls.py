"""Wiring hints for Unit 8's ``urls.py``.

Import and include these patterns from ``apps/performance_evaluation/urls.py``::

    from apps.performance_evaluation.services.additional_urls import urlpatterns as extra
    urlpatterns += extra
"""

from __future__ import annotations

from django.urls import path

from apps.performance_evaluation.views.compute import (
    compute_view,
    download_report_view,
)
from apps.performance_evaluation.views.monitoring import (
    poll_view,
    start_monitoring_view,
    stop_monitoring_view,
)

urlpatterns = [
    path("compute/", compute_view, name="performance_evaluation_compute"),
    path("report/", download_report_view, name="performance_evaluation_report"),
    path(
        "monitoring/start/",
        start_monitoring_view,
        name="performance_evaluation_monitoring_start",
    ),
    path(
        "monitoring/stop/",
        stop_monitoring_view,
        name="performance_evaluation_monitoring_stop",
    ),
    path(
        "monitoring/poll/",
        poll_view,
        name="performance_evaluation_monitoring_poll",
    ),
]
