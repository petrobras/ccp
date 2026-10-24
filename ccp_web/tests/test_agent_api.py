"""Agent HTTP API (``api/agent/v1/``): auth, owner scoping, every endpoint.

The API is called through a fresh test ``Client`` without a session: the
token is the only credential. Every JSON response goes through ``Api``,
which records it so one test can check that no secret ever leaves.
"""

import json
from datetime import timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone

from ccp_web.agent import adapters, api
from ccp_web.agent.models import AgentNote, AgentRevision, AgentToken
from ccp_web.agent.views import navigate_key
from ccp_web.core import secrets
from ccp_web.core.models import Case, Job, Project
from ccp_web.core.views import new_case
from ccp_web.services import ccpfile

from .conftest import import_case

pytestmark = pytest.mark.django_db

BASE = "/api/agent/v1/"
ST = Case.STRAIGHT_THROUGH
SECRET_WORDS = ("pi_password", "ai_api_key", "password")


class Api:
    """Token-authenticated JSON calls; keeps every response body."""

    def __init__(self, token, header="Authorization"):
        self.client = Client()
        self.token = token
        self.header = header
        self.bodies = []

    def _headers(self):
        if self.token is None:
            return {}
        if self.header == "Authorization":
            return {"Authorization": f"Bearer {self.token}"}
        return {self.header: self.token}

    def _keep(self, response):
        self.bodies.append(response.content)
        return response

    def get(self, path, **params):
        return self._keep(self.client.get(BASE + path, params, headers=self._headers()))

    def post(self, path, data=None, method="post"):
        call = getattr(self.client, method)
        body = json.dumps(data) if data is not None else ""
        return self._keep(
            call(
                BASE + path,
                body,
                content_type="application/json",
                headers=self._headers(),
            )
        )

    def upload(self, path, data):
        return self._keep(self.client.post(BASE + path, data, headers=self._headers()))


@pytest.fixture(autouse=True)
def clear_cache(settings):
    settings.ALLOWED_HOSTS = ["testserver"]
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def token(user):
    return AgentToken.issue(user, "Claude")[1]


@pytest.fixture
def agent(token):
    return Api(token)


@pytest.fixture
def project(user):
    return Project.objects.create(owner=user, name="Agent API")


@pytest.fixture
def case(project):
    return new_case(project, ST, name="Empty ST")


@pytest.fixture
def bob(django_user_model):
    return django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="pw-bob-123"
    )


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------


def test_missing_invalid_and_expired_tokens_get_401(user):
    for client in (Api(None), Api("ccpa_not-a-real-token"), Api("nonsense")):
        response = client.get("context")
        assert response.status_code == 401
        assert response["Content-Type"] == "application/json"
        assert "error" in response.json()
        assert response["WWW-Authenticate"].startswith("Bearer")
    row, plaintext = AgentToken.issue(
        user, "old", expires=timezone.now() - timedelta(seconds=1)
    )
    assert Api(plaintext).get("").status_code == 401
    row.expires = timezone.now() + timedelta(hours=1)
    row.save()
    assert Api(plaintext).get("").status_code == 200


def test_hosted_login_required_does_not_redirect(user, token):
    """No token: 401 JSON, never the login page (hosted) or a session (desktop)."""
    response = Client().post(BASE + "cases/1/state", "{}", "application/json")
    assert response.status_code == 401
    response = Api(token).get("")
    assert response.status_code == 200
    assert settings.SESSION_COOKIE_NAME not in response.cookies


def test_session_cookie_alone_is_not_accepted(web, case):
    assert web.get(BASE).status_code == 401
    assert web.get(BASE + f"cases/{case.pk}").status_code == 401
    response = web.post(
        BASE + f"cases/{case.pk}/state",
        json.dumps({"values": {"speed_point_1": "1"}}),
        content_type="application/json",
    )
    assert response.status_code == 401
    case.refresh_from_db()
    assert case.revision == 0


def test_x_ccp_token_header(token):
    assert Api(token, header="X-CCP-Token").get("").status_code == 200


