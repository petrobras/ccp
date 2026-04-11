# STUB: Local test settings for running this unit in isolation.
# When Unit 1 lands ``ccp_web/settings.py`` replaces this harness at runtime.
"""Minimal Django settings so ``apps.curves_conversion`` can be tested alone."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

SECRET_KEY = "curves-conversion-test-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "apps.curves_conversion",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
]

ROOT_URLCONF = "apps.curves_conversion.tests.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "curves-conversion-tests",
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
STATIC_URL = "/static/"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
