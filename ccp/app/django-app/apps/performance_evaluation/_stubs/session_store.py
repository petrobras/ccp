# STUB: replaced by Unit 3 at merge time
"""In-memory fallback for :mod:`apps.core.session_store`."""

from __future__ import annotations

from typing import Any

_STORE: dict[str, dict[str, Any]] = {}


def get_session(session_id: str) -> dict[str, Any]:
    """Return the state dict for ``session_id`` (empty if missing)."""
    return _STORE.setdefault(session_id, {})


def set_session(session_id: str, state: dict[str, Any]) -> None:
    """Persist ``state`` under ``session_id``."""
    _STORE[session_id] = state


def clear_session(session_id: str) -> None:
    """Drop all state for ``session_id``."""
    _STORE.pop(session_id, None)
