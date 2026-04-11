# STUB: replaced by Unit 3 (apps.core.session_store) at merge time.
"""In-memory session store used until the Redis-backed one lands."""

_STORE: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """Return session state dict for ``session_id`` (empty if unknown)."""
    return _STORE.setdefault(session_id, {})


def set_session(session_id: str, state: dict) -> None:
    """Persist ``state`` for ``session_id``."""
    _STORE[session_id] = state


def clear_session(session_id: str) -> None:
    """Drop ``session_id`` from the store."""
    _STORE.pop(session_id, None)
