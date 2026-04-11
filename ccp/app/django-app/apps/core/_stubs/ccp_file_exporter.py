"""Exporter stub for .ccp archive files.

# STUB: replaced by Unit 3 (apps.core.storage.ccp_file_exporter) at merge time.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any


def export_ccp_file(state: dict[str, Any]) -> bytes:
    """Serialize a session state dictionary into a .ccp archive.

    Parameters
    ----------
    state : dict
        Session state dictionary to archive.

    Returns
    -------
    bytes
        Bytes of a ZIP archive containing ``session_state.json``.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        serializable = {k: v for k, v in state.items() if _json_safe(v)}
        zf.writestr("session_state.json", json.dumps(serializable, default=str))
    return buf.getvalue()


def _json_safe(value: Any) -> bool:
    try:
        json.dumps(value, default=str)
    except (TypeError, ValueError):
        return False
    return True
