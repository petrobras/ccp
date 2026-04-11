"""Smoke tests for shared UI partials owned by Unit 4."""

from __future__ import annotations

from django.template.loader import render_to_string


def test_expander_renders_title_and_body_id():
    html = render_to_string(
        "core/partials/expander.html",
        {"title": "Dados de Entrada", "body_id": "exp-inputs", "expanded": True},
    )
    assert "ccp-expander" in html
    assert "Dados de Entrada" in html
    assert 'id="exp-inputs"' in html
    assert "x-data" in html


def test_gas_selection_contains_rows_and_fluids():
    html = render_to_string(
        "core/partials/gas_selection.html",
        {
            "name_prefix": "test_gas",
            "composition": {"methane": 0.9, "ethane": 0.1},
            "fluid_list": ["methane", "ethane", "nitrogen"],
        },
    )
    assert "ccp-gas-selection" in html
    assert html.count("ccp-gas-row") == 6
    assert "methane" in html
    assert 'name="test_gas_component_1"' in html


def test_oil_inputs_has_alpine_state_and_defaults():
    html = render_to_string(
        "core/partials/oil_inputs.html",
        {
            "specific_heat_units": ["kJ/kg/degK", "J/kg/degK"],
            "density_units": ["kg/m³", "g/cm³"],
            "iso_options": ["VG 32", "VG 46"],
            "default_specific_heat": 2.03,
            "default_specific_heat_unit": "kJ/kg/degK",
            "default_density": 846.9,
            "default_density_unit": "kg/m³",
            "default_iso": "VG 32",
        },
    )
    assert "ccp-oil-inputs" in html
    assert "oil_specific_heat" in html
    assert "Test Lube Oil" in html
    assert "VG 32" in html
    assert "x-model" in html


def test_file_sidebar_uses_htmx_urls():
    html = render_to_string(
        "core/partials/file_sidebar.html",
        {
            "session_name": "exemplo",
            "save_url": "/core/save/",
            "load_url": "/core/load/",
        },
    )
    assert "ccp-file-sidebar" in html
    assert 'hx-post="/core/save/"' in html
    assert 'hx-post="/core/load/"' in html
    assert 'accept=".ccp"' in html
    assert "Sessão" in html


def test_parameter_row_renders_units_and_help():
    html = render_to_string(
        "core/partials/parameter_row.html",
        {
            "key": "suction_pressure",
            "label": "Suction Pressure",
            "value": 1.5,
            "units": ["bar", "Pa", "kPa"],
            "selected_unit": "bar",
            "help": "Pressão de sucção",
        },
    )
    assert "ccp-param-row" in html
    assert 'name="suction_pressure"' in html
    assert 'name="suction_pressure_unit"' in html
    assert "Pressão de sucção" in html
    assert "selected" in html


def test_sidebar_options_renders_all_checkboxes():
    html = render_to_string(
        "core/partials/sidebar_options.html",
        {
            "polytropic_methods": {
                "Sandberg-Colby": "sandberg_colby",
                "Schultz": "schultz",
            },
            "selected_polytropic_method": "Sandberg-Colby",
            "pressure_units": ["bar", "Pa"],
            "defaults": {},
            "ambient_pressure_value": 1.01325,
            "ambient_pressure_unit": "bar",
        },
    )
    assert "ccp-sidebar-options" in html
    for name in (
        "reynolds_correction",
        "casing_heat_loss",
        "bearing_mechanical_losses",
        "calculate_leakages",
        "seal_gas_flow",
        "variable_speed",
        "show_points",
        "polytropic_method",
        "ambient_pressure",
    ):
        assert f'name="{name}"' in html
    assert "Sandberg-Colby" in html
