"""AppConfig for :mod:`apps.integrations`."""

from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    """Register :mod:`apps.integrations` with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    label = "integrations"
    verbose_name = "Optional Integrations"
