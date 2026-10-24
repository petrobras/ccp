"""Agent API foundation: value validation, revisions, undo, the stale-form
guard and the browser endpoints (presence, poll, undo, panel, tokens)."""

import json
from datetime import timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from ccp_web.agent import revisions
from ccp_web.agent.models import AgentNote, AgentRevision, AgentToken
from ccp_web.agent.views import navigate_key, presence_key
from ccp_web.core import state as core_state
from ccp_web.core.models import Case, Job, Project
from ccp_web.core.state import ValuesError, apply_values
from ccp_web.core.views import new_case
from ccp_web.services import schemas

pytestmark = pytest.mark.django_db

ST = Case.STRAIGHT_THROUGH


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def project(user):
    return Project.objects.create(owner=user, name="Agent tests")


@pytest.fixture
def case(project):
    return new_case(project, ST, name="ST case")


@pytest.fixture
def other(django_user_model, settings):
    settings.ALLOWED_HOSTS = ["testserver"]
    bob = django_user_model.objects.create_user(
        username="bob", email="bob@example.com", password="pw-bob-123"
    )
    client = Client()
    client.force_login(bob)
    return client


def _state(app_type=ST):
    return schemas.default_state(app_type)


def _reject(values, app_type=ST):
    with pytest.raises(ValuesError) as info:
        apply_values(app_type, _state(app_type), values)
    return info.value


# --------------------------------------------------------------------------
# apply_values
# --------------------------------------------------------------------------


def test_unknown_key_rejects_the_whole_request_with_suggestions():
    err = _reject({"suction_presure_point_1": "1", "flow_point_1": "3"})
    assert "suction_pressure_point_1" in err.unknown["suction_presure_point_1"]
    assert "unknown" in err.details and "invalid" not in err.details


def test_bad_select_lists_the_options():
    err = _reject({"flow_method": "Venturi", "tappings_fo_1": "pipe"})
    assert "Direct" in err.invalid["flow_method"]
    assert "flange" in err.invalid["tappings_fo_1"]
    # Fluid fraction units are not pint units (mol_frac): strict.
    err = _reject({"fluid_unit_0": "kg"}, Case.PERFORMANCE_EVALUATION)
    assert "fluid_unit_0" in err.invalid


def test_unit_keys_take_any_pint_unit():
    new, warnings = apply_values(
        ST, _state(), {"suction_pressure_units": "psi", "speed_units": "rad/s"}
    )
    assert new["suction_pressure_units"] == "psi"
    assert new["speed_units"] == "rad/s"
    assert any("rad/s" in w for w in warnings)
    err = _reject({"suction_pressure_units": "not_a_unit"})
    assert "suction_pressure_units" in err.invalid
    # A unit of another dimension would only fail in the calculation.
    err = _reject({"suction_pressure_units": "degC"})
    assert "dimension" in err.invalid["suction_pressure_units"]
    # Flow takes mass and volumetric units.
    new, _ = apply_values(ST, _state(), {"flow_units": "lbm/s"})
    assert new["flow_units"] == "lbm/s"


def test_numbers_text_fields_keep_strings():
    new, _ = apply_values(
        ST,
        _state(),
        {"suction_pressure_point_1": 4.5, "speed_point_1": "11000", "flow_point_1": 7},
    )
    assert new["suction_pressure_point_1"] == "4.5"
    assert new["speed_point_1"] == "11000"
    assert new["flow_point_1"] == "7"
    cleared, _ = apply_values(ST, new, {"speed_point_1": ""})
    assert cleared["speed_point_1"] == ""
    err = _reject(
        {
            "suction_pressure_point_1": "abc",
            "speed_point_1": "1,5",
            "flow_point_1": True,
        }
    )
    assert set(err.invalid) == {
        "suction_pressure_point_1",
        "speed_point_1",
        "flow_point_1",
    }
    assert "decimal separator" in err.invalid["speed_point_1"]


