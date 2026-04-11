"""Local Django configuration for :mod:`apps.reports` tests.

Unit 10 is developed in isolation: the project-level ``ccp_web`` settings
module owned by Unit 1 may not exist yet in this worktree. This conftest
provides a minimal, self-contained settings module so the reports app can
be imported and exercised via ``pytest`` without any cross-unit wiring.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import django
from django.conf import settings

REPORTS_APP_DIR = Path(__file__).resolve().parents[1]
DJANGO_APP_ROOT = REPORTS_APP_DIR.parents[1]


def _ensure_django_configured() -> None:
    if settings.configured:
        return
    if str(DJANGO_APP_ROOT) not in sys.path:
        sys.path.insert(0, str(DJANGO_APP_ROOT))
    settings.configure(
        DEBUG=True,
        SECRET_KEY="reports-tests-secret",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF="apps.reports.tests.urls",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django.contrib.staticfiles",
            "apps.reports",
        ],
        MIDDLEWARE=[],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {"context_processors": []},
            }
        ],
        STATIC_URL="/static/",
        USE_TZ=True,
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "")
    django.setup()


_ensure_django_configured()
