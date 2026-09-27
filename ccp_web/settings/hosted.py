"""Hosted profile: multi-user service with allauth accounts and PostgreSQL."""

import os
from pathlib import Path

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

SECRET_KEY = os.environ["CCP_SECRET_KEY"]
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("CCP_ALLOWED_HOSTS", "").split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CCP_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("CCP_DB_NAME", "ccp"),
        "USER": os.environ.get("CCP_DB_USER", "ccp"),
        "PASSWORD": os.environ.get("CCP_DB_PASSWORD", ""),
        "HOST": os.environ.get("CCP_DB_HOST", "localhost"),
        "PORT": os.environ.get("CCP_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

MEDIA_ROOT = Path(os.environ.get("CCP_MEDIA_ROOT", "/var/lib/ccp/media"))
STATIC_ROOT = Path(os.environ.get("CCP_STATIC_ROOT", "/var/lib/ccp/static"))
WHITENOISE_USE_FINDERS = False

INSTALLED_APPS = INSTALLED_APPS + [
    "allauth",
    "allauth.account",
]

MIDDLEWARE = MIDDLEWARE + [
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = os.environ.get("CCP_EMAIL_VERIFICATION", "optional")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "ccp_cache",
    }
}

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CCP_PROFILE = "hosted"
CCP_MULTI_USER = True
CCP_SECRETS_BACKEND = "cache"
