"""Agent API on a performance evaluation case (``evaluation/agent.py``).

Driven through the HTTP API with a token, like ``test_agent_api.py``. The
imported ``example_evaluation_pi.ccp`` carries a saved evaluation, so results
and figures only need the plot build (seconds); the full ``Evaluation``
rebuild is never run here (see ``--run-full-evaluation`` in conftest).

The agent API never handles secrets: PI runs and AI reports are refused with
a 400, and no agent-started job gets a secret handed off, even when one is
remembered (``CCP_PI_PASSWORD`` / ``CCP_AI_API_KEY``).
"""

import json

import pytest
from django.core.cache import cache
from django.test import Client

from ccp_web.agent.models import AgentToken
from ccp_web.core import jobs, secrets
from ccp_web.core.models import Case, Job, Project
from ccp_web.core.views import new_case
from ccp_web.evaluation import agent as eval_agent
from ccp_web.evaluation import views as eval_views
from ccp_web.services import evaluation as ev
from ccp_web.services import plant_data

from .conftest import import_case

pytestmark = pytest.mark.django_db

BASE = "/api/agent/v1/"
PE = Case.PERFORMANCE_EVALUATION
PI_SECRET = "pi-secret-do-not-leak"
AI_SECRET = "ai-secret-do-not-leak"


class Api:
    """Token-authenticated JSON calls; keeps every response body."""

    def __init__(self, token):
        self.client = Client()
        self.headers = {"Authorization": f"Bearer {token}"}
        self.bodies = []

    def get(self, path, **params):
        response = self.client.get(BASE + path, params, headers=self.headers)
        self.bodies.append(response.content)
        return response

    def post(self, path, data=None, method="post"):
        response = getattr(self.client, method)(
            BASE + path,
            json.dumps(data) if data is not None else "",
            content_type="application/json",
            headers=self.headers,
        )
        self.bodies.append(response.content)
        return response

    def calculate(self, case, wait=None, **params):
        body = {"params": params}
        if wait is not None:
            body["wait"] = wait
        return self.post(f"cases/{case.pk}/calculate", body)


@pytest.fixture(autouse=True)
def remembered_secrets(settings, monkeypatch):
    """Secrets a page run would use; the agent must never hand them off."""
    settings.ALLOWED_HOSTS = ["testserver"]
    monkeypatch.setenv("CCP_PI_PASSWORD", PI_SECRET)
    monkeypatch.setenv("CCP_AI_API_KEY", AI_SECRET)
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def stashed(monkeypatch):
    """Every secret handed to a job: ``[(job_id, name)]``."""
    calls = []
    original = secrets.stash_for_job

    def record(job_id, name, value):
        calls.append((job_id, name))
        original(job_id, name, value)

    monkeypatch.setattr(secrets, "stash_for_job", record)
    return calls


@pytest.fixture
def agent(user):
    return Api(AgentToken.issue(user, "Claude")[1])


@pytest.fixture
def empty(user):
    project = Project.objects.create(owner=user, name="Agent evaluation")
    return new_case(project, PE, name="Empty evaluation")


@pytest.fixture
def imported(web, example):
    case, _ = import_case(web, example("example_evaluation_pi.ccp"))
    return case


@pytest.fixture
def two_ticks(monkeypatch):
    """Monitoring jobs run inline in tests: stop the loop after two ticks."""
    handler = jobs.HANDLERS["monitoring"]

    def bounded(ctx):
        ctx.params.setdefault("max_ticks", 1)
        return handler(ctx)

    monkeypatch.setitem(jobs.HANDLERS, "monitoring", bounded)


def set_values(agent, case, **values):
    response = agent.post(f"cases/{case.pk}/state", {"values": values}, "patch")
    assert response.status_code == 200, response.content
    return response.json()


def kinds(case):
    return list(Job.objects.filter(case=case).values_list("kind", flat=True))


# --------------------------------------------------------------------------
# Params and validation (no evaluation needed)
# --------------------------------------------------------------------------