def test_read_token_cannot_write(user, case):
    plaintext = AgentToken.issue(user, "reader", scope=AgentToken.READ)[1]
    reader = Api(plaintext)
    assert reader.get(f"cases/{case.pk}").status_code == 200
    assert reader.get(f"cases/{case.pk}/notes").status_code == 200
    for path, body in [
        (f"cases/{case.pk}/state", {"values": {"speed_point_1": "1"}}),
        (f"cases/{case.pk}/calculate", {}),
        (f"cases/{case.pk}/notes", {"body": "hi"}),
        (f"cases/{case.pk}/undo", {}),
        (f"cases/{case.pk}/duplicate", {}),
        ("cases", {"app_type": ST}),
        ("context/open", {"case": case.pk}),
    ]:
        response = reader.post(path, body)
        assert response.status_code == 403, path
        assert response.json()["error"] == "this token is read-only"
    case.refresh_from_db()
    assert case.revision == 0


def test_root(agent, user):
    data = agent.get("").json()
    assert data["api"] == "ccp-agent" and data["version"] == 1
    assert data["user"] == user.get_username()
    assert data["token"] == {"name": "Claude", "scope": "write", "kind": "personal"}
    assert data["profile"] == settings.CCP_PROFILE
    assert data["app_types"][ST]["adapter"] is True
    assert any("cases/<id>/state" in e for e in data["endpoints"])


def test_method_not_allowed_and_trailing_slash(agent, case):
    response = agent.post("context", {})
    assert response.status_code == 405
    assert "GET" in response["Allow"]
    assert agent.get(f"cases/{case.pk}/").status_code == 200


def test_unknown_paths_are_json_404(agent):
    for path in ("cases/abc", "case/3", "jobs/x", "nope"):
        response = agent.get(path)
        assert response.status_code == 404, path
        assert response["Content-Type"] == "application/json"
        assert "no such endpoint" in response.json()["error"]


# --------------------------------------------------------------------------
# Owner scoping
# --------------------------------------------------------------------------


def test_owner_scoping_across_users(agent, user, bob, case):
    from ccp_web.agent import revisions

    rev = revisions.record_agent_write(case, {"speed_point_1": "1"})
    job = Job.objects.create(owner=user, case=case, kind="calculate")
    AgentNote.objects.create(owner=user, case=case, body="alice only")
    intruder = Api(AgentToken.issue(bob, "bob agent")[1])
    for path in [
        f"cases/{case.pk}",
        f"cases/{case.pk}/state",
        f"cases/{case.pk}/results",
        f"cases/{case.pk}/figures",
        f"cases/{case.pk}/revisions",
        f"cases/{case.pk}/notes",
        f"cases/{case.pk}/export",
        f"jobs/{job.pk}",
    ]:
        assert intruder.get(path).status_code == 404, path
    for path, body in [
        (f"cases/{case.pk}/state", {"values": {"speed_point_2": "2"}}),
        (f"cases/{case.pk}/calculate", {}),
        (f"cases/{case.pk}/undo", {"revision_id": rev.pk}),
        (f"cases/{case.pk}/notes", {"body": "x"}),
        (f"cases/{case.pk}/duplicate", {}),
        (f"jobs/{job.pk}/cancel", {}),
        ("context/open", {"case": case.pk}),
        ("cases", {"app_type": ST, "project": case.project_id}),
    ]:
        assert intruder.post(path, body).status_code == 404, path
    assert intruder.get("cases").json() == []
    assert all(p["name"] != "Agent API" for p in intruder.get("projects").json())
    # Bob's own token cannot undo Alice's revision through his own case either.
    own = new_case(Project.objects.create(owner=bob, name="Bob"), ST)
    response = intruder.post(f"cases/{own.pk}/undo", {"revision_id": rev.pk})
    assert response.status_code == 404
    case.refresh_from_db()
    assert case.revision == 1 and case.state["speed_point_2"] == ""
    job.refresh_from_db()
    assert not job.cancel_requested
    assert [c["id"] for c in agent.get("cases").json()] == [case.pk]


