"""Agent API, browser side: what the server renders for agent.js.

Every case page embeds the case and the revision it was rendered at (sent back
as X-CCP-Rev) and loads agent.js; the drawer partial renders agent text
escaped; the tokens page shows a new token's plaintext once. The JS itself is
checked for the rules that keep agent text out of the HTML parser.
"""

import re
from pathlib import Path

import pytest
from django.core.cache import cache

from ccp_web.agent import revisions
from ccp_web.agent.models import AgentNote, AgentToken, display_value
from ccp_web.core.models import Case, Project
from ccp_web.core.views import new_case

pytestmark = pytest.mark.django_db

JS_DIR = Path(__file__).resolve().parents[1] / "static" / "ccp_web" / "js"
XSS = "<script>alert(1)</script>"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def project(user):
    return Project.objects.create(owner=user, name="Frontend tests")


def _meta(body, name):
    match = re.search(rf'<meta name="{re.escape(name)}" content="([^"]*)">', body)
    return match.group(1) if match else None


@pytest.mark.parametrize("app_type", [t for t, _ in Case.APP_TYPES])
def test_case_pages_embed_case_and_revision(web, project, app_type):
    case = new_case(project, app_type, name=f"{app_type} case")
    Case.objects.filter(pk=case.pk).update(revision=7)
    response = web.get(case.get_absolute_url())
    assert response.status_code == 200
    body = response.content.decode()
    assert _meta(body, "ccp-case") == str(case.pk)
    assert _meta(body, "ccp-case-rev") == "7"
    assert _meta(body, "ccp-page") == app_type
    assert _meta(body, "ccp-agent-poll") == "/agent/poll/"
    assert _meta(body, "ccp-agent-presence") == "/agent/presence/"
    assert _meta(body, "ccp-agent-panel") == f"/agent/panel/{case.pk}/"
    assert _meta(body, "ccp-agent-undo") == "/agent/revisions/0/undo/"
    assert _meta(body, "ccp-agent-dismiss") == "/agent/notes/0/dismiss/"
    assert "ccp_web/js/agent.js" in body
    assert 'id="agent-btn"' in body and 'id="agent-drawer"' in body
    assert 'href="/agent/tokens/"' in body


def test_revision_meta_follows_agent_writes(web, project):
    case = new_case(project, Case.STRAIGHT_THROUGH, name="ST")
    body = web.get(case.get_absolute_url()).content.decode()
    assert _meta(body, "ccp-case-rev") == "0"
    revisions.record_agent_write(case, {"speed_point_1": "9000"}, note="test")
    body = web.get(case.get_absolute_url()).content.decode()
    assert _meta(body, "ccp-case-rev") == "1"
    # The agent's value is what the reloaded form shows.
    assert 'value="9000"' in body


def test_pages_without_a_case_load_agent_js_without_case_meta(web):
    for url in ("/", "/agent/tokens/"):
        body = web.get(url).content.decode()
        assert "ccp_web/js/agent.js" in body
        assert _meta(body, "ccp-agent-poll") == "/agent/poll/"
        assert _meta(body, "ccp-case") is None
        assert _meta(body, "ccp-case-rev") is None
        assert 'id="agent-drawer"' not in body
        assert 'href="/agent/tokens/"' in body
    assert _meta(web.get("/").content.decode(), "ccp-page") == "home"


def test_panel_escapes_agent_text_and_offers_undo(web, user, project):
    case = new_case(project, Case.STRAIGHT_THROUGH, name="ST")
    rev = revisions.record_agent_write(case, {"speed_point_1": "1"}, note=f"why {XSS}")
    second = revisions.record_agent_write(case, {"speed_point_2": "2"})
    revisions.undo(second, user)
    AgentNote.objects.create(
        owner=user, case=case, body=f"{XSS}\nline two", author=f"bot {XSS}"
    )
    body = web.get(f"/agent/panel/{case.pk}/").content.decode()
    assert "<script" not in body
    assert body.count("&lt;script&gt;alert(1)&lt;/script&gt;") == 3
    assert "line two" in body and "<br>" in body
    # Undo for the open write, Redo for the undo revision, none for the undone one.
    assert f'data-agent-undo="{rev.pk}"' in body
    assert f'data-url="/agent/revisions/{rev.pk}/undo/"' in body
    assert f'data-agent-undo="{second.pk}"' not in body
    assert ">Redo</button>" in body and "undone" in body
    assert "speed_point_1" in body and "speed_point_2" in body
    assert "data-agent-dismiss=" in body
    # The buttons are agent.js's, not htmx's (they reload with a highlight).
    assert "hx-post" not in body


def test_panel_labels_a_redo_as_undo_and_shows_gas_fields(web, user, project):
    case = new_case(project, Case.STRAIGHT_THROUGH, name="ST")
    table = case.state["gas_compositions_table"]
    gas = dict(table["gas_0"], molar_fraction_0=0.5, molar_fraction_1=0.5)
    write = revisions.record_agent_write(
        case, {"gas_compositions_table": {"gas_0": gas}, "speed_point_1": "2100"}
    )
    undo = revisions.undo(write, user)
    redo = revisions.undo(undo, user)
    assert [r.as_dict()["redo"] for r in (write, undo, redo)] == [False, False, True]
    assert revisions.change_flags([write, undo, redo]) == {
        write.pk: True,
        undo.pk: False,
        redo.pk: True,
    }
    body = web.get(f"/agent/panel/{case.pk}/").content.decode()
    button = re.search(
        rf'data-agent-undo="{redo.pk}".*?title="([^"]*)">(\w+)</button>', body, re.S
    )
    # Undoing the redo takes the agent's change back out: an Undo.
    assert button.group(2) == "Undo" and "this change replaced" in button.group(1)
    assert ">Redo</button>" not in body
    # The gas table is listed field by field; scalars as the toast shows them.
    assert "gas_0 molar_fraction_0" in body and "gas_0 molar_fraction_1" in body
    assert "component_0" not in body
    rows = {k: (o, n) for k, o, n in write.display_changes()}
    assert rows["gas_0 molar_fraction_0"] == ("0", "0.5")
    assert rows["speed_point_1"][0] is None
    # As the toast's fmt (JSON, String(2100) is "2100").
    assert display_value(2100.0) == "2100" and display_value(True) == "true"
    assert display_value({"a": None}) == '{"a":null}'