def test_bad_params_are_400(agent, empty):
    for params, text in [
        ({"speed": 1}, "unknown params"),
        ({"action": "explode"}, "action"),
        ({"mode": "fast"}, "mode"),
        ({"action": "report", "mode": "run"}, "do not apply"),
        ({"action": "monitoring_start", "ai": False}, "do not apply"),
        ({"action": "report", "ai": "maybe"}, "true or false"),
    ]:
        response = agent.calculate(empty, **params)
        assert response.status_code == 400, params
        assert text in response.json()["error"], (params, response.json())
    assert kinds(empty) == []


def test_run_validation_errors_match_the_page(agent, empty, web):
    response = agent.calculate(empty)
    assert response.status_code == 400
    errors = response.json()["details"]["errors"]
    assert "No design cases loaded" in errors["suc_p_case_A"]
    assert kinds(empty) == []
    # The page shows the same validation (shared ``run_errors``).
    body = web.post(f"/evaluation/{empty.pk}/run/", {}).content.decode()
    assert "Failed" in body and "No design cases loaded" in body


def test_empty_case_has_no_results_figures_or_report(agent, empty):
    results = agent.get(f"cases/{empty.pk}/results").json()
    assert results["available"] is False
    assert "not evaluated yet" in results["reason"]
    assert results["monitoring"]["available"] is False
    assert agent.get(f"cases/{empty.pk}/figures").json() == []
    assert agent.get(f"cases/{empty.pk}/figures/trend_delta_eff").status_code == 404
    detail = agent.get(f"cases/{empty.pk}").json()
    assert detail["results_available"] is False

    report = agent.calculate(empty, action="report")
    assert report.status_code == 400
    assert "Run an evaluation first" in report.json()["details"]["errors"]["eval_start"]
    monitor = agent.calculate(empty, action="monitoring_start")
    assert monitor.status_code == 400
    assert "Run a performance evaluation first" in monitor.json()["error"]
    stop = agent.calculate(empty, action="monitoring_stop")
    assert stop.status_code == 400 and "never started" in stop.json()["error"]


def test_page_monitoring_start_without_evaluation(web, empty):
    """The refactored view still renders the failed monitor."""
    body = web.post(f"/evaluation/{empty.pk}/monitoring/start/", {}).content
    assert b"Run a performance evaluation first" in body


def test_schema_lists_the_params(agent):
    params = agent.get(f"schema/{PE}").json()["calculate_params"]
    assert set(params) == {"action", "mode", "ai", "letter"}


def test_load_action_presses_a_design_case_load_button(agent, empty):
    """The run needs loaded design cases; the agent can load them too."""
    response = agent.calculate(empty, action="load")
    assert response.status_code == 400 and "letter" in response.json()["error"]
    response = agent.calculate(empty, action="load", letter="A", mode="run")
    assert response.status_code == 400 and "do not apply" in response.json()["error"]
    # The same validation as the page's Load button (``start_load``).
    response = agent.calculate(empty, action="load", letter="a")
    assert response.status_code == 400
    assert "upload both curve files" in str(response.json()["details"])
    results = agent.get(f"cases/{empty.pk}/results").json()
    cases = {d["letter"]: d for d in results["design_cases"]}
    assert cases["A"] == {
        "letter": "A",
        "loaded": False,
        "curve_name": None,
        "load_job": None,
    }


# --------------------------------------------------------------------------
# Secrets: refused, never handed off
# --------------------------------------------------------------------------


def test_pi_run_and_monitoring_are_refused(agent, imported, monkeypatch, stashed):
    assert imported.state["data_source"] == "pi"
    # Without pandaspi the PI source cannot run in the browser either: the
    # field error explains it.
    response = agent.calculate(imported)
    assert response.status_code == 400
    assert "pandaspi" in response.json()["details"]["errors"]["data_source"]

    monkeypatch.setattr(plant_data, "has_pandaspi", lambda: True)
    running = Job.objects.create(
        owner=imported.owner, case=imported, kind="monitoring", status=Job.RUNNING
    )
    for params in ({}, {"mode": "full_rebuild"}, {"action": "monitoring_start"}):
        response = agent.calculate(imported, **params)
        assert response.status_code == 400, params
        error = response.json()["error"]
        assert "PI password" in error and "browser" in error, error
    # Refused before anything happened: the monitor keeps running.
    running.refresh_from_db()
    assert not running.cancel_requested
    assert set(kinds(imported)) == {"monitoring"}
    assert stashed == []


