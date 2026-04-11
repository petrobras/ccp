"""Smoke tests for :mod:`apps.core.services.parameter_map`."""

import pytest

from apps.core.services import parameter_map as pmap


def test_guarantee_point_keys_present():
    assert "guarantee_point" in pmap.POINT_KEYS
    assert "test_point_6" in pmap.POINT_KEYS
    assert len(pmap.POINT_KEYS) == 7


def test_suction_pressure_entry_shape():
    entry = pmap.get_parameter("suction_pressure")
    assert entry["label"] == "Suction Pressure"
    assert "bar" in entry["units"]
    assert "default" in entry
    assert "help" in entry


def test_flow_has_help_text():
    entry = pmap.PARAMETERS["flow"]
    assert entry["help"] is not None
    assert "mass flow" in entry["help"]


def test_unknown_parameter_raises():
    with pytest.raises(KeyError):
        pmap.get_parameter("not_a_parameter")


def test_all_entries_have_required_keys():
    for key, entry in pmap.PARAMETERS.items():
        assert set(entry.keys()) == {"label", "units", "help", "default"}, key
        assert isinstance(entry["units"], list) and entry["units"], key
