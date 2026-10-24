"""Agent API on a curves digitizer case: digitize, results, figures.

Driven through ``api/agent/v1/`` with a token, like ``test_agent_api.py``.
The validation and results tests use a hand-made digitized document, so they
run without Tesseract; the end-to-end test digitizes the synthetic vendor
sheet of ``ccp/tests/test_digitize.py`` and needs the ``digitize`` extra and
Tesseract (skipped otherwise, as in ``test_digitizer.py``).
"""

import json

import pytest

from ccp_web.agent.models import AgentToken
from ccp_web.core import storage
from ccp_web.core.models import Case, Job, Project
from ccp_web.core.views import new_case
from ccp_web.services import digitizer

from .test_agent_api import Api

pytestmark = pytest.mark.django_db

needs_digitizer = pytest.mark.skipif(
    not digitizer.available(), reason="digitize extra or tesseract missing"
)


@pytest.fixture(autouse=True)
def hosts(settings):
    settings.ALLOWED_HOSTS = ["testserver"]


@pytest.fixture
def agent(user):
    return Api(AgentToken.issue(user, "Claude")[1])


@pytest.fixture
def case(user):
    project = Project.objects.create(owner=user, name="Digitizer")
    return new_case(project, Case.CURVES_DIGITIZER, name="Vendor sheet")


def _doc(edited=False):
    """A digitized document with one case of two plots (head and eff)."""
    axis = {"offset": 100.0, "slope": 0.05}
    plot = {
        "page": 1,
        "index": 0,
        "dpi": 300,
        "box": [100, 100, 900, 600],
        "units": "kJ/kg",
        "flow_units": "m³/h",
        "y_title": "POLYTROPIC HEAD kJ/kg",
        "x_title": "INLET VOLUME FLOW m3/h",
        "speeds": [9000.0, 10000.0],
        "x_ticks": [[0.0, 100.0], [2000.0, 200.0]],
        "y_ticks": [[40.0, 600.0], [240.0, 100.0]],
        "x_residual": 0.4,
        "y_residual": 0.3,
        "x_axis": axis,
        "y_axis": {"offset": 700.0, "slope": -2.5},
        "warnings": [],
        "notes": [],
        "source": "vector",
        "labeled": False,
        "reference": [9000.0, 150.0],
        "envelopes": [{"flow": [5000.0, 6000.0], "value": [120.0, 180.0]}],
    }
    head = {
        **plot,
        "param": "head",
        "id": "1-0",
        "edited": edited,
        "curves": [
            {
                "speed": 9000.0,
                "flow": [5000.0, 8000.0, 11000.0],
                "value": [120.0, 110.0, 80.0],
            },
            {"speed": 10000.0, "flow": [6000.0, 12000.0], "value": [180.0, 100.0]},
        ],
    }
    eff = {
        **plot,
        "param": "eff",
        "index": 1,
        "id": "1-1",
        "units": "",
        "curves": [
            {"speed": 9000.0, "flow": [5000.0, 11000.0], "value": [0.7, 0.75]},
            {"speed": 10000.0, "flow": [6000.0, 12000.0], "value": [0.72, 0.8]},
        ],
    }
    logo = {**plot, "param": None, "index": 2, "id": "1-2", "curves": []}
    return {
        "format": "ccp-digitized/1",
        "path": "",
        "n_pages": 1,
        "toc": [],
        "plots": [head, eff, logo],
        "cases": [
            {
                "name": "TEST-1 CASE A",
                "pages": [1],
                "conditions": {"p": [12.5, "bar"], "T": [32.5, "degC"], "mw": 20.0},
                "speeds": [9000.0, 10000.0],
                "flow_ranges": {},
                "warnings": [],
                "plots": {"head": "1-0", "eff": "1-1"},
            }
        ],
    }


def _store(case, data):
    text = digitizer.dumps(data)
    storage.save_case_file(case, "curve_pdf", "curve_pdf", "curves.pdf", b"%PDF-1.4")
    storage.save_artifact(case, "digitized_original", "digitized_original.json", text)
    storage.save_artifact(case, "digitized", "digitized.json", text)


# --------------------------------------------------------------------------
# start: the same validation as the Digitize button
# --------------------------------------------------------------------------


