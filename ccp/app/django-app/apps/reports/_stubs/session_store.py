# STUB: replaced by Unit 3 at merge time.
"""In-memory fallback for :mod:`apps.core.session_store`."""

from __future__ import annotations

_STORE: dict[str, dict] = {}


def get_session(session_id: str) -> dict | None:
    """Return the cached session state for ``session_id`` or ``None``."""
    return _STORE.get(session_id)


def set_session(session_id: str, state: dict) -> None:
    """Persist ``state`` under ``session_id`` in the in-memory store."""
    _STORE[session_id] = state


def clear_session(session_id: str) -> None:
    """Remove ``session_id`` from the in-memory store if present."""
    _STORE.pop(session_id, None)
