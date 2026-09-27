"""Test profile.

``CCP_TEST_MULTI_USER=1`` switches the owner model to the hosted behaviour
(no auto-login) so the suite can run under both profiles.
"""

import os
import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

MULTI_USER = os.environ.get("CCP_TEST_MULTI_USER", "").lower() in {"1", "true"}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="ccp-web-test-media-"))

TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
        "QUEUES": ["default", "monitoring"],
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if MULTI_USER:
    INSTALLED_APPS = INSTALLED_APPS + ["allauth", "allauth.account"]
    MIDDLEWARE = MIDDLEWARE + [
        "allauth.account.middleware.AccountMiddleware",
        "django.contrib.auth.middleware.LoginRequiredMiddleware",
    ]
    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
        "allauth.account.auth_backends.AuthenticationBackend",
    ]
    LOGIN_URL = "account_login"
    ACCOUNT_LOGIN_METHODS = {"email"}
    ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
    ACCOUNT_EMAIL_VERIFICATION = "none"
    CCP_PROFILE = "hosted"
    CCP_MULTI_USER = True
else:
    MIDDLEWARE = MIDDLEWARE + ["ccp_web.core.middleware.LocalUserMiddleware"]
    CCP_PROFILE = "desktop"
    CCP_MULTI_USER = False

CCP_SECRETS_BACKEND = "session"
