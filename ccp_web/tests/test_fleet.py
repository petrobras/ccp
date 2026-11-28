"""Fleet analysis page: member editor, the no-PyMC path and the fit job.

The job test replaces the loading of the member evaluations with
``simulate_fleet`` observations (building real evaluations takes minutes) and
samples with tiny settings.
"""

import io
import json

import pytest

from ccp_web.core import storage
from ccp_web.core.models import Case, Job, Project
from ccp_web.core.views import new_case
from ccp_web.services import fleet as fl

pytestmark = pytest.mark.django_db


def make_cases(user, n=3, evaluated=True):
    project = Project.objects.create(owner=user, name="Fleet project")
    evaluations = []
    for i in range(n):
        case = new_case(project, Case.PERFORMANCE_EVALUATION, name=f"Train {i + 1}")
        if evaluated:
            # the fit is patched; the page only checks the artifact exists
            storage.save_artifact(case, "evaluation", "evaluation.zip", b"stub")
        evaluations.append(case)
    fleet = new_case(project, Case.FLEET_ANALYSIS, name="Fleet")
    return fleet, evaluations


def members_post(evaluations, **extra):
    return {
        "member_evaluation": [str(c.pk) for c in evaluations],
        "member_name": [f"U{i + 1}" for i in range(len(evaluations))],
        "member_site": ["S1", "S2", "S1"][: len(evaluations)],
        "member_shop": [""] * len(evaluations),
        **extra,
    }


def test_page_renders(web, user):
    fleet, evaluations = make_cases(user)
    response = web.get("/app/fleet_analysis/", follow=True)
    assert response.status_code == 200
    body = response.content.decode()
    assert "Fleet analysis" in body
    assert "Fleet project / Train 1" in body  # evaluation cases to pick
    home = web.get("/").content.decode()
    assert "Fleet analysis" in home


def test_member_editor(web, user):
    fleet, evaluations = make_cases(user)
    url = f"/fleet/{fleet.pk}/members/"
    body = web.post(url, members_post(evaluations)).content.decode()
    fleet.refresh_from_db()
    members = fleet.state["fleet_members"]
    assert [m["evaluation"] for m in members] == [c.pk for c in evaluations]
    assert [m["site"] for m in members] == ["S1", "S2", "S1"]
    assert 'id="member-name-2"' in body

    web.post(url, members_post(evaluations, action="add"))
    fleet.refresh_from_db()
    assert len(fleet.state["fleet_members"]) == 4

    web.post(url, members_post(evaluations, action="remove:0"))
    fleet.refresh_from_db()
    assert [m["name"] for m in fleet.state["fleet_members"]] == ["U2", "U3"]

    # text fields save quietly
    response = web.post(url, members_post(evaluations, quiet="1"))
    assert "saved" in response.content.decode().lower()


def test_validation(web, user):
    fleet, evaluations = make_cases(user, evaluated=False)
    post = members_post(evaluations[:1])
    body = web.post(f"/fleet/{fleet.pk}/run/", post).content.decode()
    assert "at least two units" in body
    body = web.post(
        f"/fleet/{fleet.pk}/run/", members_post(evaluations)
    ).content.decode()
    assert "run the evaluation" in body
    assert not Job.objects.filter(case=fleet).exists()


def test_without_pymc(web, user, monkeypatch):
    monkeypatch.setattr(fl, "available", lambda: False)
    fleet, evaluations = make_cases(user)
    body = web.get(f"/fleet/{fleet.pk}/").content.decode()
    assert "pip install ccp-performance[bayes]" in body
    assert 'id="runBtn" type="button" title="Fit the fleet model (⌘↵)" disabled' in body
    body = web.post(
        f"/fleet/{fleet.pk}/run/", members_post(evaluations)
    ).content.decode()
    assert "needs PyMC" in body
    assert not Job.objects.filter(case=fleet).exists()


def test_settings_and_priors():
    state = {
        "fleet_draws": 200,
        "fleet_tune": 100,
        "fleet_chains": 2,
        "fleet_seed": 7,
        "fleet_threshold": 2.5,
        "fleet_tau_unit_head": 3.0,
        "fleet_tau_unit_eff": None,
    }
    assert fl.sampler_kwargs(state) == {
        "draws": 200,
        "tune": 100,
        "chains": 2,
        "random_seed": 7,
    }
    assert fl.threshold(state) == pytest.approx(-0.025)
    priors = fl.priors(state)
    assert priors.tau_unit_head == pytest.approx(0.03)
    assert priors.tau_unit_eff == pytest.approx(0.015)  # library default


