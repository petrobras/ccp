"""PI passwords and AI API keys.

Secrets never go into model rows or ``.ccp`` files. Two mechanisms:

- *Remembered* secrets (desktop profile): the OS keyring, when a backend is
  available; environment variables ``CCP_PI_PASSWORD`` / ``CCP_AI_API_KEY``
  act as a default in every profile.
- *Hand-off* to a job: the view stashes the secret in the cache under the job
  id with a short timeout and the worker takes (reads and deletes) it.
"""

import logging
import os

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger("ccp_web.secrets")

SERVICE = "ccp"
NAMES = ("pi_password", "ai_api_key")
HANDOFF_TIMEOUT = 600


def _keyring():
    if settings.CCP_SECRETS_BACKEND != "keyring":
        return None
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring

        if isinstance(keyring.get_keyring(), FailKeyring):
            return None
        return keyring
    except Exception:  # no usable backend on this machine
        return None


def keyring_available():
    return _keyring() is not None


def remembered(name, user=None):
    kr = _keyring()
    if kr is not None:
        try:
            value = kr.get_password(SERVICE, name)
            if value:
                return value
        except Exception as exc:
            log.warning("Keyring read failed: %s", exc)
    return os.environ.get(f"CCP_{name.upper()}", "")


def remember(name, value, user=None):
    """Store a secret in the keyring; returns False when there is none."""
    kr = _keyring()
    if kr is None:
        return False
    try:
        if value:
            kr.set_password(SERVICE, name, value)
        else:
            try:
                kr.delete_password(SERVICE, name)
            except Exception:
                pass
        return True
    except Exception as exc:
        log.warning("Keyring write failed: %s", exc)
        return False


def _key(job_id, name):
    return f"ccp-secret:{job_id}:{name}"


def stash_for_job(job_id, name, value):
    if value:
        cache.set(_key(job_id, name), value, HANDOFF_TIMEOUT)


def take_for_job(job_id, name):
    key = _key(job_id, name)
    value = cache.get(key)
    if value is not None:
        cache.delete(key)
    return value or ""