def test_number_fields():
    app = Case.CURVES_CONVERSION
    new, _ = apply_values(app, _state(app), {"suc_p_case_A": "3.2", "new_suc_t": 40})
    assert new["suc_p_case_A"] == 3.2
    assert new["new_suc_t"] == 40.0
    err = _reject({"suc_p_case_A": "high"}, app)
    assert "suc_p_case_A" in err.invalid


def test_bool_fields():
    new, _ = apply_values(
        ST,
        _state(),
        {"opt_reynolds_correction": "false", "opt_seal_gas_flow": 0, "oil_iso": True},
    )
    assert new["opt_reynolds_correction"] is False
    assert new["opt_seal_gas_flow"] is False
    assert new["oil_iso"] is True
    err = _reject({"opt_reynolds_correction": "maybe"})
    assert "opt_reynolds_correction" in err.invalid


def test_gas_fields_must_name_a_defined_gas():
    new, _ = apply_values(ST, _state(), {"gas_point_1": "gas_2"})
    assert new["gas_point_1"] == "gas_2"
    err = _reject({"gas_point_1": "natural gas"})
    assert "gas_point_1" in err.invalid


def test_gas_convenience_key_renames_and_sets_the_composition():
    values = {
        "gas": {
            "gas_0": {
                "name": "natural gas",
                "composition": {"methane": 90, "Ethane": 10},
            }
        },
        "gas_point_2": "natural gas",
    }
    new, warnings = apply_values(ST, _state(), values)
    assert new["gas_0"] == "natural gas"
    entry = new["gas_compositions_table"]["gas_0"]
    assert entry["name"] == "natural gas"
    assert entry["component_0"] == "methane" and entry["molar_fraction_0"] == 90
    assert entry["component_1"] == "ethane" and entry["molar_fraction_1"] == 10
    assert "component_2" not in entry
    # Selects that used the old name follow the rename.
    assert new["gas_point_1"] == "natural gas"
    assert new["gas_point_guarantee"] == "natural gas"
    assert warnings == []
    _, warnings = apply_values(
        ST, _state(), {"gas": {"gas_1": {"composition": {"methane": 0.5}}}}
    )
    assert any("add up" in w for w in warnings)
    err = _reject({"gas": {"gas_0": {"composition": {"methanol_x": 1}}}})
    assert any(k.startswith("gas.gas_0.") for k in err.invalid)
    err = _reject({"gas": {"gas_9": {"name": "x"}}})
    assert "gas.gas_9" in err.invalid


def test_gas_table_in_the_legacy_layout():
    table = {"gas_3": {"name": "co2 mix", "component_0": "co2", "molar_fraction_0": 1}}
    new, _ = apply_values(ST, _state(), {"gas_compositions_table": table})
    assert new["gas_3"] == "co2 mix"
    assert new["gas_compositions_table"]["gas_3"]["component_0"] == "co2"
    # The other gases are kept.
    assert new["gas_compositions_table"]["gas_0"] == _state()["gas_compositions_table"][
        "gas_0"
    ] | {"name": "gas_0"}
    err = _reject({"gas_compositions_table": "methane"})
    assert "gas_compositions_table" in err.invalid


# --------------------------------------------------------------------------
# record_agent_write, undo, redo
# --------------------------------------------------------------------------


def test_record_agent_write_diff_bump_and_noop(case):
    warnings = []
    rev = revisions.record_agent_write(
        case,
        {"suction_pressure_point_1": "4.5", "suction_pressure_units": "atm"},
        note="match the test log",
        warnings=warnings,
    )
    assert rev.number == 1 and case.revision == 1
    assert sorted(rev.keys) == ["suction_pressure_point_1", "suction_pressure_units"]
    assert rev.before == {
        "suction_pressure_point_1": "",
        "suction_pressure_units": "bar",
    }
    assert rev.after["suction_pressure_point_1"] == "4.5"
    assert rev.note == "match the test log"
    assert warnings and "atm" in warnings[0]
    case.refresh_from_db()
    assert case.revision == 1
    assert case.state["suction_pressure_point_1"] == "4.5"

    # Same values again: nothing recorded, no bump.
    assert revisions.record_agent_write(case, {"suction_pressure_point_1": 4.5}) is None
    case.refresh_from_db()
    assert case.revision == 1
    assert case.agent_revisions.count() == 1

    # A rejected write changes nothing.
    with pytest.raises(ValuesError):
        revisions.record_agent_write(case, {"suction_pressure_point_1": "x"})
    case.refresh_from_db()
    assert case.revision == 1