# --------------------------------------------------------------------------
# Validation and errors
# --------------------------------------------------------------------------


def test_state_validation_errors_are_400_json_with_details(agent, case):
    response = agent.post(
        f"cases/{case.pk}/state",
        {"values": {"suction_presure_point_1": "1", "flow_method": "Venturi"}},
    )
    assert response.status_code == 400
    data = response.json()
    assert (
        "suction_pressure_point_1"
        in (data["details"]["unknown"]["suction_presure_point_1"])
    )
    assert "Direct" in data["details"]["invalid"]["flow_method"]
    case.refresh_from_db()
    assert case.revision == 0

    response = agent.client.post(
        BASE + f"cases/{case.pk}/state",
        "{not json",
        content_type="application/json",
        headers=agent._headers(),
    )
    assert response.status_code == 400
    assert "invalid JSON" in response.json()["error"]
    assert agent.post(f"cases/{case.pk}/state", {"note": "x"}).status_code == 400
    response = agent.post(f"cases/{case.pk}/state", {"values": [1, 2]})
    assert response.status_code == 400
    assert agent.get(f"cases/{case.pk}/state", keys="nope").status_code == 400


def test_calculate_with_invalid_inputs_is_400_with_field_errors(agent, case):
    response = agent.post(f"cases/{case.pk}/calculate", {"wait": 5})
    assert response.status_code == 400
    errors = response.json()["details"]["errors"]
    assert "flow_point_1" in errors or "flow_point_guarantee" in errors
    assert not Job.objects.filter(case=case).exists()
    response = agent.post(f"cases/{case.pk}/calculate", {"params": {"speed": 1}})
    assert response.status_code == 400
    assert "unknown params" in response.json()["error"]
    response = agent.post(
        f"cases/{case.pk}/calculate", {"params": {"calculate_speed": "maybe"}}
    )
    assert response.status_code == 400


def test_results_and_figures_before_calculating(agent, case):
    data = agent.get(f"cases/{case.pk}/results").json()
    assert data["available"] is False and data["reason"]
    assert agent.get(f"cases/{case.pk}/figures").json() == []
    response = agent.get(f"cases/{case.pk}/figures/head")
    assert response.status_code == 404
    assert agent.get(f"cases/{case.pk}/figures/bogus").status_code == 404
    assert agent.get(f"cases/{case.pk}").json()["results_available"] is False


def test_missing_adapter_is_501(agent, project, monkeypatch):
    other = new_case(project, Case.CURVES_DIGITIZER)
    monkeypatch.setitem(
        adapters.ADAPTERS, Case.CURVES_DIGITIZER, "ccp_web.digitizer.no_such_agent"
    )
    for path in ("results", "figures", "figures/x"):
        response = agent.get(f"cases/{other.pk}/{path}")
        assert response.status_code == 501
        assert "not implemented for this app type" in response.json()["error"]
    response = agent.post(f"cases/{other.pk}/calculate", {})
    assert response.status_code == 501
    assert agent.get("").json()["app_types"][Case.CURVES_DIGITIZER]["adapter"] is False
    assert agent.get(f"schema/{Case.CURVES_DIGITIZER}").status_code == 200


def test_undo_errors(agent, case):
    assert agent.post(f"cases/{case.pk}/undo", {}).status_code == 404
    first = agent.post(
        f"cases/{case.pk}/state", {"values": {"speed_point_1": "1"}}
    ).json()
    assert agent.post(f"cases/{case.pk}/undo", {}).status_code == 200
    response = agent.post(
        f"cases/{case.pk}/undo", {"revision_id": first["revision_id"]}
    )
    assert response.status_code == 409
    assert response.json()["error"] == "already undone"


def test_notes_validation(agent, case):
    assert agent.post(f"cases/{case.pk}/notes", {"body": "  "}).status_code == 400
    too_long = "x" * (api.MAX_NOTE + 1)
    assert agent.post(f"cases/{case.pk}/notes", {"body": too_long}).status_code == 400
    assert agent.post(f"cases/{case.pk}/notes", {"body": 3}).status_code == 400


