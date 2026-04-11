"""Tests for :mod:`apps.integrations.sentry`."""

from __future__ import annotations

import sys

from apps.integrations import sentry as sentry_mod


def test_imports_without_sentry_sdk(monkeypatch):
    """Module must remain importable when sentry_sdk is absent."""
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    import importlib

    reloaded = importlib.reload(sentry_mod)
    assert hasattr(reloaded, "init_sentry")


def test_init_sentry_noop_when_dsn_empty(monkeypatch):
    monkeypatch.delenv("CCP_STANDALONE", raising=False)
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    # Empty string forces no-op path.
    assert sentry_mod.init_sentry(dsn="") is None


def test_init_sentry_noop_when_standalone(monkeypatch):
    monkeypatch.setenv("CCP_STANDALONE", "1")
    assert sentry_mod.init_sentry(dsn="https://example/1") is None


def test_init_sentry_noop_when_sdk_missing(monkeypatch):
    monkeypatch.delenv("CCP_STANDALONE", raising=False)
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    # Should not raise even though sentry_sdk cannot be imported.
    assert sentry_mod.init_sentry(dsn="https://example/1") is None


def test_init_sentry_calls_sdk_when_available(monkeypatch):
    monkeypatch.delenv("CCP_STANDALONE", raising=False)

    calls = {}

    class _FakeSDK:
        @staticmethod
        def init(**kwargs):
            calls.update(kwargs)

    monkeypatch.setitem(sys.modules, "sentry_sdk", _FakeSDK)
    sentry_mod.init_sentry(dsn="https://example/1")
    assert calls.get("dsn") == "https://example/1"
    assert calls.get("traces_sample_rate") == 1.0
