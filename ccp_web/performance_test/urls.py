from django.urls import path

from . import views

app_name = "performance_test"

urlpatterns = [
    path("<int:pk>/", views.case_view, name="case"),
    path("<int:pk>/calculate/", views.calculate, name="calculate"),
    path("<int:pk>/orifice/", views.orifice, name="orifice"),
    path("<int:pk>/results/", views.results, name="results"),
    path("<int:pk>/excel/<str:sec>/", views.excel, name="excel"),
]
