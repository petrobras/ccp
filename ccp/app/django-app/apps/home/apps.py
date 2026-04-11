"""AppConfig for the home landing page."""

from django.apps import AppConfig


class HomeConfig(AppConfig):
    """Django app config for :mod:`apps.home`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.home"
    label = "home"
