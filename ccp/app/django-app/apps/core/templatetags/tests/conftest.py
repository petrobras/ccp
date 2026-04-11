"""Minimal Django configuration so Unit 4 templatetag tests can run in isolation.

Unit 1 owns ``ccp_web/settings.py``; this conftest only wires up
enough of Django to exercise the template engine and template tags
owned by Unit 4, without depending on other units.
"""

from __future__ import annotations

import os
from pathlib import Path

import django
from django.conf import settings

APP_DIR = Path(__file__).resolve().parents[2]  # apps/core/
TEMPLATES_DIR = APP_DIR / "templates"


def pytest_configure(config):  # noqa: D401 - pytest hook
    """Configure a minimal Django settings module for the test run."""
    if settings.configured:
        return

    settings.configure(
        DEBUG=True,
        DATABASES={},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "apps.core",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [str(TEMPLATES_DIR)],
                "APP_DIRS": True,
                "OPTIONS": {
                    "builtins": ["apps.core.templatetags.ccp_tags"],
                },
            },
        ],
        SECRET_KEY="test-secret",
        USE_TZ=True,
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "")
    django.setup()
