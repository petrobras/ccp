"""Agent API on the curves conversion page (``ccp_web/curves/agent.py``).

Driven through the HTTP API with a token, like ``test_agent_api.py``. The
example ``curves-conversion-example.ccp`` carries design case A (both
Engauge CSVs and its impeller) and a converted impeller, so results and
figures are available right after import.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ccp_web.agent.models import AgentToken
from ccp_web.core.models import Artifact, Case, Job, Project
from ccp_web.core.views import new_case

from .conftest import import_case
from .test_agent_api import Api

pytestmark = pytest.mark.django_db

EXAMPLE = "curves-conversion-example.ccp"
PANEL_PLOTS = ["head", "eff", "power", "disch_T", "disch_p"]


@pytest.fixture(autouse=True)
def hosts(settings):
    settings.ALLOWED_HOSTS = ["testserver"]


@pytest.fixture
def agent(user):
    return Api(AgentToken.issue(user, "Claude")[1])


@pytest.fixture
def example_case(agent, example):
    """The example imported through the API (multipart ``.ccp`` upload)."""
    response = agent.upload(
        "cases", {"file": SimpleUploadedFile(EXAMPLE, example(EXAMPLE))}
    )
    assert response.status_code == 201, response.content
    case = Case.objects.get(pk=response.json()["id"])
    assert case.app_type == Case.CURVES_CONVERSION
    return case


@pytest.fixture
def empty_case(user):
    project = Project.objects.create(owner=user, name="Curves")
    return new_case(project, Case.CURVES_CONVERSION, name="Empty curves")


def jobs_of(case, kind):
    return Job.objects.filter(case=case, kind=kind).count()


def test_results_of_the_imported_example(agent, example_case):
    results = agent.get(f"cases/{example_case.pk}/results").json()
    assert results["available"] is True
    assert results["loaded_cases"] == ["A"]
    a, b = results["design_cases"][:2]
    assert a["loaded"] and not b["loaded"] and "info" not in b
    assert a["suction_pressure"] == {"value": 3876.0, "units": "kPa"}
    assert a["files"]["curves_file_1_case_A"].endswith(".csv")
    assert a["info"]["n_points"] > 0 and a["info"]["units"]["flow"] == "m³/h"
    assert a["info"]["curve_speeds"] == sorted(a["info"]["curve_speeds"])
    point = a["operating_point"]
    assert point["speed"]["units"] == "rpm" and point["head"]["units"] == "kJ/kg"
    assert 0 < point["eff"]["value"] < 1 and point["eff"]["units"] == "fraction"

    converted = results["converted"]
    assert converted["available"] is True and converted["info"]["n_points"] > 0
    assert converted["operating_point"]["discharge_pressure"]["units"] == "bar"
    assert sum(converted["operating_point"]["gas_mol_fractions"].values()) == (
        pytest.approx(1.0)
    )
    assert results["target"] == {
        "gas": "gas_1",
        "gas_defined": True,
        "suction_pressure": {"value": 2000.0, "units": "kPa"},
        "suction_temperature": {"value": 300.0, "units": "degK"},
        "find_method": "speed",
        "speed_option": "same",
    }
    assert results["plot_units"]["flow_v"] == "m³/h"

    # The operating point follows the panel's inputs, set through the API.
    response = agent.post(
        f"cases/{example_case.pk}/state",
        {"values": {"converted_speed_input": 9000}, "note": "look at 9000 rpm"},
        method="patch",
    )
    assert response.status_code == 200, response.content
    results = agent.get(f"cases/{example_case.pk}/results").json()
    speed = results["converted"]["operating_point"]["speed"]
    assert speed["value"] == pytest.approx(9000)


def test_figures_of_the_imported_example(agent, example_case):
    figures = agent.get(f"cases/{example_case.pk}/figures").json()
    ids = [f["id"] for f in figures]
    assert ids == [f"converted_{n}" for n in PANEL_PLOTS] + [
        f"orig_case_A_{n}" for n in PANEL_PLOTS
    ]
    assert figures[0] == {
        "id": "converted_head",
        "title": "Head (Converted)",
        "section": "converted",
    }
    data = agent.get(f"cases/{example_case.pk}/figures/converted_head").json()
    assert data["id"] == "converted_head" and data["traces"]
    assert any(t["x"] for t in data["traces"])
    plotly = agent.get(
        f"cases/{example_case.pk}/figures/orig_case_A_eff", format="plotly"
    ).json()
    assert plotly["data"] and "template" not in plotly["layout"]
    # A loaded panel's id that is not loaded is unknown.
    response = agent.get(f"cases/{example_case.pk}/figures/orig_case_B_head")
    assert response.status_code == 404
    assert "converted_head" in response.json()["details"]["figures"]


def test_point_outside_the_curves(agent, example_case):
    agent.post(
        f"cases/{example_case.pk}/state",
        {"values": {"converted_flow_input": 1e9}},
        method="patch",
    )
    results = agent.get(f"cases/{example_case.pk}/results").json()
    assert "error" in results["converted"]["operating_point"]
    response = agent.get(f"cases/{example_case.pk}/figures/converted_head")
    assert response.status_code == 400
    assert "converted_flow_input" in response.json()["error"]


def test_convert_and_load_through_the_api(agent, example_case):
    """Both buttons: convert (the default action) and load a design case."""
    pk = example_case.pk
    response = agent.post(
        f"cases/{pk}/state",
        {"values": {"new_suc_p": 2100}, "note": "new suction"},
        method="patch",
    )
    assert response.status_code == 200, response.content
    job = agent.post(f"cases/{pk}/calculate", {"wait": 60}).json()
    assert job["kind"] == "convert_curves" and job["status"] == Job.SUCCEEDED, job
    assert "case A" in job["message"]
    results = agent.get(f"cases/{pk}/results").json()["converted"]
    assert results["job"]["id"] == job["id"]
    assert results["inputs_saved_after_calculation"] is False

    Artifact.objects.filter(case=example_case, key="impeller_case_A").delete()
    assert agent.get(f"cases/{pk}/results").json()["loaded_cases"] == []
    job = agent.post(
        f"cases/{pk}/calculate",
        {"params": {"action": "load", "letter": "a"}, "wait": 60},
    ).json()
    assert job["kind"] == "load_curves" and job["status"] == Job.SUCCEEDED, job
    assert job["params"] == {"case": "A"}
    example_case.refresh_from_db()
    assert example_case.state["curve_name_case_A"] == "case-a"
    results = agent.get(f"cases/{pk}/results").json()
    assert results["loaded_cases"] == ["A"]
    assert results["design_cases"][0]["load_job"]["id"] == job["id"]


def test_calculate_params_are_validated(agent, example_case):
    pk = example_case.pk
    bad = [
        {"bogus": 1},
        {"action": "digitize"},
        {"action": "load"},
        {"action": "load", "letter": "F"},
        {"action": "load", "letter": 1},
        {"action": "convert", "letter": "A"},
    ]
    for params in bad:
        response = agent.post(f"cases/{pk}/calculate", {"params": params})
        assert response.status_code == 400, (params, response.content)
    assert not Job.objects.filter(case=example_case).exists()


def test_load_needs_both_curve_files(agent, example_case):
    response = agent.post(
        f"cases/{example_case.pk}/calculate",
        {"params": {"action": "load", "letter": "B"}},
    )
    assert response.status_code == 400
    errors = response.json()["details"]["errors"]
    assert set(errors) == {"curves_file_1_case_B", "curves_file_2_case_B"}
    assert jobs_of(example_case, "load_curves") == 0


def test_load_needs_valid_suction(agent, example_case):
    agent.post(
        f"cases/{example_case.pk}/state",
        {"values": {"suc_p_case_A": 0}},
        method="patch",
    )
    response = agent.post(
        f"cases/{example_case.pk}/calculate",
        {"params": {"action": "load", "letter": "A"}},
    )
    assert response.status_code == 400
    assert "suc_p_case_A" in response.json()["details"]["errors"]
    assert jobs_of(example_case, "load_curves") == 0


def test_convert_needs_a_design_case(agent, empty_case):
    pk = empty_case.pk
    results = agent.get(f"cases/{pk}/results").json()
    assert results["available"] is False and "reason" in results
    assert results["converted"]["available"] is False
    assert agent.get(f"cases/{pk}").json()["results_available"] is False
    assert agent.get(f"cases/{pk}/figures").json() == []
    assert agent.get(f"cases/{pk}/figures/converted_head").status_code == 404
    response = agent.post(f"cases/{pk}/calculate", {})
    assert response.status_code == 400
    assert (
        "load at least one design case"
        in (response.json()["details"]["errors"]["suc_p_case_A"])
    )
    assert jobs_of(empty_case, "convert_curves") == 0


def test_convert_needs_new_suction(agent, example_case):
    agent.post(
        f"cases/{example_case.pk}/state",
        {"values": {"new_suc_p": 0, "new_suc_t": 0}},
        method="patch",
    )
    response = agent.post(f"cases/{example_case.pk}/calculate", {})
    assert response.status_code == 400
    assert set(response.json()["details"]["errors"]) == {"new_suc_p", "new_suc_t"}


def test_schema_lists_the_actions(agent):
    schema = agent.get("schema/curves_conversion").json()
    assert set(schema["calculate_params"]) == {"action", "letter"}


def test_other_users_cannot_reach_the_case(example_case, django_user_model):
    bob = django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="pw-bob-123"
    )
    other = Api(AgentToken.issue(bob, "Other")[1])
    pk = example_case.pk
    for path in ("results", "figures", "figures/converted_head"):
        assert other.get(f"cases/{pk}/{path}").status_code == 404
    assert other.post(f"cases/{pk}/calculate", {}).status_code == 404
    assert not Job.objects.filter(case=example_case).exists()


def test_page_buttons_still_render_the_validation_errors(web, example):
    """The views share ``start_load`` / ``start_conversion`` with the adapter."""
    case, _ = import_case(web, example(EXAMPLE))
    body = web.post(f"/curves/{case.pk}/load/B/", {}).content.decode()
    assert "Failed" in body and "upload both curve files for Case B" in body
    body = web.post(f"/curves/{case.pk}/convert/", {"new_suc_p": "0"}).content.decode()
    assert "Failed" in body and "new suction condition" in body
    assert not Job.objects.filter(case=case).exists()
    assert web.post(f"/curves/{case.pk}/load/F/", {}).status_code == 404
