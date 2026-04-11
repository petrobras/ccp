# STUB: replaced by Unit 3 at merge time
"""Fallback .ccp ZIP import/export used until Unit 3 lands."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any, BinaryIO


def load_ccp_file(fp: BinaryIO) -> dict[str, Any]:
    """Extract a state dict from a ``.ccp`` archive.

    Parameters
    ----------
    fp : file-like
        Binary stream positioned at the start of the archive.

    Returns
    -------
    dict
        Session state with any PNG curves stored as raw bytes under keys
        ``fig_<curve>``. Unknown TOML payloads are returned as strings so the
        real importer (Unit 3) can reinstate them.
    """
    state: dict[str, Any] = {}
    with zipfile.ZipFile(fp) as archive:
        for name in archive.namelist():
            data = archive.read(name)
            stem = name.rsplit(".", 1)[0]
            if name.endswith(".json"):
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    state.update(payload)
            elif name.endswith(".png"):
                state[stem] = data
            elif name.endswith(".toml"):
                state[f"{stem}_toml"] = data.decode("utf-8")
    return state


def export_ccp_file(state: dict[str, Any]) -> bytes:
    """Pack a state dict into a ``.ccp`` archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        json_payload = {
            k: v
            for k, v in state.items()
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None
        }
        archive.writestr("session_state.json", json.dumps(json_payload))
        for key, value in state.items():
            if isinstance(value, bytes) and key.startswith("fig_"):
                archive.writestr(f"{key}.png", value)
    return buf.getvalue()