def test_agent_write_runs_the_page_post_save_hook(case):
    """Switching to the orifice keeps the measured flows aside, as the form does."""
    assert ST in core_state.POST_SAVE_HOOKS
    revisions.record_agent_write(case, {"flow_point_1": "12", "flow_units": "kg/h"})
    rev = revisions.record_agent_write(case, {"flow_method": "Orifice"})
    assert "flow_measured_point_1" in rev.keys
    assert rev.after["flow_measured_point_1"] == "12"
    assert rev.after["flow_measured_units"] == "kg/h"
    # Undo restores every key the write changed, dependent ones included.
    revisions.undo(rev, case.owner)
    case.refresh_from_db()
    assert case.state["flow_method"] == "Direct"
    assert case.state["flow_measured_point_1"] == ""
    assert case.state["flow_point_1"] == "12"


def test_undo_redo_and_already_undone(case, user):
    rev = revisions.record_agent_write(case, {"speed_point_1": "9000"})
    # The user edits the same key afterwards; undo still puts back the old value.
    core_state.update_state(case, speed_point_1="9100")
    undo = revisions.undo(rev, user)
    assert undo.source == AgentRevision.UNDO
    assert undo.number == 2
    assert undo.before == {"speed_point_1": "9100"}
    assert undo.after == {"speed_point_1": ""}
    case.refresh_from_db()
    assert case.state["speed_point_1"] == ""
    assert case.revision == 2
    rev.refresh_from_db()
    assert rev.undone_by == undo
    assert undo.as_dict()["undoes"] == rev.pk

    with pytest.raises(ValueError, match="already undone"):
        revisions.undo(rev, user)

    redo = revisions.undo(undo, user)
    case.refresh_from_db()
    assert case.state["speed_point_1"] == "9100"
    assert redo.number == 3
    # The redo put the write back: the default undo takes it back again.
    assert revisions.latest_undoable(case) == redo
    revisions.undo(redo, user)
    assert revisions.latest_undoable(case) is None

    token, _ = AgentToken.issue(user, "laptop")
    rev5 = revisions.record_agent_write(case, {"speed_point_2": "1"}, token=token)
    assert revisions.latest_undoable(case) == rev5
    assert rev5.as_dict()["author"] == "laptop"
    assert revisions.undo(rev5, token).token == token


def test_default_undo_after_a_redo_takes_the_newest_change(case, user):
    r1 = revisions.record_agent_write(case, {"flow_point_1": "1"})
    r2 = revisions.record_agent_write(case, {"flow_point_2": "2"})
    undo = revisions.undo(r2, user)
    # Successive default undos step back through the agent's writes.
    assert revisions.latest_undoable(case) == r1
    redo = revisions.undo(undo, user)  # the browser's Redo
    assert revisions.latest_undoable(case) == redo
    revisions.undo(revisions.latest_undoable(case), user)
    case.refresh_from_db()
    assert case.state["flow_point_2"] == "" and case.state["flow_point_1"] == "1"
    assert revisions.latest_undoable(case) == r1


def test_undo_of_a_flow_method_switch_restores_the_measured_flows(case, user):
    """Orifice flows stored over the test flows since must not lose them."""
    core_state.update_state(case, flow_point_1="10", flow_units="m³/h")
    rev = revisions.record_agent_write(case, {"flow_method": "Orifice"})
    assert rev.requested == ["flow_method"]
    assert rev.after["flow_measured_point_1"] == "10"
    # The page (or calculate) stores the orifice flows, without a revision.
    core_state.update_state(case, flow_point_1="", flow_units="kg/s")
    undo = revisions.undo(rev, user)
    case.refresh_from_db()
    assert case.state["flow_method"] == "Direct"
    assert case.state["flow_point_1"] == "10"
    assert case.state["flow_units"] == "m³/h"
    assert case.state["flow_measured_point_1"] == ""
    assert case.state["flow_measured_units"] == ""
    # Redo switches back and keeps the measured flows aside again.
    revisions.undo(undo, user)
    case.refresh_from_db()
    assert case.state["flow_method"] == "Orifice"
    assert case.state["flow_measured_point_1"] == "10"
    assert case.state["flow_point_1"] == ""


