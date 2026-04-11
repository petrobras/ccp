"""Redis-backed monitoring state helpers.

Serialises the small bookkeeping variables (``monitoring_active`` flag,
accumulated results DataFrame, last fetch timestamp) used by the online
monitoring view. When Redis is not configured the helpers fall back to a
process-local dictionary so unit tests and ``manage.py check`` keep
working in isolation.
"""

from __future__ import annotations

import io
import json
import time
from typing import Any

import pandas as pd

try:  # pragma: no cover - exercised only when Django is installed
    from django.core.cache import cache as _django_cache
except Exception:  # pragma: no cover
    _django_cache = None


_PREFIX = "perfeval:mon:"
_LOCAL: dict[str, Any] = {}


def _key(session_id: str, field: str) -> str:
    """Return the namespaced cache key."""
    return f"{_PREFIX}{session_id}:{field}"


def _get(key: str) -> Any:
    if _django_cache is not None:
        return _django_cache.get(key)
    return _LOCAL.get(key)


def _set(key: str, value: Any, timeout: int | None = 3600) -> None:
    if _django_cache is not None:
        _django_cache.set(key, value, timeout=timeout)
    else:
        _LOCAL[key] = value


def _delete(key: str) -> None:
    if _django_cache is not None:
        _django_cache.delete(key)
    else:
        _LOCAL.pop(key, None)


def set_active(session_id: str, active: bool) -> None:
    """Flag monitoring as active/inactive for ``session_id``."""
    _set(_key(session_id, "active"), bool(active))


def is_active(session_id: str) -> bool:
    """Return ``True`` if monitoring is currently running."""
    return bool(_get(_key(session_id, "active")))


def set_last_fetch(session_id: str, ts: float | None = None) -> None:
    """Store the UNIX timestamp of the last successful fetch."""
    _set(_key(session_id, "last_fetch"), float(ts if ts is not None else time.time()))


def get_last_fetch(session_id: str) -> float | None:
    """Return the UNIX timestamp of the last successful fetch, if any."""
    value = _get(_key(session_id, "last_fetch"))
    return float(value) if value is not None else None


def set_accumulated_results(session_id: str, df: pd.DataFrame | None) -> None:
    """Serialise ``df`` (JSON orient=split) and store it in cache."""
    if df is None or df.empty:
        _delete(_key(session_id, "accumulated"))
        return
    buffer = io.StringIO()
    df.to_json(buffer, orient="split", date_format="iso", default_handler=str)
    _set(_key(session_id, "accumulated"), buffer.getvalue())


def get_accumulated_results(session_id: str) -> pd.DataFrame:
    """Return the accumulated monitoring DataFrame (empty if missing)."""
    raw = _get(_key(session_id, "accumulated"))
    if not raw:
        return pd.DataFrame()
    try:
        return pd.read_json(io.StringIO(raw), orient="split")
    except ValueError:
        return pd.DataFrame()


def append_accumulated_results(
    session_id: str,
    new_rows: pd.DataFrame,
    *,
    keep: int = 5,
) -> pd.DataFrame:
    """Append ``new_rows`` to the accumulated DataFrame (keeping ``keep`` tail)."""
    existing = get_accumulated_results(session_id)
    if new_rows is None or new_rows.empty:
        return existing
    combined = pd.concat([existing, new_rows]) if not existing.empty else new_rows
    trimmed = combined.tail(keep)
    set_accumulated_results(session_id, trimmed)
    return trimmed


def clear(session_id: str) -> None:
    """Reset every monitoring key for ``session_id``."""
    for field in ("active", "last_fetch", "accumulated"):
        _delete(_key(session_id, field))


def snapshot(session_id: str) -> dict[str, Any]:
    """Return a JSON-serialisable snapshot of the current monitoring state."""
    return {
        "active": is_active(session_id),
        "last_fetch": get_last_fetch(session_id),
        "accumulated_rows": len(get_accumulated_results(session_id)),
    }


__all__ = [
    "append_accumulated_results",
    "clear",
    "get_accumulated_results",
    "get_last_fetch",
    "is_active",
    "set_accumulated_results",
    "set_active",
    "set_last_fetch",
    "snapshot",
]
