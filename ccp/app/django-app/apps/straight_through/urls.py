"""URL routes for the straight-through compressor page."""

from django.urls import path

from apps.straight_through import views

app_name = "straight_through"

urlpatterns = [
    path("", views.index, name="index"),
    path("compute/", views.compute, name="compute"),
    path("upload-curve/", views.upload_curve, name="upload_curve"),
    path("save.ccp", views.save_ccp, name="save_ccp"),
    path("load.ccp", views.load_ccp, name="load_ccp"),
]
