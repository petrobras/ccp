"""Pure service-layer tests (no database)."""

import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from ccp_web.services import ccpfile, gas, plant_data, schemas, units
from ccp_web.services import performance_test as pt

EXAMPLES = {
    "example_straight.ccp": "straight_through",
    "example_back_to_back.ccp": "back_to_back",
    "curves-conversion-example.ccp": "curves_conversion",
    "example_evaluation_pi.ccp": "performance_evaluation",
    "example_online.ccp": "performance_evaluation",
    "example_online_pi.ccp": "performance_evaluation",
}


@pytest.mark.parametrize("name,app_type", EXAMPLES.items())
def test_read_examples(example, name, app_type):
    parsed = ccpfile.read_ccp(example(name))
    assert parsed.app_type == app_type
    schema = schemas.get_schema(app_type)
    assert set(parsed.state) == set(schema.fields)
    names = gas.gas_names(parsed.state)
    for key, field in schema.fields.items():
        if field.kind == "gas":
            assert parsed.state[key] in names


def test_back_to_back_example_is_detected_by_content(example):
    # Its session_state.json says app_type=straight_through.
    raw = json.loads(
        zipfile.ZipFile(
            __import__("io").BytesIO(example("example_back_to_back.ccp"))
        ).read("session_state.json")
    )
    assert raw["app_type"] == "straight_through"
    assert (
        ccpfile.read_ccp(example("example_back_to_back.ccp")).app_type == "back_to_back"
    )


def test_expected_app_type(example):
    with pytest.raises(ccpfile.CcpFileError):
        ccpfile.read_ccp(
            example("example_straight.ccp"), expected_app_type="back_to_back"
        )


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_round_trip(example, name):
    first = ccpfile.read_ccp(example(name))
    files = [(k, kind, fname, data) for k, (kind, fname, data) in first.files.items()]
    artifacts = [(k, fname, data) for k, (fname, data) in first.artifacts.items()]
    content = ccpfile.write_ccp(
        first.app_type, first.state, files=files, artifacts=artifacts
    )
    second = ccpfile.read_ccp(content)
    assert second.app_type == first.app_type
    exported = ccpfile.export_state(first.app_type, first.state)
    for key, value in exported.items():
        if key in second.state:
            assert second.state[key] == value, key
    assert {k: v[2] for k, v in second.files.items()} == {
        k: v[2] for k, v in first.files.items()
    }
    assert {k: v[1] for k, v in second.artifacts.items()} == {
        k: v[1] for k, v in first.artifacts.items()
    }


def test_written_file_matches_streamlit_layout(example):
    first = ccpfile.read_ccp(example("example_evaluation_pi.ccp"))
    files = [(k, kind, fname, data) for k, (kind, fname, data) in first.files.items()]
    artifacts = [(k, fname, data) for k, (fname, data) in first.artifacts.items()]
    content = ccpfile.write_ccp(
        first.app_type, first.state, files=files, artifacts=artifacts
    )
    names = zipfile.ZipFile(__import__("io").BytesIO(content)).namelist()
    assert "ccp.version" in names and "session_state.json" in names
    assert "evaluation.zip" in names
    assert "impeller_case_A.toml" in names
    assert "case_A/case-a-head.csv" in names and "case_A/case-a-eff.csv" in names
    state = json.loads(
        zipfile.ZipFile(__import__("io").BytesIO(content)).read("session_state.json")
    )
    # Secrets and endpoints never go into the file.
    assert "pi_password" not in state and "ai_api_key" not in state
    assert "ai_azure_endpoint" not in state


def test_legacy_gas_migration():
    data = {
        "gas_0": "natural",
        "gas_0_component_0": "methane",
        "gas_0_molar_fraction_0": "90",
        "gas_0_component_1": "ethane",
        "gas_0_molar_fraction_1": "10",
    }
    migrated = ccpfile.migrate_state(data, "0.3.6")
    table = migrated["gas_compositions_table"]
    assert table["gas_0"]["component_0"] == "methane"
    state = schemas.normalize("straight_through", migrated)
    assert gas.composition(state, "natural") == {"methane": 90.0, "ethane": 10.0}


def test_legacy_result_toml_migration():
    text = 'speed = "1 rpm"\nother = 1\n'
    assert "speed_operational" in ccpfile.migrate_result_toml(text, "0.3.5")
    assert ccpfile.migrate_result_toml(text, "0.3.6") == text


def test_legacy_csv_names_are_rebuilt(example):
    parsed = ccpfile.read_ccp(example("curves-conversion-example.ccp"))
    assert parsed.files["curves_file_1_case_A"][1] == "case-a-head.csv"
    assert parsed.files["curves_file_2_case_A"][1] == "case-a-eff.csv"
    # Curve names recorded in the session win over the generic one.
    parsed = ccpfile.read_ccp(example("example_online.ccp"))
    names = sorted(parsed.files[k][1] for k in parsed.files)
    assert names == ["lp-sec1-caso-a-eff.csv", "lp-sec1-caso-a-head.csv"]


