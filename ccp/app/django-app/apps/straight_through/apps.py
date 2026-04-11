"""AppConfig for the straight-through compressor Django app."""

from django.apps import AppConfig


class StraightThroughConfig(AppConfig):
    """Register :mod:`apps.straight_through` with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.straight_through"
    label = "straight_through"
    verbose_name = "Straight-Through Compressor"