def test_gas_revisions_and_undo_are_per_gas(case, user):
    rev = revisions.record_agent_write(
        case, {"gas": {"gas_0": {"composition": {"methane": 90, "ethane": 10}}}}
    )
    assert rev.keys == ["gas_compositions_table"]
    # Only the changed gas is recorded, not the whole six-gas table.
    assert list(rev.before["gas_compositions_table"]) == ["gas_0"]
    assert list(rev.after["gas_compositions_table"]) == ["gas_0"]
    # The user then edits another gas in the browser (no revision).
    table = dict(case.state["gas_compositions_table"])
    table["gas_3"] = {"name": "gas_3", "component_0": "co2", "molar_fraction_0": 42.0}
    core_state.update_state(case, gas_compositions_table=table)
    revisions.undo(rev, user)
    case.refresh_from_db()
    after = case.state["gas_compositions_table"]
    assert after["gas_3"]["molar_fraction_0"] == 42.0
    assert after["gas_0"] == _state()["gas_compositions_table"]["gas_0"] | {
        "name": "gas_0"
    }


def test_agent_cannot_change_where_secrets_are_sent(project, user):
    ev = new_case(project, Case.PERFORMANCE_EVALUATION, name="EV")
    for values in (
        {"ai_azure_endpoint": "https://evil.example"},
        {"ai_provider": "azure"},
        {"pi_server_name": "evil.example", "pi_auth_method": "basic"},
    ):
        with pytest.raises(ValuesError) as info:
            revisions.record_agent_write(ev, {"ai_enabled": True, **values})
        assert set(values) <= set(info.value.invalid)
        assert "browser" in next(iter(info.value.invalid.values()))
    ev.refresh_from_db()
    assert ev.revision == 0 and ev.state["ai_enabled"] is False
    # Sending the current value is harmless (a read-modify-write of the state).
    rev = revisions.record_agent_write(
        ev, {"ai_enabled": True, "pi_server_name": ev.state["pi_server_name"]}
    )
    assert rev.keys == ["ai_enabled"]
    # The user's own form saves are unaffected.
    core_state.update_state(ev, ai_azure_endpoint="https://mine.example")
    # Undo puts back what the agent replaced, without the guard.
    revisions.undo(rev, user)


def test_job_state_updates_keep_values_written_during_the_run(project):
    from ccp_web.core.jobs import JobContext

    cc = new_case(project, Case.CURVES_CONVERSION, name="CC")
    core_state.update_state(cc, converted_flow_input=100.0)
    job = Job.objects.create(owner=cc.owner, case=cc, kind="convert_curves")
    ctx = JobContext(Job.objects.select_related("case").get(pk=job.pk))
    revisions.record_agent_write(cc, {"converted_flow_input": 500})
    ctx.update_state(converted_flow_input=None, converted_speed_input=None)
    cc.refresh_from_db()
    assert cc.state["converted_flow_input"] == 500  # the agent's, kept
    assert cc.state["converted_speed_input"] is None


def test_view_settings_do_not_touch_case_updated(case):
    before = Case.objects.get(pk=case.pk).updated
    core_state.merge_state(case, {"speed_point_1": "1"}, touch=False)
    fresh = Case.objects.get(pk=case.pk)
    assert fresh.state["speed_point_1"] == "1" and fresh.updated == before


