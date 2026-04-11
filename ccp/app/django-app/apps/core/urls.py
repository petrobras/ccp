"""URL routes for ``apps.core`` (mounted under ``/core/`` by Unit 1)."""

from django.urls import path

from apps.core.views import file_download, file_upload

app_name = "core"

urlpatterns = [
    path("upload/ccp/", file_upload.upload_ccp, name="upload-ccp"),
    path("upload/csv/", file_upload.upload_csv, name="upload-csv"),
    path("upload/curve-png/", file_upload.upload_curve_png, name="upload-curve-png"),
    path(
        "download/ccp/<str:session_id>/",
        file_download.download_ccp,
        name="download-ccp",
    ),
    path(
        "download/excel/<str:session_id>/",
        file_download.download_excel,
        name="download-excel",
    ),
]
