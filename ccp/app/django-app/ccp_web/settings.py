"""Minimal Django settings for Unit 12 local verification.

# STUB: replaced by Unit 1 at merge time with full MongoEngine + Redis config.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "unit12-dev-secret-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "ccp_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

# Max upload size (bytes) mirroring Streamlit's default of 200 MB.
CCP_MAX_UPLOAD_SIZE = 200 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = CCP_MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = CCP_MAX_UPLOAD_SIZE
