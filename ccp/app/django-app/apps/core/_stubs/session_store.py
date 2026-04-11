"""Session store stub.

# STUB: replaced by Unit 3 (apps.core.session_store) at merge time. This
# stub uses an in-process dictionary so Unit 12 views can be exercised
# without Redis running.
"""

from __future__ import annotations

import uuid
from typing import Any

_SESSIONS: dict[str, dict[str, Any]] = {}


def new_session_id() -> str:
    """Return a fresh random session identifier."""
    return uuid.uuid4().hex


def get_session(session_id: str) -> dict[str, Any]:
    """Return the state dict for ``session_id`` or an empty dict."""
    return dict(_SESSIONS.get(session_id, {}))


def set_session(session_id: str, state: dict[str, Any]) -> None:
    """Persist ``state`` under ``session_id``."""
    _SESSIONS[session_id] = state


def clear_session(session_id: str) -> None:
    """Remove ``session_id`` from the store."""
    _SESSIONS.pop(session_id, None)