def test_fit_job(web, user, monkeypatch):
    pytest.importorskip("pymc")
    from ccp.analytics.fleet import simulate_fleet

    field, shop, _truth = simulate_fleet(
        n_units=3, n_sites=2, days=40, rows_per_day=3, seed=3
    )
    # every field row of U3 is near choke: only its shop test is used
    field.loc[field["unit"] == "U3", "head_slope"] = -3.0
    seen = {}

    def fake_observations(units, load_evaluation, load_shop=None, progress=None):
        seen["units"] = units
        return field, shop, dict(zip(field["unit"], field["site"]))

    monkeypatch.setattr(fl, "observations", fake_observations)
    fleet, evaluations = make_cases(user)
    post = members_post(
        evaluations,
        fleet_draws="50",
        fleet_tune="50",
        fleet_chains="1",
        fleet_seed="1",
        fleet_threshold="3",
    )
    web.post(f"/fleet/{fleet.pk}/run/", post)
    job = Job.objects.filter(case=fleet, kind="fleet").latest("pk")
    assert job.status == Job.SUCCEEDED, job.error + job.result.get("traceback", "")
    assert [u["name"] for u in seen["units"]] == ["U1", "U2", "U3"]
    assert [u["site"] for u in seen["units"]] == ["S1", "S2", "S1"]

    data = json.loads(fleet.artifact("fleet_results").read())
    assert sorted(data["units"]) == ["U1", "U2", "U3"]
    assert set(data["figures"]) == {"units", "health_eff", "health_head"}
    assert {"max_rhat", "min_ess", "divergences"} <= set(data["diagnostics"])
    rows = fl.unit_rows(data)
    u1 = next(r for r in rows if r["unit"] == "U1")
    assert len(rows) == 3 and u1["current_eff"]["range"]
    assert data["units_without_field"] == ["U3"]
    u3 = next(r for r in rows if r["unit"] == "U3")
    assert u3["no_field"] and u3["current_eff"] is None and u3["p_worst"] is None
    assert u3["time_to"] == "—" and u3["asbuilt_eff"] is not None
    assert any("Unit U3" in w for w in job.warnings)

    from ccp.analytics.fleet import Fleet

    loaded = Fleet.load(io.BytesIO(fleet.artifact("fleet").read()))
    assert loaded.units == data["units"]

    body = web.get(f"/fleet/{fleet.pk}/results/").content.decode()
    assert "R-hat" in body and "Fleet scatter" in body and "U2" in body
    assert "no field data" in body
    assert fl.diagnostics(data)["status"] in ("ok", "warn")
    page = web.get(f"/fleet/{fleet.pk}/").content.decode()
    assert "Health" in page

    # the results travel in the .ccp file
    from ccp_web.services import ccpfile

    content = web.get(f"/cases/{fleet.pk}/export/").content
    parsed = ccpfile.read_ccp(content)
    assert parsed.app_type == "fleet_analysis"
    assert set(parsed.artifacts) == {"fleet", "fleet_results"}
    assert len(parsed.state["fleet_members"]) == 3


def test_observations_unit_without_usable_rows(monkeypatch):
    import pandas as pd

    import ccp.analytics.fleet as fleet_module
    from ccp_web.services.units import InputError

    rows = pd.DataFrame(
        {"r_head": [0.0, 0.01], "head_slope": [-2.0, -3.0]},
        index=pd.date_range("2025-01-01", periods=2, freq="1h"),
    )
    monkeypatch.setattr(fleet_module, "field_observations", lambda evaluation: rows)
    units = [
        {"name": "U1", "site": "", "evaluation": 1, "shop": None},
        {"name": "U2", "site": "", "evaluation": 2, "shop": None},
    ]
    with pytest.raises(InputError, match="near choke"):
        fl.observations(units, load_evaluation=lambda pk: None)


def test_diagnostics_status():
    ok = fl.diagnostics({"diagnostics": {"max_rhat": 1.004, "divergences": 0}})
    assert ok["status"] == "ok" and not ok["reasons"]
    bad = fl.diagnostics({"diagnostics": {"max_rhat": 1.05, "divergences": 3}})
    assert bad["status"] == "warn" and len(bad["reasons"]) == 2
