"""URL routes for the curves conversion page."""

from django.urls import path

from apps.curves_conversion import views

app_name = "curves_conversion"

urlpatterns = [
    path("", views.page, name="page"),
    path("convert/", views.convert, name="convert"),
    path("upload-csv/", views.upload_csv, name="upload_csv"),
    path("download-csv/<str:case>/", views.download_csv, name="download_csv"),
    path("save.ccp", views.save_ccp, name="save_ccp"),
    path("load.ccp", views.load_ccp, name="load_ccp"),
]
