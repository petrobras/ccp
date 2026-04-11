"""Django ``AppConfig`` for the curves conversion page."""

from django.apps import AppConfig


class CurvesConversionConfig(AppConfig):
    """Config for the curves conversion app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.curves_conversion"
    label = "curves_conversion"
    verbose_name = "Curves Conversion"
