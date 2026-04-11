"""Smoke tests for :mod:`apps.core.services.gas_composition`."""

from apps.core.services import gas_composition as gc


def test_fluid_list_starts_with_placeholder():
    assert gc.FLUID_LIST[0] == ""
    assert any("methane" in name for name in gc.FLUID_LIST)


def test_default_composition_sums_to_one():
    comp = gc.default_composition()
    assert comp["methane"] == 1.0
    assert sum(comp.values()) == 1.0
    assert set(comp.keys()) == set(gc.DEFAULT_COMPONENTS[:6])


def test_get_gas_composition_from_table():
    table = {
        "gas_0": {
            "name": "main_gas",
            "component_0": "methane",
            "molar_fraction_0": "0.9",
            "component_1": "ethane",
            "molar_fraction_1": "0.1",
            "component_2": "propane",
            "molar_fraction_2": "",
        }
    }
    result = gc.get_gas_composition("main_gas", table)
    assert result == {"methane": 0.9, "ethane": 0.1}


def test_get_gas_composition_missing_name_returns_empty():
    assert gc.get_gas_composition("nope", {}) == {}


def test_get_index_selected_gas():
    opts = ["", "methane", "ethane"]
    assert gc.get_index_selected_gas(opts, "ethane") == 2
    assert gc.get_index_selected_gas(opts, "missing") == 0
