"""Django ``AppConfig`` for the back-to-back compressor page."""

from django.apps import AppConfig


class BackToBackConfig(AppConfig):
    """Configuration for the back-to-back Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.back_to_back"
    label = "back_to_back"
    verbose_name = "Back-to-Back Compressor"