def test_ai_report_is_refused(agent, imported):
    set_values(agent, imported, ai_enabled=True)
    for params in ({"action": "report"}, {"action": "report", "ai": True}):
        response = agent.calculate(imported, **params)
        assert response.status_code == 400
        assert "AI API key" in response.json()["error"]
    set_values(agent, imported, ai_enabled=False)
    response = agent.calculate(imported, action="report", ai=True)
    assert response.status_code == 400
    assert "report" not in kinds(imported)


def test_page_buttons_still_hand_off_remembered_secrets(web, imported, stashed):
    """The views pass the remembered secrets as before the refactor."""
    web.post(f"/evaluation/{imported.pk}/report/", {})
    job = Job.objects.filter(case=imported, kind="report").get()
    assert stashed == [(job.pk, "ai_api_key")]


# --------------------------------------------------------------------------
# End to end on the imported example
# --------------------------------------------------------------------------


@pytest.mark.slow
def test_evaluation_end_to_end(agent, web, imported, monkeypatch, stashed, two_ticks):
    # The imported evaluation has no plots yet: results build them once, in
    # the analysis job (inline in tests), as opening the page does.
    results = agent.get(f"cases/{imported.pk}/results")
    assert results.status_code == 200
    results = results.json()
    assert results["available"] is True, results
    assert kinds(imported) == ["analysis"]
    assert results["inputs_saved_after_calculation"] is False
    assert {d["letter"] for d in results["design_cases"] if d["loaded"]}
    # Viewing the page (its perf panel saves the cluster shown) is not an
    # input change.
    page = web.get(f"/evaluation/{imported.pk}/perf/?cluster=1&similarity=1")
    assert page.status_code == 200
    imported.refresh_from_db()
    assert imported.state["eval_cluster_idx"] == 1
    again = agent.get(f"cases/{imported.pk}/results").json()
    assert again["inputs_saved_after_calculation"] is False

    # From here on nothing may load the evaluation in a request.
    def no_load(*args, **kwargs):
        raise AssertionError("Evaluation.load in a request")

    load = ev.load
    monkeypatch.setattr(ev, "load", no_load)

    assert results["data_source"] == "pi"
    assert results["evaluated"]["n_rows"] >= results["evaluated"]["n_valid"] > 0
    summary = results["summary"]
    assert summary["columns"] == list(ev.TREND_PLOTS)
    assert "mean" in summary["index"]
    assert summary["units"]["delta_head"] == "%"
    assert summary["units"]["delta_eff"] == "percentage points"
    assert all(len(row) == len(summary["columns"]) for row in summary["data"])
    regression = results["trend_regression"]["delta_eff"]
    assert isinstance(regression["slope_per_month"], float)
    clusters = results["clusters"]
    assert clusters["n_clusters"] == len(clusters["items"]) == 4
    assert sum(c["n_rows"] for c in clusters["items"]) == results["table"]["n_rows"]
    table = results["table"]
    assert table["units"]["head"] == "J/kg" and table["units"]["flow_v"] == "m³/s"
    last = table["last_rows"][-1]
    assert isinstance(last["head"], float) and isinstance(last["valid"], bool)
    assert results["report"]["available"] is False
    assert results["monitoring"]["available"] is False
    assert agent.get(f"cases/{imported.pk}").json()["results_available"] is True

    figures = {f["id"]: f for f in agent.get(f"cases/{imported.pk}/figures").json()}
    assert {"trend_delta_eff", "perf_0_head", "perf_3_disch_p_similarity"} <= set(
        figures
    )
    assert {f["section"] for f in figures.values()} == {"trend", "performance"}
    trend = agent.get(f"cases/{imported.pk}/figures/trend_delta_eff").json()
    assert trend["y_title"] == "Delta Efficiency (%)"
    assert len(trend["traces"][0]["y"]) == regression["n_points"]
    head = agent.get(f"cases/{imported.pk}/figures/perf_1_head").json()
    assert head["y_title"] == "Head (kJ/kg)" and "m<sup>3</sup>/h" in head["x_title"]
    assert any(t["name"] == "Historical Points" for t in head["traces"])
    plotly = agent.get(f"cases/{imported.pk}/figures/perf_1_head", format="plotly")
    assert plotly.status_code == 200 and "template" not in plotly.json()["layout"]
    missing = agent.get(f"cases/{imported.pk}/figures/perf_9_head")
    assert (
        missing.status_code == 404
        and "perf_0_head" in missing.json()["details"]["figures"]
    )
    # The jobs below load the saved evaluation, as they should.
    monkeypatch.setattr(ev, "load", load)

    # Report without AI.
    job = agent.calculate(imported, wait=60, action="report", ai=False).json()
    assert job["kind"] == "report" and job["status"] == Job.SUCCEEDED, job
    report = agent.get(f"cases/{imported.pk}/results").json()["report"]
    assert report["available"] is True and report["artifact"] == "report"

    # A run on mock data (no secret needed): nothing new after the window.
    set_values(agent, imported, data_source="mock")
    job = agent.calculate(imported, wait=60).json()
    assert job["kind"] == "evaluation" and job["status"] == Job.SUCCEEDED, job
    assert job["params"] == {"mode": "run"} and "No new data" in job["message"]
    # The run's own state update (the window) does not make it look stale.
    fresh = agent.get(f"cases/{imported.pk}/results").json()
    assert fresh["inputs_saved_after_calculation"] is False

    # Online monitoring on mock data, then stop.
    job = agent.calculate(imported, wait=60, action="monitoring_start").json()
    assert job["kind"] == "monitoring" and job["status"] == Job.SUCCEEDED, job
    # The job lists the view's figures by id (read with figures/<id>).
    assert "monitoring_head" in job["result"]["view"]["figures"]
    monitoring = agent.get(f"cases/{imported.pk}/results").json()["monitoring"]
    assert monitoring["available"] is True, monitoring
    assert monitoring["ticks"] == 1
    metrics = {m["name"]: m for m in monitoring["metrics"]}
    assert metrics["Head"]["units"] == "kJ/kg"
    assert metrics["Efficiency"]["units"] == "%"
    assert metrics["Efficiency"]["delta_units"] == "percentage points"
    assert metrics["Head"]["delta_units"] == "%" and "delta" in metrics["Head"]
    assert all(isinstance(m["value"], (float, type(None))) for m in metrics.values())
    assert monitoring["recent_points"]["units"]["head"] == "J/kg"
    assert monitoring["recent_points"]["rows"]
    assert set(monitoring["figures"]) == {
        "monitoring_head",
        "monitoring_eff",
        "monitoring_power",
        "monitoring_disch_p",
    }
    fig = agent.get(f"cases/{imported.pk}/figures/monitoring_eff").json()
    assert any(t["name"] == "Expected Point" for t in fig["traces"])
    stopped = agent.calculate(imported, action="monitoring_stop").json()
    assert stopped["id"] == job["id"] and stopped["active"] is False

    # No agent-started job got a secret, and none left through a response.
    assert stashed == []
    for body in agent.bodies:
        assert PI_SECRET.encode() not in body and AI_SECRET.encode() not in body


def test_run_on_a_missing_plant_file_is_400(agent, imported):
    set_values(agent, imported, data_source="file")
    response = agent.calculate(imported)
    assert response.status_code == 400
    assert "plant data file" in response.json()["details"]["errors"]["plant_data"]
    assert "evaluation" not in kinds(imported)


def test_adapter_module_shape():
    assert eval_agent.APP_TYPES == eval_views.APP_TYPES
    assert set(eval_agent.ACTION_PARAMS) == set(eval_agent.ACTIONS)
