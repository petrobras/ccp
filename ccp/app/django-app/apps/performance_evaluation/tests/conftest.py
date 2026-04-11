"""Isolated pytest bootstrap for the performance evaluation Django app.

Mirrors ``apps/straight_through/tests/conftest.py`` so this worker can
run its own tests without Unit 1's ``ccp_web`` project package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django
from django.conf import settings

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-secret",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF="apps.performance_evaluation.tests.urls",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "apps.performance_evaluation.tests",
        ],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": True,
                "DIRS": [
                    Path(__file__).resolve().parent / "templates",
                    Path(__file__).resolve().parents[1] / "templates",
                ],
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                    ],
                },
            }
        ],
        SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
        USE_TZ=True,
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "")
    django.setup()
