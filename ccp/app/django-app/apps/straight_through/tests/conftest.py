"""Isolated pytest bootstrap for the straight-through Django app.

Configures a minimal in-memory Django settings object so the tests can run
without the Unit 1 project scaffolding (``ccp_web/settings.py``,
``manage.py``) being present in the worktree.
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
        ROOT_URLCONF="apps.straight_through.tests.urls",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.sessions",
            "apps.straight_through",
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
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "")
    django.setup()
