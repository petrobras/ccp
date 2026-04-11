# STUB: replaced by Unit 3 at merge time
"""In-process session-store fallback used until Unit 3 lands."""

from __future__ import annotations

from typing import Any

_STORE: dict[str, dict[str, Any]] = {}


def get_session(session_id: str) -> dict[str, Any]:
    """Return the mutable state dict for *session_id*."""
    return _STORE.setdefault(session_id, {})


def set_session(session_id: str, state: dict[str, Any]) -> None:
    """Replace the stored state for *session_id*."""
    _STORE[session_id] = dict(state)


def clear_session(session_id: str) -> None:
    """Remove *session_id* from the store if present."""
    _STORE.pop(session_id, None)