def test_stale_keys(case):
    revisions.record_agent_write(case, {"speed_point_1": "1"})
    revisions.record_agent_write(case, {"speed_point_2": "2"})
    assert revisions.stale_keys(case, 0) == {"speed_point_1", "speed_point_2"}
    assert revisions.stale_keys(case, 1) == {"speed_point_2"}
    assert revisions.stale_keys(case, 2) == set()


# --------------------------------------------------------------------------
# Stale-form guard
# --------------------------------------------------------------------------


def test_stale_autosave_keeps_the_agent_values(web, case):
    revisions.record_agent_write(case, {"suction_pressure_point_1": "4.5"})
    form = {
        "suction_pressure_point_1": "",  # what the stale page shows
        "suction_temperature_point_1": "30",
    }
    response = web.post(f"/cases/{case.pk}/state/", form, HTTP_X_CCP_REV="0")
    assert response.status_code == 200
    assert response["HX-Refresh"] == "true"
    case.refresh_from_db()
    assert case.state["suction_pressure_point_1"] == "4.5"
    assert case.state["suction_temperature_point_1"] == "30"

    # A page rendered at the current revision saves everything.
    response = web.post(
        f"/cases/{case.pk}/state/",
        {"suction_pressure_point_1": "5"},
        HTTP_X_CCP_REV=str(case.revision),
    )
    assert "HX-Refresh" not in response
    case.refresh_from_db()
    assert case.state["suction_pressure_point_1"] == "5"

    # No header (older page script): no guard, as before.
    response = web.post(f"/cases/{case.pk}/state/", {"suction_pressure_point_1": "6"})
    assert "HX-Refresh" not in response
    case.refresh_from_db()
    assert case.state["suction_pressure_point_1"] == "6"


def test_stale_autosave_keeps_the_agent_gas_table(web, case):
    revisions.record_agent_write(
        case, {"gas": {"gas_0": {"name": "ng", "composition": {"methane": 100}}}}
    )
    form = {
        "gas_0": "gas_0",
        "gas_component_0": "ethane",
        "gas_fraction_0_0": "100",
        "speed_point_1": "9000",
    }
    response = web.post(f"/cases/{case.pk}/state/", form, HTTP_X_CCP_REV="0")
    assert response["HX-Refresh"] == "true"
    case.refresh_from_db()
    assert case.state["gas_0"] == "ng"
    entry = case.state["gas_compositions_table"]["gas_0"]
    assert entry["component_0"] == "methane"
    assert case.state["speed_point_1"] == "9000"


def test_stale_calculate_refreshes_without_starting_a_job(web, case):
    revisions.record_agent_write(case, {"flow_point_guarantee": "123"})
    response = web.post(
        f"/performance-test/{case.pk}/calculate/",
        {"flow_point_guarantee": "1", "speed_point_1": "9000"},
        HTTP_X_CCP_REV="0",
    )
    assert response.status_code == 200
    assert response["HX-Refresh"] == "true"
    case.refresh_from_db()
    assert case.state["flow_point_guarantee"] == "123"
    assert case.state["speed_point_1"] == "9000"
    assert not Job.objects.filter(case=case).exists()

    # At the current revision the view validates as usual (empty case: errors).
    response = web.post(
        f"/performance-test/{case.pk}/calculate/",
        {},
        HTTP_X_CCP_REV=str(case.revision),
    )
    assert "HX-Refresh" not in response
    assert "Failed" in response.content.decode()


def test_stale_test_data_autosave_refreshes(web, case):
    revisions.record_agent_write(case, {"flow_method": "Orifice"})
    response = web.post(
        f"/performance-test/{case.pk}/test-data/",
        {"flow_method": "Direct", "speed_point_1": "1"},
        HTTP_X_CCP_REV="0",
    )
    assert response["HX-Refresh"] == "true"
    case.refresh_from_db()
    assert case.state["flow_method"] == "Orifice"


def test_base_revision_header_parsing(rf):
    assert core_state.base_revision(rf.get("/", HTTP_X_CCP_REV="7")) == 7
    assert core_state.base_revision(rf.get("/", HTTP_X_CCP_REV="x")) is None
    assert core_state.base_revision(rf.get("/", HTTP_X_CCP_REV="-1")) is None
    assert core_state.base_revision(rf.get("/")) is None


