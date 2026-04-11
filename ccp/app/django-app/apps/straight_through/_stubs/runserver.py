# STUB: replaced by Unit 1 at merge time
"""Stand-alone ``runserver`` entry point used for in-isolation smoke testing.

Usage
-----
``uv run python -m apps.straight_through._stubs.runserver 0.0.0.0:8000``

Configures Django with a minimal in-process settings object and mounts
:mod:`apps.straight_through.urls` under ``/straight-through/``.
"""

from __future__ import annotations

import sys

import django
from django.conf import settings


def main() -> None:
    """Entry point that configures settings and delegates to ``runserver``."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY="dev",
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
    django.setup()
    from django.core.management import execute_from_command_line

    argv = ["manage.py", "runserver", *sys.argv[1:]]
    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
