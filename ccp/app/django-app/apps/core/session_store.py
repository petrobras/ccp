"""Redis-backed ephemeral session store.

This module is a thin wrapper around Django's cache framework, which
Unit 1's ``settings.py`` points at ``django_redis``. If Redis is
unavailable (e.g. during unit tests on a workstation) the cache is
expected to fall back to the locmem backend - this module tolerates
either one.

The public API mirrors the three operations the old Streamlit code
performed against ``st.session_state``: get, set, and clear.
"""

from __future__ import annotations

from typing import Any

_SESSION_KEY_PREFIX = "ccp:session:"
_DEFAULT_TIMEOUT = 60 * 60 * 24  # 24 hours


def _key(session_id: str) -> str:
    """Return the namespaced cache key for ``session_id``."""
    return f"{_SESSION_KEY_PREFIX}{session_id}"


def _cache():
    """Return Django's default cache, or an in-memory fallback.

    The import is performed lazily so this module can be imported by
    tooling that has not yet configured Django settings.
    """
    try:
        from django.core.cache import cache

        return cache
    except Exception:
        return _LocalCache.instance()


class _LocalCache:
    """Minimal locmem-style fallback used when Django is unavailable."""

    _singleton: "_LocalCache | None" = None

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    @classmethod
    def instance(cls) -> "_LocalCache":
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value, timeout=None):  # noqa: ARG002
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)


def get_session(session_id: str) -> dict:
    """Return the state dict stored for ``session_id``.

    Parameters
    ----------
    session_id : str
        Opaque identifier (usually Django's session key).

    Returns
    -------
    dict
        The stored state, or an empty dict when nothing has been set.
    """
    return _cache().get(_key(session_id)) or {}


def set_session(session_id: str, state: dict) -> None:
    """Store ``state`` under ``session_id`` in the cache.

    Parameters
    ----------
    session_id : str
        Opaque identifier.
    state : dict
        Serialisable session payload.
    """
    _cache().set(_key(session_id), state, timeout=_DEFAULT_TIMEOUT)


def clear_session(session_id: str) -> None:
    """Remove the entry for ``session_id`` from the cache.

    Parameters
    ----------
    session_id : str
        Opaque identifier.
    """
    _cache().delete(_key(session_id))