def test_create_validation(agent):
    assert agent.post("cases", {"app_type": "nope"}).status_code == 400
    response = agent.post(
        "cases", {"app_type": ST, "state": {"suction_presure_point_1": "1"}}
    )
    assert response.status_code == 400
    assert "unknown" in response.json()["details"]
    response = agent.upload("cases", {"file": SimpleUploadedFile("x.ccp", b"junk")})
    assert response.status_code == 400
    # Where a remembered secret is sent stays the user's choice.
    response = agent.post(
        "cases",
        {
            "app_type": Case.PERFORMANCE_EVALUATION,
            "state": {"ai_azure_endpoint": "https://evil.example"},
        },
    )
    assert response.status_code == 400
    assert "ai_azure_endpoint" in response.json()["details"]["invalid"]


def test_created_from_a_file_cannot_redirect_secrets(agent, project):
    """A .ccp the agent uploads cannot choose where a saved secret goes."""
    state = new_case(project, Case.PERFORMANCE_EVALUATION).state
    state.update(pi_server_name="evil.example", pi_username="mallory")
    content = ccpfile.write_ccp(Case.PERFORMANCE_EVALUATION, state)
    response = agent.upload(
        "cases", {"file": SimpleUploadedFile("ev.ccp", content), "name": "Ev"}
    )
    assert response.status_code == 201, response.content
    body = response.json()
    created = Case.objects.get(pk=body["id"]).state
    default = new_case(project, Case.PERFORMANCE_EVALUATION).state
    assert created["pi_server_name"] == default["pi_server_name"]
    assert created["pi_username"] == default["pi_username"]
    assert len(body["warnings"]) == 2
    assert body["warnings"][0].startswith("pi_server_name reset to its default")


def test_state_write_cannot_redirect_secrets(agent, project):
    ev = new_case(project, Case.PERFORMANCE_EVALUATION)
    response = agent.post(
        f"cases/{ev.pk}/state",
        {"values": {"pi_server_name": "evil.example", "pi_auth_method": "basic"}},
    )
    assert response.status_code == 400
    assert set(response.json()["details"]["invalid"]) == {
        "pi_server_name",
        "pi_auth_method",
    }


def test_monitoring_calculate_does_not_wait_for_the_whole_wait(
    agent, user, case, monkeypatch
):
    """A monitoring job runs until stopped: return soon, not after ``wait``."""
    from ccp_web.agent.views import agent_job_key

    class Adapter:
        def start(self, case, params):
            return Job.objects.create(owner=user, case=case, kind=params["kind"])

    monkeypatch.setattr(adapters, "get_adapter", lambda app_type: Adapter())
    now = [0.0]
    monkeypatch.setattr(api, "_clock", lambda: now[0])
    monkeypatch.setattr(api, "_sleep", lambda s: now.__setitem__(0, now[0] + s))
    job = agent.post(
        f"cases/{case.pk}/calculate", {"params": {"kind": "monitoring"}, "wait": 60}
    ).json()
    assert job["active"] is True and now[0] == pytest.approx(api.MONITORING_WAIT)
    # The open page learns about the agent's job from its poll.
    assert cache.get(agent_job_key(case.pk)) == job["id"]
    now[0] = 0.0
    agent.post(
        f"cases/{case.pk}/calculate", {"params": {"kind": "calculate"}, "wait": 999}
    )
    assert now[0] == pytest.approx(api.MAX_CALCULATE_WAIT)


def test_monitoring_job_lists_figure_ids_instead_of_the_figures(agent, user, case):
    """The view's plotly figures (~60 KB) are read with ``figures/<id>``."""
    big = {"data": [{"x": list(range(500))}], "layout": {}}
    view = {"metrics": [{"label": "Head"}], "figures": {"head": big, "eff": big}}
    job = Job.objects.create(
        owner=user,
        case=case,
        kind="monitoring",
        status=Job.RUNNING,
        result={"ticks": 3, "view": view},
    )
    for body in (
        agent.get(f"jobs/{job.pk}").json(),
        agent.get(f"cases/{case.pk}").json()["jobs"][0],
    ):
        assert body["result"]["ticks"] == 3
        assert body["result"]["view"]["metrics"] == view["metrics"]
        assert body["result"]["view"]["figures"] == [
            "monitoring_head",
            "monitoring_eff",
        ]
    # Stored as it was: the page still renders the figures.
    job.refresh_from_db()
    assert job.result["view"]["figures"]["head"] == big


