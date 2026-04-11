"""Root URL configuration for the ccp web application."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


_APP_PREFIXES = [
    ("", "apps.home.urls"),
    ("straight-through/", "apps.straight_through.urls"),
    ("back-to-back/", "apps.back_to_back.urls"),
    ("curves-conversion/", "apps.curves_conversion.urls"),
    ("performance-evaluation/", "apps.performance_evaluation.urls"),
    ("reports/", "apps.reports.urls"),
    ("core/", "apps.core.urls"),
    ("integrations/", "apps.integrations.urls"),
]

urlpatterns = []
for _prefix, _module in _APP_PREFIXES:
    # Stub apps (Units 2-12) ship without a urls.py; swallow only the
    # missing-module error so real import failures still surface.
    try:
        urlpatterns.append(path(_prefix, include(_module)))
    except ModuleNotFoundError:
        continue

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
