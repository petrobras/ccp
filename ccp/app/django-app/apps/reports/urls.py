"""URL routes for :mod:`apps.reports`."""

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("<str:session_id>/", views.report_view, name="detail"),
    path("<str:session_id>/download/", views.report_download, name="download"),
]