# --------------------------------------------------------------------------
# Browser endpoints
# --------------------------------------------------------------------------


def test_presence(web, user, case, other, django_user_model):
    response = web.post(
        "/agent/presence/",
        json.dumps({"case": case.pk, "page": "straight_through", "section": "test"}),
        content_type="application/json",
    )
    assert response.status_code == 204
    value = cache.get(presence_key(user))
    assert value["case"] == case.pk and value["section"] == "test"
    assert value["seen"] > 0
    web.post("/agent/presence/", {"page": "home", "url": "/"})
    assert cache.get(presence_key(user))["case"] is None
    # Another user's case is not recorded as theirs.
    assert other.post("/agent/presence/", {"case": case.pk}).status_code == 204
    bob = django_user_model.objects.get(username="bob")
    assert cache.get(presence_key(bob))["case"] is None


def test_poll_changes_notes_and_navigate(web, user, case):
    url = f"/agent/poll/?case={case.pk}&rev=0&note=0"
    data = web.get(url).json()
    assert data == {
        "revision": 0,
        "changes": [],
        "notes": [],
        "navigate": None,
        "agent_job": None,
    }

    revisions.record_agent_write(case, {"speed_point_1": "1"}, note="first")
    revisions.record_agent_write(case, {"speed_point_2": "2"})
    n1 = AgentNote.objects.create(owner=user, case=case, body="hello")
    AgentNote.objects.create(owner=user, case=case, body="old", dismissed=True)
    data = web.get(url).json()
    assert data["revision"] == 2
    assert [c["number"] for c in data["changes"]] == [1, 2]
    assert data["changes"][0]["changed"] == {"speed_point_1": ["", "1"]}
    assert data["changes"][0]["note"] == "first"
    assert [n["body"] for n in data["notes"]] == ["hello"]

    data = web.get(f"/agent/poll/?case={case.pk}&rev=1&note={n1.pk}").json()
    assert [c["number"] for c in data["changes"]] == [2]
    assert data["notes"] == []
    # Without ``rev`` the page is current: no changes.
    assert web.get(f"/agent/poll/?case={case.pk}").json()["changes"] == []

    cache.set(navigate_key(user), "/performance-test/1/", 60)
    data = web.get("/agent/poll/").json()  # home page: no case
    assert data["navigate"] == "/performance-test/1/"
    assert data["revision"] is None
    assert web.get("/agent/poll/").json()["navigate"] is None


def test_poll_reports_the_job_the_agent_started(web, case):
    """A calculate without a write must still reach the open page."""
    from ccp_web.agent.views import agent_job_key

    job = Job.objects.create(owner=case.owner, case=case, kind="calculate")
    cache.set(agent_job_key(case.pk), job.pk, 60)
    data = web.get(f"/agent/poll/?case={case.pk}&rev=0").json()
    assert data["agent_job"] == {"id": job.pk, "status": "pending", "active": True}


def test_undo_endpoint(web, case):
    rev = revisions.record_agent_write(case, {"speed_point_1": "1"})
    response = web.post(f"/agent/revisions/{rev.pk}/undo/")
    assert response.status_code == 200
    data = response.json()
    assert data["revision"] == 2
    assert data["undo"]["source"] == "undo"
    assert data["undo"]["undoes"] == rev.pk
    case.refresh_from_db()
    assert case.state["speed_point_1"] == ""
    response = web.post(f"/agent/revisions/{rev.pk}/undo/")
    assert response.status_code == 409
    assert response.json()["error"] == "already undone"


def test_note_dismiss_and_panel(web, user, case):
    rev = revisions.record_agent_write(case, {"speed_point_1": "1"}, note="why")
    note = AgentNote.objects.create(
        owner=user, case=case, body="<script>alert(1)</script>\nline two"
    )
    body = web.get(f"/agent/panel/{case.pk}/").content.decode()
    assert "&lt;script&gt;" in body and "<script>alert" not in body
    assert "line two" in body and "<br>" in body
    assert f"/agent/revisions/{rev.pk}/undo/" in body
    assert "speed_point_1" in body
    response = web.post(f"/agent/notes/{note.pk}/dismiss/")
    assert response.json()["ok"] is True
    note.refresh_from_db()
    assert note.dismissed


