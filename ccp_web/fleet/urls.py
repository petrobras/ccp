from django.urls import path

from . import views

app_name = "fleet"

urlpatterns = [
    path("<int:pk>/", views.case_view, name="case"),
    path("<int:pk>/members/", views.members, name="members"),
    path("<int:pk>/run/", views.run, name="run"),
    path("<int:pk>/results/", views.results, name="results"),
]
