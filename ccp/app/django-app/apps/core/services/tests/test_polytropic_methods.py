"""Smoke tests for :mod:`apps.core.services.polytropic_methods`."""

import pytest

from apps.core.services import polytropic_methods as pm


def test_mapping_contains_expected_labels():
    mapping = pm.get_polytropic_methods()
    assert mapping["Sandberg-Colby"] == "sandberg_colby"
    assert mapping["Schultz"] == "schultz"
    assert len(mapping) == 5


def test_resolve_known_label():
    assert pm.resolve("Huntington") == "huntington"


def test_resolve_unknown_label_raises():
    with pytest.raises(KeyError):
        pm.resolve("does-not-exist")


def test_get_polytropic_methods_returns_copy():
    a = pm.get_polytropic_methods()
    a["Schultz"] = "mutated"
    assert pm.POLYTROPIC_METHODS["Schultz"] == "schultz"
