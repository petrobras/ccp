# STUB: replaced by Unit 1 at merge time
"""Minimal AppConfig so Django can discover ``apps.core`` in isolation."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
