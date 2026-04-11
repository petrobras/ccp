# STUB: replaced by Unit 3 at merge time
"""Minimal importer for ``.ccp`` ZIP archives used by the curves conversion page."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any, BinaryIO

import ccp


def load_ccp_file(fp: BinaryIO) -> dict[str, Any]:
    """Load a ``.ccp`` archive into a state dict.

    Matches the behaviour of the Streamlit page's ``_load_curves_conversion``
    helper: JSON session state, plus original / converted impeller TOML files,
    plus any loose ``.csv`` curve files preserved under ``curves_file_<i>``.

    Parameters
    ----------
    fp : file-like
        Binary file-like object positioned at the start of a ``.ccp`` ZIP.

    Returns
    -------
    dict
        Session state dict with ``original_impeller`` / ``converted_impeller``
        keys populated as :class:`ccp.Impeller` instances when present.
    """
    state: dict[str, Any] = {}
    with zipfile.ZipFile(fp) as archive:
        names = archive.namelist()
        for name in names:
            if name.endswith(".json"):
                state = json.loads(archive.read(name))
                if state.get("app_type") != "curves_conversion":
                    state["app_type"] = "curves_conversion"
        csv_index = 1
        for name in names:
            if name.endswith(".csv"):
                state[f"curves_file_{csv_index}"] = {
                    "name": name,
                    "content": archive.read(name),
                }
                csv_index += 1
            elif name.endswith(".toml"):
                impeller_file = io.StringIO(archive.read(name).decode("utf-8"))
                if name.startswith("original_impeller"):
                    state["original_impeller"] = ccp.Impeller.load(impeller_file)
                elif name.startswith("converted_impeller"):
                    state["converted_impeller"] = ccp.Impeller.load(impeller_file)
    return state
