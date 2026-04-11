# STUB: replaced by Unit 3 (apps.core.storage.{ccp_file_importer,ccp_file_exporter}).
"""Minimal .ccp file importer/exporter used until Unit 3 lands."""

import io
import json
import zipfile


def load_ccp_file(fp) -> dict:
    """Return a state dict read from a .ccp ZIP archive."""
    state: dict = {}
    with zipfile.ZipFile(fp) as zf:
        for name in zf.namelist():
            if name.endswith(".json"):
                state.update(json.loads(zf.read(name)))
    state.setdefault("app_type", "performance_evaluation")
    return state


def export_ccp_file(state: dict) -> bytes:
    """Serialise ``state`` to a .ccp ZIP archive as bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("session_state.json", json.dumps(state, default=str))
    return buf.getvalue()
