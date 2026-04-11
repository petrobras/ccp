"""Importer stub for .ccp archive files.

# STUB: replaced by Unit 3 (apps.core.storage.ccp_file_importer) at merge time.
"""

from __future__ import annotations

import json
import zipfile
from typing import IO, Any


def load_ccp_file(fp: IO[bytes]) -> dict[str, Any]:
    """Load a .ccp archive into a session state dictionary.

    Parameters
    ----------
    fp : file-like
        Binary file-like object pointing at a .ccp ZIP archive.

    Returns
    -------
    dict
        Session state dictionary. The stub implementation reads
        ``session_state.json`` from the archive when present, otherwise
        returns a dictionary listing the archive's file names.
    """
    fp.seek(0)
    state: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(fp) as zf:
            names = zf.namelist()
            state["_archive_files"] = names
            if "session_state.json" in names:
                with zf.open("session_state.json") as fh:
                    try:
                        state.update(json.load(fh))
                    except json.JSONDecodeError:
                        pass
    except zipfile.BadZipFile:
        state["_archive_files"] = []
    try:
        fp.seek(0)
    except Exception:
        pass
    return state
