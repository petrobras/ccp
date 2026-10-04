"""Desktop profile: one local user, SQLite and media in the user data dir."""

import os
from pathlib import Path

from platformdirs import user_data_dir

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE

DATA_DIR = Path(os.environ.get("CCP_DATA_DIR", user_data_dir("ccp", "ccp")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "ccp.sqlite3",
        # The web server and two task workers share the file.
        "OPTIONS": {
            "timeout": 30,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
        },
    }
}

MEDIA_ROOT = DATA_DIR / "media"

# Shared by the web server and the workers (secret hand-off to jobs).
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(mode=0o700, exist_ok=True)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(CACHE_DIR),
    }
}

MIDDLEWARE = MIDDLEWARE + ["ccp_web.core.middleware.LocalUserMiddleware"]

CCP_PROFILE = "desktop"
CCP_MULTI_USER = False
CCP_SECRETS_BACKEND = "keyring"
