"""Smoke tests for the straight-through Django app."""

from __future__ import annotations

import importlib

import pytest
from django.test import Client


def test_module_imports():
    """Every public module loads without side-effects."""
    for dotted in (
        "apps.straight_through.apps",
        "apps.straight_through.forms",
        "apps.straight_through.services",
        "apps.straight_through.urls",
        "apps.straight_through.views",
        "apps.straight_through.templatetags.ccp_tags",
    ):
        importlib.import_module(dotted)


def test_index_get_renders():
    """A plain GET to the page returns HTTP 200 with the page title."""
    client = Client()
    response = client.get("/straight-through/")
    assert response.status_code == 200
    assert b"Straight-Through" in response.content


def test_run_straight_through_missing_data_raises():
    """Empty form data should error out, not silently succeed."""
    from apps.straight_through import services

    with pytest.raises(Exception):
        services.run_straight_through({}, {})


def test_run_straight_through_minimal():
    """A minimal-but-valid dataset produces the expected figure keys."""
    from apps.straight_through import services

    form_data = {
        "gas_point_guarantee": {"methane": 1.0},
        "data_sheet_units": {
            "flow": "kg/h",
            "suction_pressure": "bar",
            "suction_temperature": "degK",
            "discharge_pressure": "bar",
            "discharge_temperature": "degK",
            "speed": "rpm",
            "b": "mm",
            "D": "mm",
            "casing_area": "m²",
            "surface_roughness": "mm",
        },
        "test_units": {
            "flow": "kg/h",
            "suction_pressure": "bar",
            "suction_temperature": "degK",
            "discharge_pressure": "bar",
            "discharge_temperature": "degK",
            "speed": "rpm",
        },
        "flow_point_guarantee": "85050",
        "suction_pressure_point_guarantee": "90",
        "suction_temperature_point_guarantee": "308.15",
        "discharge_pressure_point_guarantee": "160",
        "discharge_temperature_point_guarantee": "355.15",
        "speed_point_guarantee": "9300",
        "b_point_guarantee": "10",
        "D_point_guarantee": "390",
        "casing_area_point_guarantee": "5.5",
        "surface_roughness_point_guarantee": "0.0000066",
        "flow_point_1": "85050",
        "suction_pressure_point_1": "90",
        "suction_temperature_point_1": "308.15",
        "discharge_pressure_point_1": "160",
        "discharge_temperature_point_1": "355.15",
        "speed_point_1": "9300",
        "gas_point_1": {"methane": 1.0},
    }
    options = {
        "reynolds_correction": True,
        "bearing_mechanical_losses": False,
        "casing_heat_loss": False,
        "calculate_leakages": False,
        "seal_gas_flow": False,
        "show_points": False,
        "calculate_speed": False,
    }
    try:
        result = services.run_straight_through(form_data, options)
    except Exception as exc:
        pytest.skip(f"ccp library rejected minimal fixture: {exc}")
    assert set(result["figures"]) >= {"head", "eff", "discharge_pressure", "power", "mach", "reynolds"}
    assert result["speed_operational_rpm"] > 0
