from django.urls import path

from . import views

app_name = "curves"

urlpatterns = [
    path("<int:pk>/", views.case_view, name="case"),
    path("<int:pk>/load/<str:letter>/", views.load_case, name="load"),
    path("<int:pk>/convert/", views.convert, name="convert"),
    path("<int:pk>/results/", views.results, name="results"),
    path("<int:pk>/plots/<str:prefix>/", views.plots, name="plots"),
]