def test_calculate_without_pdf_is_a_field_error(agent, case):
    response = agent.post(f"cases/{case.pk}/calculate", {})
    assert response.status_code == 400
    assert "curve_pdf" in response.json()["details"]["errors"]
    assert not Job.objects.filter(case=case).exists()


def test_calculate_rejects_params_and_bad_pages(agent, case, monkeypatch):
    storage.save_case_file(case, "curve_pdf", "curve_pdf", "c.pdf", b"%PDF-1.4")
    response = agent.post(f"cases/{case.pk}/calculate", {"params": {"pages": "1"}})
    assert response.status_code == 400
    assert "digitize_pages" in response.json()["error"]

    monkeypatch.setattr(digitizer, "available", lambda: True)
    response = agent.post(
        f"cases/{case.pk}/state", {"values": {"digitize_pages": "5-3"}}
    )
    assert response.status_code == 200, response.content
    response = agent.post(f"cases/{case.pk}/calculate", {})
    assert response.status_code == 400
    assert "digitize_pages" in response.json()["details"]["errors"]
    assert not Job.objects.filter(case=case).exists()


def test_calculate_without_digitizer_installed(agent, case, monkeypatch):
    storage.save_case_file(case, "curve_pdf", "curve_pdf", "c.pdf", b"%PDF-1.4")
    monkeypatch.setattr(digitizer, "available", lambda: False)
    response = agent.post(f"cases/{case.pk}/calculate", {})
    assert response.status_code == 400
    assert "Tesseract" in response.json()["details"]["errors"]["curve_pdf"]


def test_page_button_still_renders_field_errors(web, case):
    response = web.post(f"/digitizer/{case.pk}/digitize/", {})
    assert response.status_code == 200
    assert b"Upload a curve PDF first" in response.content


# --------------------------------------------------------------------------
# results and figures
# --------------------------------------------------------------------------


def test_results_and_figures_before_digitizing(agent, case):
    body = agent.get(f"cases/{case.pk}/results").json()
    assert body["available"] is False
    assert "PDF" in body["reason"]
    assert agent.get(f"cases/{case.pk}/figures").json() == []
    assert agent.get(f"cases/{case.pk}/figures/1-0").status_code == 404
    assert agent.get(f"cases/{case.pk}").json()["results_available"] is False


def test_results_summary_has_explicit_units(agent, case):
    _store(case, _doc())
    assert agent.get(f"cases/{case.pk}").json()["results_available"] is True
    body = agent.get(f"cases/{case.pk}/results").json()
    assert body["available"] is True
    assert body["n_plots"] == 3 and body["n_edited"] == 0
    assert body["units"]["speed"] == "rpm"

    (row,) = body["cases"]
    assert row["name"] == "TEST-1 CASE A"
    assert row["conditions"]["p"] == {"value": 12.5, "units": "bar"}
    assert row["conditions"]["mw"] == 20.0
    assert row["plots"] == {"head": "1-0", "eff": "1-1"}
    assert body["unassigned"] == {"plots": [], "pages": [1]}

    head = next(p for p in body["plots"] if p["id"] == "1-0")
    assert head["param"] == "head" and head["cases"] == ["TEST-1 CASE A"]
    assert head["units"] == "kJ/kg" and head["flow_units"] == "m³/h"
    assert head["edited"] is False
    assert head["n_curves"] == 2 and head["n_points"] == 5
    first = head["curves"][0]
    assert first["name"] == "9000 rpm" and first["speed_units"] == "rpm"
    assert first["n_points"] == 3
    assert first["flow_range"] == {"min": 5000.0, "max": 11000.0, "units": "m³/h"}
    assert first["value_range"] == {"min": 80.0, "max": 120.0, "units": "kJ/kg"}
    assert head["flow_range"]["max"] == 12000.0
    cal = head["calibration"]
    assert cal["dpi"] == 300 and "offset + slope" in cal["convention"]
    assert cal["x"]["slope"] == 0.05 and cal["x"]["ticks"] == [0.0, 2000.0]
    assert cal["y"]["residual_px"] == 0.3
    assert head["reference_point"] == {"flow": 9000.0, "value": 150.0}
    # eff in fractions: no units printed on the sheet
    eff = next(p for p in body["plots"] if p["id"] == "1-1")
    assert eff["units"] is None and eff["value_range"]["units"] is None


