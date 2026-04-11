"""Unit tests for :mod:`apps.curves_conversion.services`.

The tests exercise the real ``ccp`` library end-to-end, loading the example
``curves-conversion-example.ccp`` archive checked into ``ccp/app/``.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from apps.curves_conversion.services import (
    CurveFile,
    extract_curve_name,
    resolve_flow_v_unit,
    run_conversion,
)

EXAMPLE_CCP = Path(__file__).resolve().parents[4] / "curves-conversion-example.ccp"


def _load_example_csvs() -> list[CurveFile]:
    files: list[CurveFile] = []
    with zipfile.ZipFile(EXAMPLE_CCP) as archive:
        for name in archive.namelist():
            if name.endswith(".csv"):
                files.append(CurveFile(name=name, content=archive.read(name)))
    return files


def test_extract_curve_name_strips_known_suffixes():
    assert extract_curve_name("normal-head.csv") == "normal"
    assert extract_curve_name("pump-eff.csv") == "pump"
    assert extract_curve_name("no_suffix.csv") == "no_suffix"


def test_resolve_flow_v_unit_defaults_to_cubic_metres_per_hour():
    assert resolve_flow_v_unit("kg/h") == "m³/h"
    assert resolve_flow_v_unit("m³/min") == "m³/min"


@pytest.mark.skipif(not EXAMPLE_CCP.exists(), reason="example .ccp missing")
def test_run_conversion_with_example_curves(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "tests",
        }
    }
    curves = _load_example_csvs()
    assert curves, "example .ccp should contain CSV curves"
    gas = {
        "methane": 92.11,
        "ethane": 4.94,
        "propane": 1.71,
        "ibutane": 0.24,
        "butane": 0.30,
        "ipentane": 0.04,
        "pentane": 0.03,
        "hexane": 0.01,
        "n2": 0.40,
        "co2": 0.22,
    }
    result = run_conversion(
        original_data={
            "pressure": 3876.0,
            "pressure_unit": "kPa",
            "temperature": 11.0,
            "temperature_unit": "degC",
            "gas_composition": gas,
        },
        converted_data={
            "pressure": 2000.0,
            "pressure_unit": "kPa",
            "temperature": 300.0,
            "temperature_unit": "degK",
            "gas_composition": {"co2": 1.0},
        },
        curves_files=curves,
        conversion_params={
            "find_method": "speed",
            "speed_option": "same",
            "loaded_flow_unit": "kg/h",
            "loaded_head_unit": "kJ/kg",
            "loaded_power_unit": "kW",
            "loaded_disch_p_unit": "bar",
            "loaded_disch_T_unit": "degK",
            "loaded_speed_unit": "rpm",
            "plot_flow_unit": "m³/h",
            "plot_head_unit": "kJ/kg",
            "plot_power_unit": "kW",
            "plot_disch_p_unit": "bar",
            "plot_disch_T_unit": "degK",
            "plot_speed_unit": "rpm",
            "operational_flow": None,
            "operational_speed": None,
        },
    )
    assert "original_impeller" in result
    assert "converted_impeller" in result
    assert "head" in result["original_figures"]
    assert "head" in result["converted_figures"]


def test_ccp_importer_reads_example_archive():
    from apps.curves_conversion._stubs.ccp_file_importer import load_ccp_file

    with EXAMPLE_CCP.open("rb") as handle:
        state = load_ccp_file(handle)
    assert state.get("app_type") == "curves_conversion"
    assert "original_impeller" in state
