"""Test URL conf mounting only the curves conversion app."""

from django.urls import include, path

urlpatterns = [
    path("curves-conversion/", include("apps.curves_conversion.urls")),
]
