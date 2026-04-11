"""URL routes for the home landing page."""

from django.urls import path

from . import views

app_name = "home"

urlpatterns = [
    path("", views.index, name="index"),
]
