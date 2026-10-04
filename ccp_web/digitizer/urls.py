from django.urls import path

from . import views

app_name = "digitizer"

urlpatterns = [
    path("<int:pk>/", views.case_view, name="case"),
    path("<int:pk>/digitize/", views.digitize, name="digitize"),
    path("<int:pk>/results/", views.results, name="results"),
    path("<int:pk>/plot/<str:plot_id>/", views.editor, name="editor"),
    path("<int:pk>/plot/<str:plot_id>/image.png", views.plot_image, name="image"),
    path("<int:pk>/plot/<str:plot_id>/save/", views.plot_save, name="save"),
    path("<int:pk>/plot/<str:plot_id>/reset/", views.plot_reset, name="reset"),
    path("<int:pk>/export.zip", views.export, name="export"),
    path("<int:pk>/to-conversion/", views.to_conversion, name="to_conversion"),
]
