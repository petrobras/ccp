"""Smoke tests for :mod:`apps.core.services.unit_helpers`."""

import math

from apps.core.services import unit_helpers as uh


def test_flow_units_contains_mass_and_volumetric():
    assert "kg/s" in uh.FLOW_UNITS
    assert "m³/h" in uh.FLOW_UNITS


def test_pressure_and_temperature_units_present():
    assert "bar" in uh.PRESSURE_UNITS
    assert "degK" in uh.TEMPERATURE_UNITS
    assert "kJ/kg" in uh.HEAD_UNITS


def test_convert_bar_to_pa():
    assert math.isclose(uh.convert(1.0, "bar", "Pa"), 1e5)


def test_convert_celsius_to_kelvin():
    assert math.isclose(uh.convert(0.0, "degC", "degK"), 273.15)


def test_convert_returns_float():
    value = uh.convert(10.0, "kg/s", "kg/h")
    assert isinstance(value, float)
    assert math.isclose(value, 36000.0)
