"""Exporter for ``.ccp`` ZIP archives.

Symmetric counterpart to :mod:`apps.core.storage.ccp_file_importer`.
Given a state dict (either the one produced by
:func:`apps.core.storage.ccp_file_importer.load_ccp_file` or a fresh
one assembled by a view), write out a byte-equivalent ``.ccp`` file.

Backward compatibility is a hard requirement: an existing
``example_*.ccp`` file must survive a ``load -> export -> load``
round-trip without losing any archive member.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import toml

import ccp

from apps.core.storage.ccp_file_importer import ARCHIVE_KEY


def _coerce_png(value: Any) -> bytes | None:
    """Return ``value`` as PNG bytes when possible."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return None


def _encode_ccp_object(value: Any) -> str | None:
    """TOML-encode a ccp library object, or return ``None``."""
    if hasattr(value, "_dict_to_save"):
        return toml.dumps(value._dict_to_save())
    return None


def export_ccp_file(state: dict) -> bytes:
    """Serialise a state dict to ``.ccp`` archive bytes.

    Parameters
    ----------
    state : dict
        Either the dict returned by :func:`load_ccp_file` (with the
        ``_archive`` key present) or a freshly-assembled one with
        ``session_state`` / ``objects`` / ``ccp_version`` keys.

    Returns
    -------
    bytes
        ZIP archive contents ready to be written to disk or sent in an
        HTTP response.
    """
    buffer = io.BytesIO()

    archive_members: dict[str, bytes] = dict(state.get(ARCHIVE_KEY, {}) or {})

    session_state = state.get("session_state")
    if session_state is not None:
        archive_members["session_state.json"] = json.dumps(session_state).encode(
            "utf-8"
        )

    version = state.get("ccp_version") or ccp.__version__
    archive_members["ccp.version"] = version.encode("utf-8")

    for stem, value in (state.get("objects") or {}).items():
        toml_text = _encode_ccp_object(value)
        if toml_text is not None:
            archive_members[f"{stem}.toml"] = toml_text.encode("utf-8")
            continue
        png = _coerce_png(value)
        if png is not None and stem.startswith("fig"):
            archive_members[f"{stem}.png"] = png
            continue
        if isinstance(value, dict) and "content" in value and "name" in value:
            archive_members[value["name"]] = value["content"]

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in archive_members.items():
            zf.writestr(name, data)

    return buffer.getvalue()