def test_legacy_csv_kind_from_values():
    head = b"x,11373\n94529,148.586\n98641,148.211\n"
    eff = b"x,11373\n94088,0.7515\n97345,0.757113\n"
    # Swapped slots are named by their values, not by the slot number.
    assert ccpfile._legacy_curve_kind(eff, head, "1") == "eff"
    assert ccpfile._legacy_curve_kind(head, eff, "2") == "head"
    # European decimal commas, quoted by Engauge.
    eu = b'x,13003\n"8584,13","0,836501"\n"8863,49","0,837227"\n'
    assert ccpfile._max_y(eu) == pytest.approx(0.837227)
    # Efficiency in percent is ambiguous: fall back to the convention.
    assert ccpfile._legacy_curve_kind(b"x,1\n1,80\n", b"x,1\n1,120\n", "1") == "head"


def test_state_reader_errors():
    r = units.StateReader({"a": "", "b": "1,5", "c": "x", "d": "2.5"})
    assert r.number("a") is None and r.errors["a"] == "Required"
    assert r.number("b") is None and "decimal separator" in r.errors["b"]
    assert r.number("c") is None and r.errors["c"] == "Not a number"
    assert r.number("d") == 2.5


def test_read_inputs_lists_every_missing_field():
    state = schemas.default_state("straight_through")
    with pytest.raises(units.InputError) as info:
        with units.state_context(state):
            pt.read_inputs("straight_through", state)
    errors = info.value.errors
    assert "flow_point_guarantee" in errors
    assert "gas_point_guarantee" in errors  # default gases have no composition
    assert "flow_point_1" in errors  # no test point at all


def test_calculation_context_restores_method():
    import ccp

    before = ccp.config.POLYTROPIC_METHOD
    with units.calculation_context(ambient_pressure=1.0, polytropic_method="schultz"):
        assert ccp.config.POLYTROPIC_METHOD == "schultz"
        assert abs(ccp.Q_(1, "barg").to("bar").m - 2.0) < 1e-12
    assert ccp.config.POLYTROPIC_METHOD == before


def test_orifice_flows(example):
    state = ccpfile.read_ccp(example("example_straight.ccp")).state
    with units.state_context(state):
        updates, warnings = pt.calculate_orifice_flows(state)
    # Points 1 to 5 have orifice data; the saved results are the reference.
    for i in range(1, 6):
        assert float(updates[f"mass_flow_fo_{i}"]) == pytest.approx(
            float(state[f"mass_flow_fo_{i}"]), rel=1e-4
        )
    assert updates["mass_flow_fo_6"] == ""


def test_frozen_and_redundant_tags():
    idx = pd.date_range("2026-01-01", periods=12, freq="450s")
    df = pd.DataFrame({"ps": [5.0] * 12, "ps_2": np.linspace(4, 6, 12)}, index=idx)
    tm = {
        "suc_p_tag": "A",
        "suc_p_tag_2": "B",
        "suc_p_unit": "bar",
        "suc_p_unit_2": "bar",
    }
    merged = plant_data.merge_redundant_parameter_tags(df.copy(), tm)
    # Tag 1 is frozen (12 identical samples), so tag 2 is used alone.
    assert "ps_2" not in merged
    assert merged["ps"].tolist() == pytest.approx(np.linspace(4, 6, 12).tolist())


def test_tag_mappings_and_units():
    state = schemas.default_state("performance_evaluation")
    state.update(
        suc_p_tag="PT-1",
        flow_method="Orifice",
        delta_p_tag="FT-1",
        fluid_source="Inform Component Tags",
        fluid_component_0="methane",
        fluid_tag_0="AE-C1",
        fluid_unit_0="ppm",
        pi_auth_method="basic",
        pi_username="me",
    )
    tm = plant_data.tag_mappings(state, pi_password="secret")
    assert tm["pi_login"] == ("me", "secret")
    tags, rename, _ = plant_data.build_pi_query(tm)
    assert rename == {"PT-1": "ps", "FT-1": "delta_p", "AE-C1": "fluid_methane"}
    du = plant_data.data_units(state, tm)
    assert du["fluid_methane"] == "ppm" and "delta_p" in du and "flow_v" not in du


def test_read_plant_data_csv():
    content = b"time,ps,Ts\n2026-01-01 00:00,5,300\n2026-01-01 00:07:30,5.1,301\n"
    df = plant_data.read_data_file("data.csv", content)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df["ps"].tolist() == [5.0, 5.1]
