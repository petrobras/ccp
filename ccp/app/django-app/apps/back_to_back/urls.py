"""URL configuration for the back-to-back compressor page."""

from __future__ import annotations

from django.urls import path

from apps.back_to_back import views

app_name = "back_to_back"

urlpatterns = [
    path("", views.index, name="index"),
    path("compute/", views.compute, name="compute"),
    path("upload-curve/", views.upload_curve, name="upload_curve"),
    path("save.ccp", views.save_ccp, name="save_ccp"),
    path("load.ccp", views.load_ccp, name="load_ccp"),
]
