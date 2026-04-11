"""AppConfig for the reports Django app."""

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Register :mod:`apps.reports` with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    label = "reports"
    verbose_name = "CCP Reports"
