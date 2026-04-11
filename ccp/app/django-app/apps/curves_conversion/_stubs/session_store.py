# STUB: replaced by Unit 3 at merge time
"""In-process session store fallback.

Uses Django's cache backend so behaviour matches the Redis-backed store once
Unit 3 lands. Values are pickled through the cache layer.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache

_PREFIX = "ccp.session."


def get_session(session_id: str) -> dict[str, Any]:
    """Return the session dict associated with *session_id*.

    Parameters
    ----------
    session_id : str
        Unique session identifier, typically ``request.session.session_key``.

    Returns
    -------
    dict
        Previously stored state, or an empty dict if none exists.
    """
    return cache.get(_PREFIX + session_id, {}) or {}


def set_session(session_id: str, state: dict[str, Any]) -> None:
    """Persist *state* for *session_id*.

    Parameters
    ----------
    session_id : str
        Unique session identifier.
    state : dict
        Arbitrary picklable dict to persist.
    """
    cache.set(_PREFIX + session_id, state, timeout=24 * 3600)


def clear_session(session_id: str) -> None:
    """Drop any state associated with *session_id*."""
    cache.delete(_PREFIX + session_id)