def test_figure_title_falls_back_to_the_listing(agent, case, monkeypatch):
    import plotly.graph_objects as go

    class Adapter:
        def figures(self, case):
            return [{"id": "head", "title": "Head (Converted)", "section": "x"}]

        def figure(self, case, figure_id):
            return go.Figure(go.Scatter(x=[1], y=[2]))

    monkeypatch.setattr(adapters, "get_adapter", lambda app_type: Adapter())
    data = agent.get(f"cases/{case.pk}/figures/head").json()
    assert data["title"] == "Head (Converted)"


def test_server_errors_are_not_reported_as_client_errors(agent, case, monkeypatch):
    class Adapter:
        def results(self, case):
            raise PermissionError(13, "Permission denied", "/data/artifact.toml")

    monkeypatch.setattr(adapters, "get_adapter", lambda app_type: Adapter())
    response = agent.get(f"cases/{case.pk}/results")
    assert response.status_code == 500
    assert "PermissionError" in response.json()["error"]


# --------------------------------------------------------------------------
# Jobs and schema
# --------------------------------------------------------------------------


def test_job_long_poll_returns_when_done(agent, user, case, monkeypatch):
    job = Job.objects.create(owner=user, case=case, kind="calculate")
    sleeps = []

    def finish_on_second_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            Job.objects.filter(pk=job.pk).update(status=Job.SUCCEEDED, progress=1.0)

    monkeypatch.setattr(api, "_sleep", finish_on_second_sleep)
    data = agent.get(f"jobs/{job.pk}", wait="30").json()
    assert data["status"] == "succeeded" and data["active"] is False
    assert len(sleeps) == 2 and all(s <= api.POLL_STEP for s in sleeps)
    # Already done: no sleeping at all.
    sleeps.clear()
    assert agent.get(f"jobs/{job.pk}", wait="30").json()["status"] == "succeeded"
    assert sleeps == []


def test_job_long_poll_times_out_and_caps_the_wait(agent, user, case, monkeypatch):
    job = Job.objects.create(owner=user, case=case, kind="calculate")
    now = [0.0]
    monkeypatch.setattr(api, "_clock", lambda: now[0])

    def advance(seconds):
        now[0] += seconds

    monkeypatch.setattr(api, "_sleep", advance)
    data = agent.get(f"jobs/{job.pk}", wait="2").json()
    assert data["status"] == "pending"
    assert now[0] == pytest.approx(2.0)
    now[0] = 0.0
    agent.get(f"jobs/{job.pk}", wait="100000")
    assert now[0] == pytest.approx(api.MAX_JOB_WAIT)
    assert agent.get(f"jobs/{job.pk}", wait="soon").status_code == 400


def test_job_cancel(agent, user, case):
    job = Job.objects.create(owner=user, case=case, kind="calculate")
    data = agent.post(f"jobs/{job.pk}/cancel").json()
    assert data["status"] == "cancelled"
    job.refresh_from_db()
    assert job.cancel_requested


