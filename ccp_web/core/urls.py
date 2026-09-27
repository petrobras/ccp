from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<int:pk>/select/", views.project_select, name="project_select"),
    path("projects/<int:pk>/rename/", views.project_rename, name="project_rename"),
    path("projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("app/<str:app_type>/", views.app_index, name="app_index"),
    path("cases/new/<str:app_type>/", views.case_create, name="case_create"),
    path("cases/import/", views.case_import, name="case_import"),
    path("cases/<int:pk>/export/", views.case_export, name="case_export"),
    path("cases/<int:pk>/rename/", views.case_rename, name="case_rename"),
    path("cases/<int:pk>/duplicate/", views.case_duplicate, name="case_duplicate"),
    path("cases/<int:pk>/delete/", views.case_delete, name="case_delete"),
    path("cases/<int:pk>/state/", views.case_state, name="case_state"),
    path("cases/<int:pk>/files/<str:key>/", views.case_file, name="case_file"),
    path(
        "cases/<int:pk>/artifacts/<str:key>/", views.artifact_download, name="artifact"
    ),
    path("jobs/<int:pk>/", views.job_status, name="job_status"),
    path("jobs/<int:pk>/cancel/", views.job_cancel, name="job_cancel"),
]
