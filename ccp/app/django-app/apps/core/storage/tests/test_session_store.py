"""Tests for the Redis-backed session store with locmem fallback."""

from __future__ import annotations

from apps.core import session_store


def test_set_get_clear_roundtrip():
    """set_session / get_session / clear_session round-trip correctly."""
    sid = "unit-test-session"
    session_store.clear_session(sid)
    assert session_store.get_session(sid) == {}

    payload = {"foo": "bar", "n": 3}
    session_store.set_session(sid, payload)
    assert session_store.get_session(sid) == payload

    session_store.clear_session(sid)
    assert session_store.get_session(sid) == {}
