# STUB: replaced by Unit 3 at merge time
"""Minimal exporter that writes the curves conversion state to a ``.ccp`` archive."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

import ccp
import toml


def export_ccp_file(state: dict[str, Any]) -> bytes:
    """Serialise *state* into a ``.ccp`` ZIP archive.

    Parameters
    ----------
    state : dict
        Session state dict as produced by the curves conversion views.

    Returns
    -------
    bytes
        Bytes of a ZIP archive containing ``session_state.json``,
        ``ccp.version``, curve CSVs, and TOML-serialised impellers.
    """
    buffer = io.BytesIO()
    cleaned: dict[str, Any] = dict(state)
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ccp.version", ccp.__version__)
        for key, value in list(cleaned.items()):
            if isinstance(value, ccp.Impeller):
                if key in {"original_impeller", "converted_impeller"}:
                    archive.writestr(f"{key}.toml", toml.dumps(value._dict_to_save()))
                cleaned.pop(key)
            elif (
                key.startswith("curves_file_")
                and isinstance(value, dict)
                and "name" in value
                and "content" in value
            ):
                archive.writestr(value["name"], value["content"])
                cleaned.pop(key)
        cleaned["app_type"] = "curves_conversion"
        archive.writestr("session_state.json", json.dumps(cleaned, default=str))
    return buffer.getvalue()