def test_tokens_page_shows_plaintext_once(web, user):
    response = web.post("/agent/tokens/", {"name": "laptop agent", "scope": "write"})
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    body = response.content.decode()
    plaintext = re.search(r"ccpa_[A-Za-z0-9_-]+", body).group(0)
    row = AgentToken.objects.get(name="laptop agent")
    assert AgentToken.authenticate(plaintext) == row
    assert body.count(plaintext) == 1
    assert 'id="agent-token-created"' in body
    assert "CCP_AGENT_URL=http://testserver/api/agent/v1/" in body

    body = web.get("/agent/tokens/").content.decode()
    assert plaintext not in body
    assert 'id="agent-token-created"' not in body
    assert "laptop agent" in body and row.prefix in body


def test_js_sends_the_revision_and_keeps_agent_text_out_of_html():
    agent_js = (JS_DIR / "agent.js").read_text()
    app_js = (JS_DIR / "app.js").read_text()
    # Every htmx request and ccpSaveAndReload's fetch carry the base revision.
    assert '"X-CCP-Rev"' in agent_js and "htmx:configRequest" in agent_js
    assert 'headers["X-CCP-Rev"]' in app_js
    # Agent text is only set with textContent; the drawer comes from the server.
    assert "innerHTML" not in agent_js.replace('swap: "innerHTML"', "")
    assert "insertAdjacentHTML" not in agent_js and "outerHTML" not in agent_js
    # Every sessionStorage access is wrapped (the helpers catch).
    assert agent_js.count("window.sessionStorage.") == 3
    assert agent_js.count("} catch (_) {") >= 3


def _function(js, name):
    """The source of ``function name(...) {...}`` (to the next top-level one)."""
    start = js.index(f"function {name}(")
    end = js.find("\n  function ", start + 1)
    return js[start : end if end != -1 else len(js)]


def test_js_reloads_wait_for_the_users_pending_edits():
    """A reload must not drop an edit htmx has not sent yet (delay:400ms)."""
    js = (JS_DIR / "agent.js").read_text()
    app_js = (JS_DIR / "app.js").read_text()
    # Changes that autosave count as pending until htmx sends them.
    assert "lastChangeAt = Date.now()" in js and "lastChangeAt = 0" in js
    busy = _function(js, "busy")
    assert "undoing" in busy and "inflight.size" in busy and "lastChangeAt" in busy
    # Every reload decision checks it: the poll, the focusout re-check and
    # the banner's Reload button (which lets the blurred field's save go).
    assert "!busy()" in _function(js, "onChanges")
    assert "busy()" in _function(js, "recheckSoon")
    assert "busy()" in _function(js, "reloadWhenSettled")
    assert "reloadWhenSettled()" in js
    assert "() => flashAndReload(stale || []))" not in js
    # A stale answer while the user types in another field shows the banner.
    on_load = js[js.index('"htmx:beforeOnLoad"') :]
    on_load = on_load[: on_load.index("});\n")]
    assert "isEditing()" in on_load and "showBanner()" in on_load
    # A multi-revision undo is not cut short by the poll's own reload.
    assert "undoing = true" in _function(js, "undoRevisions")
    assert "if (undoing)" in _function(js, "poll")
    # ccpSaveAndReload reloads through agent.js when its save was stale.
    assert "window.ccpAgentReload = refreshWithFlash" in js
    assert 'r.headers.get("HX-Refresh")' in app_js and "ccpAgentReload" in app_js


def test_js_stale_guard_blocks_only_form_posting_actions():
    js = (JS_DIR / "agent.js").read_text()
    guard = js[js.index('"htmx:beforeRequest"') :]
    guard = guard[: guard.index("});\n")]
    assert "postsForm(e.detail.elt)" in guard
    posts_form = _function(js, "postsForm")
    assert "hx-include" in posts_form and '"FORM"' in posts_form


def test_js_follows_agent_jobs_and_cleans_up_highlights():
    js = (JS_DIR / "agent.js").read_text()
    # A calculation the agent started reaches the page without a write.
    assert "onAgentJob(data.agent_job" in js
    assert "document.getElementById(`job-${job.id}`)" in _function(js, "onAgentJob")
    # The "Agent: old → new" tooltip goes with the highlight.
    assert 'target.removeAttribute("data-help")' in _function(js, "highlight")
    # Presence heartbeats come from the window focused last only; the tab
    # keeps its id across the reloads agent writes cause.
    assert "focusedLast()" in js
    assert "storageGet(TAB_ID_KEY) ||" in js and "storageSet(TAB_ID_KEY" in js


def test_js_names_a_redo_and_lists_gas_fields():
    js = (JS_DIR / "agent.js").read_text()
    flash = _function(js, "showFlash")
    assert "r.redo" in flash and "Redone:" in flash
    assert 'isUndo && !isRedo ? "Redo" : "Undo"' in flash
    assert "redo: !!rev.redo" in _function(js, "compact")
    assert "gasChanges(pair[0], pair[1])" in _function(js, "changeLines")
