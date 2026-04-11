"""Test URLconf — mounts the straight-through app under ``/straight-through/``."""

from django.urls import include, path

urlpatterns = [
    path("straight-through/", include("apps.straight_through.urls")),
]
