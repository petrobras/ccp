"""Importer for ``.ccp`` ZIP archives.

Returns a plain dict shaped like :attr:`apps.core.models.Session.state`.
Live ccp objects are rehydrated when possible; any non-JSON payload
is preserved verbatim under a dedicated ``_archive`` key so the
exporter can reproduce a byte-compatible ZIP on the way back out.
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any

import toml

import ccp
from ccp.compressor import BackToBack, StraightThrough

logger = logging.getLogger(__name__)

# Reserved key used to stash the original archive members verbatim so
# round-tripping survives version-migrated or partially-rehydrated TOML.
ARCHIVE_KEY = "_archive"

_EXPLICIT_ALIASES = {
    "impeller_conversion": "curves_conversion",
    "online_monitoring": "online_monitoring",
    "performance_evaluation": "performance_evaluation",
    "curves_conversion": "curves_conversion",
}


def _detect_app_type(session_state: dict, members: list[str]) -> str:
    """Best-effort detection of which page produced ``session_state``.

    Structural signals (archive members, sentinel keys) win over
    the ``app_type`` field because some historical example archives
    ship that field set incorrectly.
    """
    explicit = session_state.get("app_type")
    if explicit in _EXPLICIT_ALIASES:
        return _EXPLICIT_ALIASES[explicit]

    if any(
        name == "evaluation.zip" or name.startswith("impeller_case_")
        for name in members
    ):
        return "performance_evaluation"

    if any(name.startswith("back_to_back") for name in members) or any(
        "_section_1_" in k or "_section_2_" in k for k in session_state
    ):
        return "back_to_back"

    if any(name.startswith("straight_through") for name in members):
        return "straight_through"

    if explicit in {"straight_through", "back_to_back"}:
        return explicit
    if "flow_point_guarantee" in session_state:
        return "straight_through"
    if "original_impeller" in session_state or "converted_impeller" in session_state:
        return "curves_conversion"
    return "unknown"


def _load_toml_object(app_type: str, name: str, text: str) -> Any:
    """Rehydrate a TOML member into a ccp library object.

    Unknown or unrecognised documents fall back to the parsed dict,
    which is still JSON-serialisable and useful to callers.
    """
    buf = io.StringIO(text)
    try:
        if app_type == "straight_through":
            return StraightThrough.load(buf)
        if app_type == "back_to_back":
            return BackToBack.load(buf)
        if name.startswith(("impeller", "original_impeller", "converted_impeller")):
            return ccp.Impeller.load(buf)
    except Exception as exc:  # pragma: no cover - tolerant of older files
        logger.warning("Failed to rehydrate %s as ccp object: %s", name, exc)
    try:
        return toml.loads(text)
    except Exception:  # pragma: no cover - degenerate TOML
        return text


def load_ccp_file(fp) -> dict:
    """Load a ``.ccp`` archive into a session-state dict.

    Parameters
    ----------
    fp : file-like or str or pathlib.Path
        Anything :class:`zipfile.ZipFile` accepts.

    Returns
    -------
    dict
        A dictionary shaped like :attr:`apps.core.models.Session.state`.
        Keys:

        ``session_state``
            The parsed ``session_state.json`` contents.
        ``app_type``
            Inferred page type.
        ``ccp_version``
            ``ccp.version`` content, or ``"0.3.5"`` for legacy files.
        ``objects``
            Mapping of archive-member-stem to the rehydrated ccp
            object (e.g. ``StraightThrough``) or parsed TOML dict.
        ``_archive``
            Mapping of archive-member-name to raw bytes, used by the
            exporter to rebuild the ZIP byte-for-byte.
    """
    with zipfile.ZipFile(fp) as archive:
        members = archive.namelist()

        try:
            version = archive.read("ccp.version").decode("utf-8")
        except KeyError:
            version = "0.3.5"

        session_state: dict = {}
        for name in members:
            if name.endswith(".json"):
                session_state = json.loads(archive.read(name))
                break

        app_type = _detect_app_type(session_state, members)

        objects: dict[str, Any] = {}
        raw_members: dict[str, bytes] = {}
        for name in members:
            data = archive.read(name)
            raw_members[name] = data
            if name == "ccp.version" or name.endswith(".json"):
                continue
            stem = name.rsplit(".", 1)[0]
            if name.endswith(".toml"):
                objects[stem] = _load_toml_object(app_type, stem, data.decode("utf-8"))
            elif name.endswith(".csv"):
                objects[stem] = {"name": name, "content": data}
            elif name.endswith(".png"):
                objects[stem] = data

    return {
        "session_state": session_state,
        "app_type": app_type,
        "ccp_version": version,
        "objects": objects,
        ARCHIVE_KEY: raw_members,
    }