def test_figures_are_the_digitized_points(agent, case):
    _store(case, _doc(edited=True))
    items = agent.get(f"cases/{case.pk}/figures").json()
    # the unrecognized frame has no curves, so no figure
    assert [f["id"] for f in items] == ["1-0", "1-1"]
    assert items[0]["section"] == "TEST-1 CASE A"

    fig = agent.get(f"cases/{case.pk}/figures/1-0").json()
    assert fig["x_title"] == "Flow (m³/h)"
    assert fig["y_title"] == "Polytropic head (kJ/kg)"
    assert "(edited)" in fig["title"]
    names = [t["name"] for t in fig["traces"]]
    assert names == ["9000 rpm", "10000 rpm", "envelope 1", "reference point"]
    assert fig["traces"][0]["x"] == [5000.0, 8000.0, 11000.0]
    assert fig["traces"][0]["y"] == [120.0, 110.0, 80.0]

    plotly = agent.get(f"cases/{case.pk}/figures/1-1", format="plotly").json()
    assert len(plotly["data"]) == 4
    assert agent.get(f"cases/{case.pk}/figures/1-2").status_code == 404

    body = agent.get(f"cases/{case.pk}/results").json()
    assert body["n_edited"] == 1


def test_other_users_cannot_read_digitizer_results(django_user_model, case):
    _store(case, _doc())
    bob = django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="pw-bob-123"
    )
    other = Api(AgentToken.issue(bob, "bob")[1])
    for path in ("results", "figures", "figures/1-0"):
        assert other.get(f"cases/{case.pk}/{path}").status_code == 404
    assert other.post(f"cases/{case.pk}/calculate", {}).status_code == 404


# --------------------------------------------------------------------------
# end to end on the synthetic vendor sheet
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sheet_pdf(tmp_path_factory):
    from ccp.tests.test_digitize import make_sheet

    path = tmp_path_factory.mktemp("sheet") / "vendor curves.pdf"
    make_sheet(path)
    return path.read_bytes()


@needs_digitizer
def test_digitize_through_the_api(agent, web, case, sheet_pdf, monkeypatch):
    monkeypatch.setenv("CCP_DIGITIZE_WORKERS", "1")
    storage.save_case_file(case, "curve_pdf", "curve_pdf", "vendor.pdf", sheet_pdf)
    assert agent.post(
        f"cases/{case.pk}/state", {"values": {"digitize_pages": "1"}}
    ).json()["changed"] == {"digitize_pages": ["", "1"]}

    job = agent.post(f"cases/{case.pk}/calculate", {"wait": 120}).json()
    assert job["kind"] == "digitize_pdf"
    assert job["status"] == Job.SUCCEEDED, job["error"]
    assert job["result"]["cases"] == 1

    body = agent.get(f"cases/{case.pk}/results").json()
    assert body["available"] is True and body["pages"] == "1"
    (row,) = body["cases"]
    assert row["name"] == "TEST-1 CASE A"
    assert set(row["plots"]) >= {"head", "eff"}
    head = next(p for p in body["plots"] if p["id"] == row["plots"]["head"])
    assert head["units"] == "kJ/kg"
    assert head["n_curves"] >= 2
    assert all(c["n_points"] >= 2 for c in head["curves"])
    assert all(c["speed_units"] == "rpm" for c in head["curves"])
    assert 0 <= head["flow_range"]["min"] < head["flow_range"]["max"] <= 14000
    assert 40 <= head["value_range"]["min"] < head["value_range"]["max"] <= 240
    assert head["edited"] is False

    fig = agent.get(f"cases/{case.pk}/figures/{head['id']}").json()
    speed_traces = [t for t in fig["traces"] if t["name"].endswith("rpm")]
    assert len(speed_traces) == head["n_curves"]
    assert len(speed_traces[0]["x"]) == head["curves"][0]["n_points"]

    # an edit in the browser editor shows up as edited
    data = json.loads(case.artifact("digitized").read())
    curves = digitizer.editor_payload(data, head["id"])["curves"]
    curves[0]["points"] = curves[0]["points"][:-1]
    response = web.post(
        f"/digitizer/{case.pk}/plot/{head['id']}/save/",
        json.dumps({"curves": curves}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    body = agent.get(f"cases/{case.pk}/results").json()
    head = next(p for p in body["plots"] if p["id"] == head["id"])
    assert head["edited"] is True and body["n_edited"] == 1
    assert head["curves"][0]["n_points"] == len(curves[0]["points"])
