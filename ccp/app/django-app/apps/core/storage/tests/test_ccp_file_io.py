"""Round-trip tests for the ``.ccp`` importer/exporter pair.

These tests load every ``example_*.ccp`` archive that ships with the
Streamlit app, assert the loader returns a sensibly shaped dict, and
then verify the exporter can reproduce a valid ZIP containing the
same member set.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from apps.core.storage.ccp_file_exporter import export_ccp_file
from apps.core.storage.ccp_file_importer import ARCHIVE_KEY, load_ccp_file

EXAMPLES_DIR = Path(__file__).resolve().parents[5]

EXAMPLE_FILES = [
    ("example_straight.ccp", "straight_through"),
    ("example_back_to_back.ccp", "back_to_back"),
    ("curves-conversion-example.ccp", "curves_conversion"),
    ("example_evaluation_pi.ccp", "performance_evaluation"),
    ("example_online.ccp", "online_monitoring"),
    ("example_online_pi.ccp", "online_monitoring"),
]


@pytest.mark.parametrize("filename,expected_app_type", EXAMPLE_FILES)
def test_load_example(filename, expected_app_type):
    """Each example file loads and yields a populated state dict."""
    path = EXAMPLES_DIR / filename
    if not path.exists():
        pytest.skip(f"example fixture missing: {path}")

    with open(path, "rb") as fp:
        state = load_ccp_file(fp)

    assert set(state) >= {
        "session_state",
        "app_type",
        "ccp_version",
        "objects",
        ARCHIVE_KEY,
    }
    assert state["session_state"], "session_state.json must be non-empty"
    assert state["app_type"] == expected_app_type
    assert state["ccp_version"]
    assert state[ARCHIVE_KEY], "archive members must be captured"


@pytest.mark.parametrize("filename,_expected", EXAMPLE_FILES)
def test_round_trip(filename, _expected):
    """``export(load(file))`` produces a ZIP with the same member names."""
    path = EXAMPLES_DIR / filename
    if not path.exists():
        pytest.skip(f"example fixture missing: {path}")

    with open(path, "rb") as fp:
        state = load_ccp_file(fp)

    raw = export_ccp_file(state)
    assert isinstance(raw, bytes) and raw

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        exported_members = set(zf.namelist())
        # ccp.version and session_state.json are mandatory.
        assert "ccp.version" in exported_members
        assert "session_state.json" in exported_members

    with zipfile.ZipFile(path) as zf:
        original_members = set(zf.namelist())

    # Every member from the source archive must be preserved on export.
    missing = original_members - exported_members
    assert not missing, f"exporter dropped members: {missing}"


def test_export_from_minimal_state():
    """A freshly-assembled state dict (no ``_archive``) still exports."""
    state = {
        "session_state": {"app_type": "straight_through", "hello": "world"},
        "ccp_version": "0.0.test",
        "objects": {},
    }
    raw = export_ccp_file(state)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert zf.read("ccp.version").decode("utf-8") == "0.0.test"
        loaded = zf.read("session_state.json")
        assert b"straight_through" in loaded
