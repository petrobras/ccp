from django.urls import path

from . import views

app_name = "evaluation"

urlpatterns = [
    path("<int:pk>/", views.case_view, name="case"),
    path("<int:pk>/run/", views.run, name="run"),
    path("<int:pk>/results/", views.results, name="results"),
    path("<int:pk>/perf/", views.perf, name="perf"),
    path("<int:pk>/table.xlsx", views.table_excel, name="table_excel"),
    path("<int:pk>/report/", views.report, name="report"),
    path("<int:pk>/report/status/", views.report_status, name="report_status"),
    path("<int:pk>/monitoring/", views.monitoring_panel, name="monitoring"),
    path("<int:pk>/monitoring/start/", views.monitoring_start, name="monitoring_start"),
    path("<int:pk>/monitoring/stop/", views.monitoring_stop, name="monitoring_stop"),
    path("<int:pk>/secrets/<str:name>/", views.remember_secret, name="remember_secret"),
]