def test_schema(agent):
    data = agent.get(f"schema/{ST}").json()
    fields = {f["key"]: f for f in data["fields"]}
    item = fields["suction_pressure_point_1"]
    assert item["kind"] == "text"
    assert item["param"]["label"] == "Suction Pressure"
    assert "bar" in item["param"]["units"]
    assert "param" not in fields["flow_method"]
    assert fields["flow_method"]["options"] == ["Direct", "Orifice"]
    assert "calculate_speed" in data["calculate_params"]
    narrow = agent.get(f"schema/{ST}", filter="oil_iso").json()["fields"]
    assert narrow and all("oil_iso" in f["key"] for f in narrow)
    # The filter also matches options.
    by_option = agent.get(f"schema/{ST}", filter="huntington").json()["fields"]
    assert [f["key"] for f in by_option] == ["polytropic_method"]
    assert agent.get("schema/nope").status_code == 404
    # Each value names the key of its unit, which is not always the obvious one.
    assert item["units_key"] == "suction_pressure_units"
    assert fields["speed_point_guarantee"]["units_key"] == "speed_units_point_guarantee"
    assert "units_key" not in fields["flow_method"]
    b2b = {
        f["key"]: f
        for f in agent.get(
            "schema/back_to_back", filter="section_2_point_guarantee"
        ).json()["fields"]
    }
    assert (
        b2b["discharge_temperature_section_2_point_guarantee"]["units_key"]
        == "discharge_temperature_units_section_1_point_guarantee"
    )


# --------------------------------------------------------------------------
# Adapter helpers
# --------------------------------------------------------------------------


def test_json_safe_and_figure_data():
    import numpy as np
    import plotly.graph_objects as go

    from ccp import Q_

    value = {
        "a": np.float64(1.5),
        "b": float("nan"),
        "c": [np.int64(2), float("inf")],
        "d": np.array([1.0, np.nan]),
        "e": Q_(3, "bar"),
        "f": np.bool_(True),
    }
    assert adapters.json_safe(value) == {
        "a": 1.5,
        "b": None,
        "c": [2, None],
        "d": [1.0, None],
        "e": {"value": 3, "units": "bar"},
        "f": True,
    }
    fig = go.Figure(
        go.Scatter(
            x=np.array([1.0, 2.0]), y=np.array([1 / 3, np.nan]), name="a", mode="lines"
        )
    )
    fig.update_layout(title="T", xaxis_title="X", yaxis_title="Y")
    data = adapters.figure_data(fig)
    assert data["title"] == "T" and data["x_title"] == "X" and data["y_title"] == "Y"
    assert data["traces"][0]["y"] == [0.333333, None]
    # A figure dict with plotly's typed arrays decodes the same way.
    assert adapters.figure_data(json.loads(fig.to_json()))["traces"] == data["traces"]
    full = adapters.figure_json(fig)
    assert full["data"][0]["x"] == [1.0, 2.0]
    assert "template" not in full["layout"]


# --------------------------------------------------------------------------
# Happy path: a straight-through case from an example file
# --------------------------------------------------------------------------


