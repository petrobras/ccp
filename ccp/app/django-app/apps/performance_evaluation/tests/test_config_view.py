"""View-level tests for the performance_evaluation config page."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.performance_evaluation import forms
from apps.performance_evaluation._compat import session_store


@pytest.fixture
def client():
    return Client()


def _post_payload(**overrides):
    data = {
        "design-TOTAL_FORMS": "5",
        "design-INITIAL_FORMS": "5",
        "design-MIN_NUM_FORMS": "5",
        "design-MAX_NUM_FORMS": "5",
        "pi-pi_server_name": "srv1",
        "pi-pi_auth_method": "kerberos",
        "pi-pi_username": "",
        "pi-pi_password": "",
        "flow-flow_method": "Direct",
        "flow-orifice_tappings": "flange",
        "flow-orifice_D_unit": "m",
        "flow-orifice_d_unit": "m",
        "fluid-fluid_source": "Fixed Operation Fluid",
        "fluid-operation_fluid_gas": "ng",
        "date-start_date": "2024-01-01",
        "date-start_time": "00:00",
        "date-end_date": "2024-01-02",
        "date-end_time": "00:00",
        "ai-ai_provider": "gemini",
        "curves-loaded_curves_speed_units": "rpm",
        "curves-loaded_curves_flow_units": "m³/h",
        "curves-loaded_curves_head_units": "J/kg",
        "curves-loaded_curves_power_units": "kW",
        "tag_suc_p_tag_1": "FT-001",
        "tag_suc_p_unit_1": "bar",
    }
    for idx, case in enumerate(forms.CASES):
        data[f"design-{idx}-case"] = case
        data[f"design-{idx}-gas"] = ""
        data[f"design-{idx}-suc_p"] = ""
        data[f"design-{idx}-suc_p_unit"] = "bar"
        data[f"design-{idx}-suc_T"] = ""
        data[f"design-{idx}-suc_T_unit"] = "degC"
    data.update(overrides)
    return data


def test_get_config_renders_200(client):
    response = client.get("/performance-evaluation/config/")
    assert response.status_code == 200
    assert b"Performance Evaluation" in response.content


def test_get_config_contains_design_cases_and_tag_mappings(client):
    response = client.get("/performance-evaluation/config/")
    body = response.content.decode("utf-8")
    for case in forms.CASES:
        assert f"Caso {case}" in body
    assert "Servidor PI" in body
    assert "Suction Pressure" in body or "suc_p" in body


def test_post_config_happy_path_persists_state(client):
    response = client.post("/performance-evaluation/config/", data=_post_payload())
    assert response.status_code == 200

    sid = client.session.session_key or "anonymous"
    state = session_store.get_session(sid)
    assert state.get("pi_server_name") == "srv1"
    assert state.get("flow_method") == "Direct"
    assert state.get("suc_p_tag") == "FT-001"


def test_post_config_invalid_date_range_returns_400(client):
    payload = _post_payload(
        **{
            "date-start_date": "2024-02-01",
            "date-end_date": "2024-01-01",
        }
    )
    response = client.post("/performance-evaluation/config/", data=payload)
    assert response.status_code == 400


def test_htmx_flow_method_change_returns_partial(client):
    response = client.post(
        "/performance-evaluation/tag-mappings/flow-method/",
        data={"flow_method": "Orifice"},
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Delta P" in body or "delta_p" in body


def test_htmx_tag_mapping_add(client):
    response = client.post(
        "/performance-evaluation/tag-mappings/add/",
        data={"parameter": "oil_flow"},
    )
    assert response.status_code == 200
    assert b"oil_flow" in response.content


def test_htmx_tag_mapping_remove(client):
    # Seed some state first
    client.get("/performance-evaluation/config/")
    sid = client.session.session_key or "anonymous"
    state = session_store.get_session(sid)
    state["suc_p_tag"] = "FT-99"
    state["suc_p_unit"] = "bar"
    session_store.set_session(sid, state)

    response = client.post("/performance-evaluation/tag-mappings/remove/suc_p/")
    assert response.status_code == 200
    state = session_store.get_session(sid)
    assert "suc_p_tag" not in state


def test_compute_placeholder_returns_204(client):
    assert client.get("/performance-evaluation/compute/").status_code == 204
    assert client.get("/performance-evaluation/monitoring/").status_code == 204
    assert client.get("/performance-evaluation/results/").status_code == 204


def test_upload_curves_persists_file_bytes(client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    client.get("/performance-evaluation/config/")
    f1 = SimpleUploadedFile("curve-head.csv", b"x,y\n1,2\n")
    f2 = SimpleUploadedFile("curve-eff.csv", b"x,y\n1,0.8\n")
    response = client.post(
        "/performance-evaluation/upload-curves/A/",
        data={"curves_file_1": f1, "curves_file_2": f2},
    )
    assert response.status_code == 200
    sid = client.session.session_key or "anonymous"
    state = session_store.get_session(sid)
    assert state["curves_file_1_case_A"]["name"] == "curve-head.csv"
    assert state["curves_file_2_case_A"]["content"].startswith(b"x,y")


def test_upload_curves_rejects_unknown_case(client):
    response = client.post("/performance-evaluation/upload-curves/Z/")
    assert response.status_code == 400