def test_owner_scoping(other, case, user, django_user_model):
    rev = revisions.record_agent_write(case, {"speed_point_1": "1"})
    note = AgentNote.objects.create(owner=user, case=case, body="private")
    assert other.get(f"/agent/poll/?case={case.pk}&rev=0").status_code == 404
    assert other.get(f"/agent/panel/{case.pk}/").status_code == 404
    assert other.post(f"/agent/revisions/{rev.pk}/undo/").status_code == 404
    assert other.post(f"/agent/notes/{note.pk}/dismiss/").status_code == 404
    rev.refresh_from_db()
    assert rev.undone_by is None
    bob = django_user_model.objects.get(username="bob")
    with pytest.raises(PermissionError):
        revisions.undo(rev, bob)


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------


def test_token_issue_authenticate_and_expiry(user):
    row, plaintext = AgentToken.issue(user, "laptop agent", scope="read")
    assert plaintext.startswith("ccpa_") and len(plaintext) > 40
    assert row.prefix == plaintext[:12]
    assert plaintext not in row.digest and len(row.digest) == 64
    assert AgentToken.authenticate(plaintext) == row
    assert AgentToken.authenticate(plaintext + "x") is None
    assert AgentToken.authenticate("") is None
    assert AgentToken.authenticate(None) is None
    assert not row.can_write

    row.refresh_from_db()
    first = row.last_used
    assert first is not None
    AgentToken.authenticate(plaintext)
    row.refresh_from_db()
    assert row.last_used == first  # at most one write per minute
    AgentToken.objects.filter(pk=row.pk).update(
        last_used=timezone.now() - timedelta(minutes=5)
    )
    AgentToken.authenticate(plaintext)
    row.refresh_from_db()
    assert row.last_used >= first

    AgentToken.objects.filter(pk=row.pk).update(
        expires=timezone.now() - timedelta(seconds=1)
    )
    assert AgentToken.authenticate(plaintext) is None
    user.is_active = False
    user.save()
    _, other_plain = AgentToken.issue(user, "x")
    assert AgentToken.authenticate(other_plain) is None


def test_tokens_page_create_once_and_revoke(web, user, other):
    AgentToken.issue(user, "desktop session", kind=AgentToken.DESKTOP)
    response = web.get("/agent/tokens/")
    assert response.status_code == 200
    assert "desktop session" in response.content.decode()

    response = web.post("/agent/tokens/", {"name": "ci bot", "scope": "read"})
    body = response.content.decode()
    row = AgentToken.objects.get(name="ci bot")
    assert row.scope == "read" and row.kind == AgentToken.PERSONAL
    plaintext = body.split('user-select:all;">')[1].split("<")[0]
    assert AgentToken.authenticate(plaintext) == row
    assert response["Cache-Control"] == "no-store"
    assert plaintext not in web.get("/agent/tokens/").content.decode()

    # Another user cannot revoke it; desktop tokens are not revocable here.
    assert other.post(f"/agent/tokens/{row.pk}/revoke/").status_code == 404
    desktop = AgentToken.objects.get(kind=AgentToken.DESKTOP)
    assert web.post(f"/agent/tokens/{desktop.pk}/revoke/").status_code == 404
    assert web.post(f"/agent/tokens/{row.pk}/revoke/").status_code == 302
    assert not AgentToken.objects.filter(pk=row.pk).exists()


@pytest.mark.skipif(settings.CCP_MULTI_USER, reason="desktop profile only")
def test_api_paths_get_no_desktop_session(client):
    settings.ALLOWED_HOSTS = ["testserver"]
    response = client.get("/api/agent/v1/does-not-exist")
    assert response.wsgi_request.user.is_authenticated is False
    assert settings.SESSION_COOKIE_NAME not in response.cookies