def test_straight_through_flow_end_to_end(web, user, agent, example, bob):
    case, _ = import_case(web, example("example_straight.ccp"), "example_straight.ccp")
    pk = case.pk

    # Presence from the browser -> context.
    response = web.post(
        "/agent/presence/",
        json.dumps({"case": pk, "page": ST, "section": "test", "url": "/x"}),
        content_type="application/json",
    )
    assert response.status_code == 204
    ctx = agent.get("context").json()
    assert ctx["presence"]["case"]["id"] == pk
    assert ctx["presence"]["section"] == "test"
    assert ctx["presence"]["stale"] is False and ctx["presence"]["age_s"] >= 0
    assert ctx["presence"]["case"]["url"].endswith(f"/performance-test/{pk}/")
    assert ctx["recent_cases"][0]["id"] == pk

    # Read.
    detail = agent.get(f"cases/{pk}").json()
    assert detail["case"]["app_type"] == ST and detail["case"]["revision"] == 0
    assert detail["state"]["suction_temperature_point_1"] == "300.13"
    assert {f["key"] for f in detail["files"]} == {"fig_head", "fig_eff"}
    assert [a["key"] for a in detail["artifacts"]] == [ST]
    assert detail["results_available"] is True
    some = agent.get(f"cases/{pk}", keys="flow_point_1,flow_units").json()
    assert some["state"] == {"flow_point_1": "17.114", "flow_units": "kg/s"}
    # Each requested value names the key that holds its unit.
    assert some["units_keys"] == {"flow_point_1": "flow_units"}

    # Set -> one undoable revision.
    response = agent.post(
        f"cases/{pk}/state",
        {"values": {"suction_temperature_point_1": 300.5}, "note": "try 300.5 K"},
        method="patch",
    )
    assert response.status_code == 200, response.content
    written = response.json()
    assert written["case"]["id"] == pk  # which case presence resolved to
    assert written["revision"] == 1
    assert written["changed"] == {"suction_temperature_point_1": ["300.13", "300.5"]}
    assert written["warnings"] == []
    again = agent.post(
        f"cases/{pk}/state", {"values": {"suction_temperature_point_1": "300.5"}}
    ).json()
    assert again == {
        "case": {"id": pk, "name": written["case"]["name"]},
        "revision": 1,
        "changed": {},
        "warnings": [],
        "revision_id": None,
    }

    # Calculate with wait -> results with real numbers.
    job = agent.post(f"cases/{pk}/calculate", {"wait": 120}).json()
    assert job["status"] == "succeeded", job
    assert job["kind"] == "calculate" and job["params"] == {"calculate_speed": False}
    assert job["result"]["speed_operational_rpm"] == pytest.approx(10098, rel=1e-3)
    assert agent.get(f"jobs/{job['id']}").json()["status"] == "succeeded"

    results = agent.get(f"cases/{pk}/results").json()
    assert results["available"] is True
    assert results["speed_rpm"] == pytest.approx(10098, rel=1e-3)
    (section,) = results["sections"]
    assert section["id"] == "st"
    guarantee = next(r for r in section["rows"] if r["label"] == "Guarantee Point")
    head = guarantee["values"]["Headₜ (kJ/kg)"]
    assert isinstance(head, float) and 50 < head < 200
    assert isinstance(results["all_ok"], bool)
    assert results["job"]["id"] == job["id"]

    # Figures.
    figures = agent.get(f"cases/{pk}/figures").json()
    ids = [f["id"] for f in figures]
    assert {"head", "eff", "power", "discharge_pressure", "mach"} <= set(ids)
    head_fig = agent.get(f"cases/{pk}/figures/head").json()
    assert head_fig["id"] == "head" and head_fig["traces"]
    xs = head_fig["traces"][0]["x"]
    assert xs and all(isinstance(x, float) for x in xs if x is not None)
    for fig_id in ids:
        data = agent.get(f"cases/{pk}/figures/{fig_id}").json()
        assert data["traces"], fig_id
    plotly = agent.get(f"cases/{pk}/figures/head", format="plotly").json()
    assert "data" in plotly and "layout" in plotly
    assert "template" not in plotly["layout"]
    path = f"cases/{pk}/figures/head"
    for off in ("0", "false"):
        compact = agent.get(path, format="plotly", template=off).json()
        assert "template" not in compact["layout"], off
    assert "template" in agent.get(path, format="plotly", template="1").json()["layout"]
    if not adapters.kaleido_available():
        assert agent.get(f"cases/{pk}/figures/head", format="png").status_code == 501
    assert agent.get(f"cases/{pk}/figures/head", format="svg").status_code == 400

    # Undo the write.
    undo = agent.post(f"cases/{pk}/undo", {}).json()
    assert undo["source"] == "undo" and undo["undoes"] == written["revision_id"]
    assert undo["changed"] == {"suction_temperature_point_1": ["300.5", "300.13"]}
    case.refresh_from_db()
    assert case.state["suction_temperature_point_1"] == "300.13"
    assert case.revision == 2

    # Notes.
    note = agent.post(f"cases/{pk}/notes", {"body": "Head ratio is 1.01."}).json()
    assert note["author"] == "Claude" and note["dismissed"] is False
    assert [n["id"] for n in agent.get(f"cases/{pk}/notes").json()] == [note["id"]]
    poll = web.get(f"/agent/poll/?case={pk}&rev=0&note=0").json()
    assert [n["body"] for n in poll["notes"]] == ["Head ratio is 1.01."]

    # Revisions.
    revs = agent.get(f"cases/{pk}/revisions").json()
    assert [r["number"] for r in revs] == [2, 1]
    assert revs[1]["undone"] is True and revs[1]["note"] == "try 300.5 K"
    assert revs[1]["author"] == "Claude"
    assert AgentRevision.objects.filter(case_id=pk).count() == 2

    # Export -> import round trip.
    response = agent.get(f"cases/{pk}/export")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/octet-stream"
    assert response["Content-Disposition"].endswith('.ccp"')
    content = response.content
    assert ccpfile.read_ccp(content).app_type == ST
    created = agent.upload(
        "cases",
        {"file": SimpleUploadedFile("round.ccp", content), "name": "Round trip"},
    )
    assert created.status_code == 201, created.content
    copy = Case.objects.get(pk=created.json()["id"])
    assert copy.name == "Round trip" and copy.project_id == case.project_id
    assert {k: v for k, v in copy.state.items() if k != "session_name"} == {
        k: v for k, v in case.state.items() if k != "session_name"
    }
    assert copy.artifact(ST) is not None

    # Duplicate.
    dup = agent.post(f"cases/{pk}/duplicate", {"name": "What if"})
    assert dup.status_code == 201
    dup_case = Case.objects.get(pk=dup.json()["id"])
    assert dup_case.name == "What if" and dup_case.state == {
        **case.state,
        "session_name": dup_case.state["session_name"],
    }
    assert dup_case.files.count() == 2
    assert agent.post(f"cases/{pk}/duplicate").json()["name"].endswith("(copy)")

    # Create (JSON), into the project of the case the user has open.
    response = agent.post(
        "cases",
        {"app_type": ST, "name": "Fresh", "state": {"speed_point_1": "9000"}},
    )
    assert response.status_code == 201
    fresh = response.json()
    assert fresh["name"] == "Fresh" and fresh["project"]["id"] == case.project_id
    assert Case.objects.get(pk=fresh["id"]).state["speed_point_1"] == "9000"
    listed = agent.get("cases", app_type=ST, project=case.project_id).json()
    assert fresh["id"] in [c["id"] for c in listed]
    projects = agent.get("projects").json()
    assert any(p["id"] == case.project_id and p["cases"] >= 4 for p in projects)

    # context/open -> the browser's next poll navigates there.
    opened = agent.post("context/open", {"case": fresh["id"]}).json()
    assert opened["ok"] is True
    assert opened["url"].endswith(f"/performance-test/{fresh['id']}/")
    assert cache.get(navigate_key(user)) == f"/performance-test/{fresh['id']}/"
    poll = web.get("/agent/poll/").json()
    assert poll["navigate"] == f"/performance-test/{fresh['id']}/"
    assert web.get("/agent/poll/").json()["navigate"] is None

    # No secret leaves, even with one handed to a job of this case.
    secret_job = Job.objects.create(
        owner=user,
        case=case,
        kind="calculate",
        result={"pi_password": "hunter2-xyz", "n": 1},
        params={"ai_api_key": "sk-hunter2"},
    )
    secrets.stash_for_job(secret_job.pk, "pi_password", "hunter2-xyz")
    agent.get(f"jobs/{secret_job.pk}")
    agent.get(f"cases/{pk}")
    agent.get(f"schema/{ST}")
    agent.get("")
    for body in agent.bodies:
        text = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
        if body[:2] == b"PK":  # the exported .ccp
            continue
        assert "hunter2" not in text
        for word in SECRET_WORDS:
            assert word not in text.lower(), (word, text[:300])


def test_back_to_back_results_and_figures_from_the_imported_result(web, agent, example):
    case, _ = import_case(web, example("example_back_to_back.ccp"))
    results = agent.get(f"cases/{case.pk}/results").json()
    assert results["available"] is True
    assert [s["id"] for s in results["sections"]] == ["sec1", "sec2"]
    labels = [r["label"] for r in results["sections"][0]["rows"]]
    assert "Guarantee Point" in labels and "Overall" in labels
    ids = [f["id"] for f in agent.get(f"cases/{case.pk}/figures").json()]
    assert "head_sec1" in ids and "power_sec2" in ids
    data = agent.get(f"cases/{case.pk}/figures/head_sec2").json()
    assert data["traces"]
