"""Agent-side tools: discovery, the Python client, the CLI and the MCP server.

The client talks to the API through its ``transport`` hook over Django's test
``Client`` (no session, the token is the only credential), so the whole chain
client -> HTTP API -> revisions runs in-process. The agent-side modules must
import without Django; one test proves it in a subprocess that blocks Django
and platformdirs.
"""

import io
import json
import os
import stat
import subprocess
import sys
import textwrap
from urllib.parse import urlsplit

import pytest
from django.core.cache import cache
from django.test import Client

from ccp_web import cli as web_cli
from ccp_web import launcher
from ccp_web.agent import cli, discovery, mcp
from ccp_web.agent.client import CcpApp, CcpAppError, connect
from ccp_web.agent.models import AgentToken
from ccp_web.core.models import Case

from .conftest import import_case

pytestmark = pytest.mark.django_db

API = "http://testserver/api/agent/v1/"
ST = Case.STRAIGHT_THROUGH
AGENT_ENV = ("CCP_AGENT_URL", "CCP_AGENT_TOKEN", "CCP_AGENT_FILE", "CCP_DATA_DIR")


def django_transport(client=None):
    """``CcpApp`` transport over the Django test client."""
    client = client or Client()

    def transport(method, url, body, headers):
        parts = urlsplit(url)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        headers = dict(headers)
        content_type = headers.pop("Content-Type", "application/octet-stream")
        response = client.generic(
            method, path, body or b"", content_type=content_type, headers=headers
        )
        return response.status_code, dict(response.items()), response.content

    return transport


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, settings):
    settings.ALLOWED_HOSTS = ["testserver"]
    for name in AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def token(user):
    return AgentToken.issue(user, "Claude")[1]


@pytest.fixture
def app(token):
    return CcpApp(API, token, transport=django_transport())


@pytest.fixture
def opened(web, example):
    """The straight-through example, open in the user's browser."""
    case, _ = import_case(web, example("example_straight.ccp"), "example_straight.ccp")
    response = web.post(
        "/agent/presence/",
        json.dumps({"case": case.pk, "page": ST, "section": "test", "url": "/x"}),
        content_type="application/json",
    )
    assert response.status_code == 204
    return case


def run_cli(capsys, token, *argv):
    """``ccp-web agent <argv>``: ``(exit code, stdout JSON, stderr JSON)``."""
    code = cli.main(
        ["--url", API, "--token", token, *argv], transport=django_transport()
    )
    out, err = capsys.readouterr()
    return (
        code,
        json.loads(out) if out.strip() else None,
        json.loads(err) if err.strip() else None,
    )


# --------------------------------------------------------------------------
# Importable without Django
# --------------------------------------------------------------------------


def test_agent_side_modules_import_without_django(tmp_path):
    script = textwrap.dedent(
        """
        import json, sys

        class Block:
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] in ("django", "platformdirs"):
                    raise ImportError("blocked: " + name)
                return None

        sys.meta_path.insert(0, Block())
        import ccp_web.agent.client, ccp_web.agent.cli, ccp_web.agent.mcp
        import ccp_web.agent.discovery as d
        from ccp_web import cli

        out = {"data_dir": str(d.data_dir())}
        try:
            cli.main(["agent", "status"])
        except SystemExit as exc:
            out["exit"] = exc.code
        out["django"] = sorted(m for m in sys.modules if m.startswith("django"))
        out["platformdirs"] = "platformdirs" in sys.modules
        print(json.dumps(out))
        """
    )
    env = {k: v for k, v in os.environ.items() if k not in AGENT_ENV}
    env["CCP_AGENT_FILE"] = str(tmp_path / "missing.json")
    env.pop("DJANGO_SETTINGS_MODULE", None)
    proc = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["django"] == [] and out["platformdirs"] is False
    assert out["exit"] == 1
    assert out["data_dir"] == str(discovery._fallback_data_dir())
    error = json.loads(proc.stderr)
    assert "not running" in error["error"] and "missing.json" in error["error"]


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def test_fallback_data_dir_matches_platformdirs(monkeypatch, tmp_path):
    from platformdirs import user_data_dir

    assert str(discovery._fallback_data_dir()) == user_data_dir("ccp", "ccp")
    assert discovery.data_dir() == discovery._fallback_data_dir()
    if sys.platform.startswith("linux"):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        assert str(discovery._fallback_data_dir()) == user_data_dir("ccp", "ccp")
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path / "data"))
    assert discovery.data_dir() == tmp_path / "data"
    assert discovery.AGENT_FILE == tmp_path / "data" / "agent.json"


def test_api_url_normalisation():
    root = "http://127.0.0.1:8000/api/agent/v1/"
    for url in (
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8000/",
        "http://127.0.0.1:8000/api/agent/v1",
        root,
    ):
        assert discovery.api_url(url) == root


def test_agent_file_write_read_remove(tmp_path):
    path = tmp_path / "sub" / "agent.json"
    written = discovery.write(
        "http://127.0.0.1:9/", "ccpa_x", pid=os.getpid(), path=path
    )
    assert written == path
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    data = discovery.read(path)
    assert data["token"] == "ccpa_x" and data["pid"] == os.getpid()
    assert data["api_url"] == "http://127.0.0.1:9/api/agent/v1/"
    assert [p.name for p in path.parent.iterdir()] == ["agent.json"]
    # Another process's file is left alone.
    assert discovery.remove_if_owned(os.getpid() + 1, path=path) is False
    assert path.exists()
    assert discovery.remove_if_owned(os.getpid(), path=path) is True
    assert not path.exists() and discovery.read(path) is None
    assert discovery.remove_if_owned(os.getpid(), path=path) is False
    path.write_text("not json")
    assert discovery.read(path) is None


def test_resolution_order(monkeypatch, tmp_path):
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path / "data"))
    discovery.write("http://127.0.0.1:1/", "ccpa_default")
    assert discovery.resolve() == (
        "http://127.0.0.1:1/api/agent/v1/",
        "ccpa_default",
        str(tmp_path / "data" / "agent.json"),
    )
    other = tmp_path / "other.json"
    discovery.write("http://127.0.0.1:2/", "ccpa_file", path=other)
    monkeypatch.setenv("CCP_AGENT_FILE", str(other))
    assert discovery.resolve()[:2] == ("http://127.0.0.1:2/api/agent/v1/", "ccpa_file")
    # The environment beats the files, field by field.
    monkeypatch.setenv("CCP_AGENT_URL", "http://10.0.0.1:3")
    assert discovery.resolve()[:2] == ("http://10.0.0.1:3/api/agent/v1/", "ccpa_file")
    monkeypatch.setenv("CCP_AGENT_TOKEN", "ccpa_env")
    assert discovery.resolve() == (
        "http://10.0.0.1:3/api/agent/v1/",
        "ccpa_env",
        "arguments or environment",
    )
    # Explicit arguments beat everything.
    assert discovery.resolve("http://h:4/", "ccpa_arg")[:2] == (
        "http://h:4/api/agent/v1/",
        "ccpa_arg",
    )


def test_missing_file_and_stale_pid_messages(monkeypatch, tmp_path):
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path))
    with pytest.raises(discovery.DiscoveryError) as exc:
        discovery.resolve()
    assert "ccp app is not running" in str(exc.value)
    assert "ccp-web serve" in str(exc.value) and "agent.json" in str(exc.value)

    monkeypatch.setenv("CCP_AGENT_URL", "http://127.0.0.1:5/")
    with pytest.raises(discovery.DiscoveryError, match="CCP_AGENT_TOKEN"):
        discovery.resolve()
    monkeypatch.delenv("CCP_AGENT_URL")

    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    discovery.write("http://127.0.0.1:5/", "ccpa_old", pid=dead.pid)
    if os.name == "posix":
        with pytest.raises(discovery.DiscoveryError) as exc:
            discovery.resolve()
        message = str(exc.value)
        assert "ccp app is not running" in message
        assert str(dead.pid) in message and "no longer running" in message
        with pytest.raises(CcpAppError) as err:
            connect()
        assert err.value.status is None and "not running" in err.value.error
    # A file written on another machine (WSL reading Windows) is not pid-checked.
    data = discovery.read()
    data["host"] = "some-windows-box"
    (tmp_path / "agent.json").write_text(json.dumps(data))
    assert discovery.resolve()[1] == "ccpa_old"


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------


def test_client_round_trip_on_the_open_case(app, opened, user):
    pk = opened.pk
    assert app.root()["user"] == user.get_username()
    assert app.case_id() == pk
    detail = app.case(keys=["flow_point_1", "flow_units"])
    assert detail["case"]["id"] == pk
    assert detail["state"] == {"flow_point_1": "17.114", "flow_units": "kg/s"}
    assert app.state(keys="flow_units") == {
        "revision": 0,
        "state": {"flow_units": "kg/s"},
    }

    written = app.set({"suction_temperature_point_1": 300.5}, note="try 300.5 K")
    assert written["revision"] == 1
    assert written["changed"] == {"suction_temperature_point_1": ["300.13", "300.5"]}

    job = app.calculate(wait=120)
    assert job["status"] == "succeeded", job
    assert app.job(job["id"])["status"] == "succeeded"
    results = app.results()
    assert results["available"] is True
    assert results["speed_rpm"] == pytest.approx(10098, rel=1e-3)
    assert "head" in [f["id"] for f in app.figures()]
    assert app.figure("head")["traces"]

    undo = app.undo()
    assert undo["undoes"] == written["revision_id"]
    opened.refresh_from_db()
    assert opened.state["suction_temperature_point_1"] == "300.13"
    assert [r["number"] for r in app.revisions()] == [2, 1]

    note = app.note("Head looks fine.")
    assert note["author"] == "Claude"
    assert [n["body"] for n in app.notes()] == ["Head looks fine."]


def test_client_errors(app, opened, token):
    with pytest.raises(CcpAppError) as exc:
        app.set({"suction_pressur_point_1": 1})
    assert exc.value.status == 400
    assert (
        "suction_pressure_point_1"
        in exc.value.details["unknown"]["suction_pressur_point_1"]
    )
    with pytest.raises(CcpAppError) as exc:
        app.case(999999)
    assert exc.value.status == 404
    with pytest.raises(CcpAppError) as exc:
        CcpApp(API, "ccpa_wrong", transport=django_transport()).context()
    assert exc.value.status == 401
    unreachable = CcpApp("http://127.0.0.1:1/", token)
    with pytest.raises(CcpAppError) as exc:
        unreachable.root()
    assert exc.value.status is None and "cannot reach" in exc.value.error


def test_client_timeouts_and_protocol_errors_are_not_app_not_running(token):
    import http.client

    def slow(method, url, body, headers):
        raise TimeoutError("timed out")

    with pytest.raises(CcpAppError) as exc:
        CcpApp(API, token, transport=slow).context()
    assert "did not answer within 30 s" in exc.value.error
    assert "not running" not in exc.value.error

    def garbled(method, url, body, headers):
        raise http.client.BadStatusLine("SSH-2.0-OpenSSH")

    with pytest.raises(CcpAppError) as exc:
        CcpApp(API, token, transport=garbled).context()
    assert exc.value.status is None and "invalid HTTP response" in exc.value.error


def test_calculate_continues_a_long_wait_on_the_job(token, monkeypatch):
    """The server caps one wait at 60 s; the client keeps polling the job."""
    calls = []

    def transport(method, url, body, headers):
        calls.append((method, urlsplit(url).path, json.loads(body) if body else None))
        active = len(calls) < 3
        job = {"id": 7, "active": active, "status": "running" if active else "ok"}
        return 200, {}, json.dumps(job).encode()

    job = CcpApp(API, token, transport=transport).calculate(case=1, wait=150)
    assert job["status"] == "ok"
    assert calls[0][2]["wait"] == 60
    assert [c[1] for c in calls[1:]] == ["/api/agent/v1/jobs/7"] * 2


def test_calculate_returns_a_running_monitoring_job_at_once(token):
    """A monitoring job stays active until stopped: do not poll it for ``wait``."""
    calls = []

    def transport(method, url, body, headers):
        calls.append(urlsplit(url).path)
        job = {"id": 8, "kind": "monitoring", "active": True, "status": "running"}
        return 200, {}, json.dumps(job).encode()

    app = CcpApp(API, token, transport=transport)
    job = app.calculate(case=1, wait=600, action="monitoring_start")
    assert job["active"] is True
    assert calls == ["/api/agent/v1/cases/1/calculate"]


def test_client_without_an_open_case(app):
    with pytest.raises(CcpAppError, match="no case is open"):
        app.results()


def test_client_create_export_import_duplicate_open(app, opened, tmp_path):
    path = tmp_path / "copy.ccp"
    content = app.export(path=path)
    assert path.read_bytes() == content and content
    created = app.create_case(ST, name="From file", file=path)
    assert created["app_type"] == ST and created["name"] == "From file"
    imported = Case.objects.get(pk=created["id"]).state
    # Only the session name follows the new case name.
    assert imported.pop("session_name") == "From file"
    assert imported == {k: v for k, v in opened.state.items() if k != "session_name"}
    empty = app.create_case(ST, name="Empty")
    assert empty["project"]["id"] == opened.project_id
    dup = app.duplicate(name="Dup")
    assert dup["name"] == "Dup" and dup["id"] != opened.pk
    assert app.open(dup["id"])["case"]["id"] == dup["id"]
    assert {c["id"] for c in app.cases()} >= {opened.pk, created["id"], dup["id"]}
    assert app.schema(ST, filter="speed")["fields"]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, value",
    [
        ("4.5", 4.5),
        ("3", 3),
        ("-1e3", -1000.0),
        ("bar", "bar"),
        ("true", True),
        ("false", False),
        ('{"a": 1}', {"a": 1}),
        ("[1, 2]", [1, 2]),
        ('"001"', "001"),
        ("", ""),
        ("null", "null"),
        ("NaN", "NaN"),
        ("Infinity", "Infinity"),
        ("kg/s", "kg/s"),
        ("4,5", "4,5"),
    ],
)
def test_cli_value_parsing(text, value):
    assert cli.parse_value(text) == value
    assert type(cli.parse_value(text)) is type(value)


def test_cli_assignments():
    assert cli.parse_assignments(["a=4.5", "b=bar", "c=true", "d=x=y"]) == {
        "a": 4.5,
        "b": "bar",
        "c": True,
        "d": "x=y",
    }
    with pytest.raises(cli.UsageError):
        cli.parse_assignments(["novalue"])


def test_cli_commands(capsys, token, opened, user, tmp_path):
    pk = opened.pk
    code, out, err = run_cli(capsys, token, "status")
    assert code == 0 and err is None
    assert out["api"]["user"] == user.get_username()
    assert out["context"]["presence"]["case"]["id"] == pk

    code, out, _ = run_cli(capsys, token, "get", "--keys", "flow_units")
    assert code == 0 and out["state"] == {"flow_units": "kg/s"}

    code, out, _ = run_cli(
        capsys,
        token,
        "set",
        "suction_temperature_point_1=300.5",
        "--note",
        "try 300.5 K",
        "--json",
        '{"suction_temperature_point_1": 1, "speed_point_1": 8454}',
    )
    assert code == 0, out
    assert out["changed"] == {
        "suction_temperature_point_1": ["300.13", "300.5"],
        "speed_point_1": ["8453.7", "8454"],
    }

    code, out, _ = run_cli(capsys, token, "calc", "--wait", "120")
    assert code == 0 and out["status"] == "succeeded", out
    job_id = out["id"]
    code, out, _ = run_cli(capsys, token, "job", str(job_id))
    assert code == 0 and out["id"] == job_id
    code, out, _ = run_cli(capsys, token, "results")
    assert code == 0 and out["available"] is True

    code, out, _ = run_cli(capsys, token, "figures")
    assert code == 0 and "head" in [f["id"] for f in out]
    fig_file = tmp_path / "head.json"
    code, out, _ = run_cli(capsys, token, "figure", "head", "--out", str(fig_file))
    assert code == 0 and out["ok"] is True
    assert json.loads(fig_file.read_text())["traces"]

    code, out, _ = run_cli(capsys, token, "undo")
    assert code == 0 and out["source"] == "undo"
    code, out, _ = run_cli(capsys, token, "revisions")
    assert code == 0 and [r["number"] for r in out] == [2, 1]

    code, out, _ = run_cli(capsys, token, "note", "Héad is fine ₜ")
    assert code == 0 and out["body"] == "Héad is fine ₜ"
    note_file = tmp_path / "note.txt"
    note_file.write_text("from a file\nline 2", encoding="utf-8")
    code, out, _ = run_cli(capsys, token, "note", "--file", str(note_file))
    assert code == 0 and out["body"] == "from a file\nline 2"
    code, out, _ = run_cli(capsys, token, "notes")
    assert code == 0 and len(out) == 2

    export = tmp_path / "case.ccp"
    code, out, _ = run_cli(capsys, token, "export", "--out", str(export))
    assert code == 0 and export.stat().st_size == out["bytes"] > 0
    code, out, _ = run_cli(
        capsys, token, "create", ST, "--from", str(export), "--name", "Again"
    )
    assert code == 0 and out["name"] == "Again"
    code, out, _ = run_cli(capsys, token, "duplicate", "--case", str(pk))
    assert code == 0 and out["app_type"] == ST
    code, out, _ = run_cli(capsys, token, "open", str(out["id"]))
    assert code == 0 and out["ok"] is True
    code, out, _ = run_cli(capsys, token, "cases", "--app-type", ST)
    assert code == 0 and len(out) == 3
    code, out, _ = run_cli(capsys, token, "schema", ST, "--filter", "speed")
    assert code == 0 and all(
        "speed" in f["key"] or "speed" in (f["label"] or "").lower()
        for f in out["fields"]
    )


def test_cli_errors(capsys, token, opened):
    code, out, err = run_cli(capsys, token, "set", "suction_pressur_point_1=1")
    assert code == 1 and out is None
    assert (
        err["status"] == 400 and "suction_pressur_point_1" in err["details"]["unknown"]
    )
    code, out, err = run_cli(capsys, token, "set", "suction_temperature_point_1=abc")
    assert code == 1 and err["status"] == 400 and err["details"]["invalid"]
    code, _, err = run_cli(capsys, token, "get", "--case", "999999")
    assert code == 1 and err["status"] == 404

    # Usage errors: exit 2, JSON on stderr.
    for argv in (
        ("set", "novalue"),
        ("set",),
        ("frobnicate",),
        ("get", "--case", "abc"),
        ("figure", "head", "--format", "png"),
        ("note",),
        ("set", "--json", "[1]"),
    ):
        code, out, err = run_cli(capsys, token, *argv)
        assert code == 2, argv
        assert out is None and err["error"], argv
    assert cli.main([]) == 2
    capsys.readouterr()


def test_cli_reports_a_stopped_app(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path))
    assert cli.main(["context"]) == 1
    out, err = capsys.readouterr()
    assert out == "" and "ccp app is not running" in json.loads(err)["error"]


def test_web_cli_dispatches_agent_and_no_agent(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path))
    with pytest.raises(SystemExit) as exc:
        web_cli.main(["agent", "context"])
    assert exc.value.code == 1
    capsys.readouterr()

    calls = []
    monkeypatch.setattr(launcher, "serve", lambda **kw: calls.append(("serve", kw)))
    monkeypatch.setattr(launcher, "desktop", lambda **kw: calls.append(("desk", kw)))
    web_cli.main(["serve", "--no-browser", "--no-agent"])
    web_cli.main(["serve", "--no-browser"])
    web_cli.main(["desktop", "--no-agent"])
    web_cli.main(["desktop"])
    assert [(name, kw["agent"]) for name, kw in calls] == [
        ("serve", False),
        ("serve", True),
        ("desk", False),
        ("desk", True),
    ]


# --------------------------------------------------------------------------
# MCP server
# --------------------------------------------------------------------------


def mcp_session(token, *messages):
    """Feed JSON-RPC lines through the server loop; the reply objects."""
    lines = [m if isinstance(m, str) else json.dumps(m) for m in messages]
    stdin = io.StringIO("\n".join(lines) + "\n")
    stdout = io.StringIO()
    code = mcp.serve(
        url=API,
        token=token,
        transport=django_transport(),
        stdin=stdin,
        stdout=stdout,
    )
    assert code == 0
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def _call(id, name, arguments=None):
    return {
        "jsonrpc": "2.0",
        "id": id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


def _payload(reply):
    return json.loads(reply["result"]["content"][0]["text"])


def test_mcp_protocol(token, opened):
    replies = mcp_session(
        token,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        "",
        {"jsonrpc": "2.0", "id": "two", "method": "ping"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 4, "method": "resources/list"},
        "{not json",
        _call(5, "ccp_nope"),
        _call(6, "ccp_context"),
    )
    assert [r["id"] for r in replies] == [1, "two", 3, 4, None, 5, 6]
    init = replies[0]["result"]
    assert init["protocolVersion"] == "2025-06-18"
    assert init["capabilities"]["tools"] and init["serverInfo"]["name"] == "ccp"
    assert replies[1]["result"] == {}
    names = {t["name"] for t in replies[2]["result"]["tools"]}
    assert names == {
        "ccp_context",
        "ccp_get_case",
        "ccp_schema",
        "ccp_set_values",
        "ccp_calculate",
        "ccp_job",
        "ccp_results",
        "ccp_figure",
        "ccp_undo",
        "ccp_note",
        "ccp_open_case",
        "ccp_duplicate",
    }
    for tool in replies[2]["result"]["tools"]:
        assert tool["inputSchema"]["type"] == "object" and tool["description"]
    assert replies[3]["error"]["code"] == -32601
    assert replies[4]["error"]["code"] == -32700
    assert replies[5]["error"]["code"] == -32602
    assert replies[6]["result"]["isError"] is False
    assert _payload(replies[6])["presence"]["case"]["id"] == opened.pk
    assert all(r["jsonrpc"] == "2.0" for r in replies)


def test_mcp_tools(token, opened):
    pk = opened.pk
    replies = mcp_session(
        token,
        _call(1, "ccp_get_case", {"keys": ["flow_units"]}),
        _call(
            2,
            "ccp_set_values",
            {"values": {"suction_temperature_point_1": 300.5}, "note": "why"},
        ),
        _call(3, "ccp_set_values", {"values": {"bogus_key": 1}, "note": "x"}),
        _call(4, "ccp_calculate", {"wait": 120}),
        _call(5, "ccp_results"),
        _call(6, "ccp_figure"),
        _call(7, "ccp_figure", {"id": "head"}),
        _call(8, "ccp_figure", {"id": "head", "format": "png"}),
        _call(9, "ccp_undo"),
        _call(10, "ccp_note", {"body": "done"}),
        _call(11, "ccp_schema", {"app_type": ST, "filter": "speed"}),
        _call(12, "ccp_get_case", {"case": 999999}),
        _call(13, "ccp_note", {}),
        _call(14, "ccp_duplicate", {"name": "Copy"}),
    )
    assert [r["id"] for r in replies] == list(range(1, 15))
    errors = {r["id"] for r in replies if r["result"]["isError"]}
    assert errors == {3, 12, 13}
    assert _payload(replies[0])["state"] == {"flow_units": "kg/s"}
    assert _payload(replies[1])["revision"] == 1
    bad = _payload(replies[2])
    assert bad["status"] == 400 and "bogus_key" in bad["details"]["unknown"]
    job = _payload(replies[3])
    assert job["status"] == "succeeded"
    assert _payload(replies[4])["available"] is True
    assert "head" in [f["id"] for f in _payload(replies[5])]
    assert _payload(replies[6])["traces"]
    png = replies[7]["result"]["content"][0]
    if png["type"] == "text":
        fallback = json.loads(png["text"])
        assert "kaleido" in fallback["png_unavailable"]
        assert fallback["figure"]["traces"]
    else:
        assert png["type"] == "image" and png["mimeType"] == "image/png"
    assert _payload(replies[8])["source"] == "undo"
    assert _payload(replies[9])["body"] == "done"
    assert _payload(replies[10])["fields"]
    assert _payload(replies[11])["status"] == 404
    assert "invalid arguments" in _payload(replies[12])["error"]
    assert _payload(replies[13])["name"] == "Copy"
    opened.refresh_from_db()
    assert opened.revision == 2 and opened.agent_notes.count() == 1
    assert pk == opened.pk


def test_mcp_tool_error_when_app_not_running(monkeypatch, tmp_path):
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path))
    stdin = io.StringIO(json.dumps(_call(1, "ccp_context")) + "\n")
    stdout = io.StringIO()
    assert mcp.serve(stdin=stdin, stdout=stdout) == 0
    (reply,) = [json.loads(x) for x in stdout.getvalue().splitlines()]
    assert reply["id"] == 1 and reply["result"]["isError"] is True
    assert "not running" in _payload(reply)["error"]


def test_mcp_batch_with_a_bad_member_does_not_end_the_server(token, opened):
    replies = mcp_session(
        token,
        [
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": [1]},
            {"jsonrpc": "2.0", "id": 7, "method": "ping"},
        ],
        {"jsonrpc": "2.0", "id": 8, "method": "initialize", "params": "x"},
        {"jsonrpc": "2.0", "id": 9, "method": "ping"},
    )
    batch, init, ping = replies
    assert [r["id"] for r in batch] == [6, 7]
    assert batch[0]["error"]["code"] == -32602 and batch[1]["result"] == {}
    assert init["error"]["code"] == -32602
    assert ping == {"jsonrpc": "2.0", "id": 9, "result": {}}


def _cp1252_stream(data=b""):
    """A stdio-like stream in the Windows ANSI code page."""
    return io.TextIOWrapper(io.BytesIO(data), encoding="cp1252", newline="")


def test_mcp_reads_and_writes_utf8_on_a_cp1252_console(token, opened, monkeypatch):
    line = json.dumps(
        _call(1, "ccp_note", {"body": "ÁGUA kgf/cm²", "case": opened.pk}),
        ensure_ascii=False,
    )
    stdin = _cp1252_stream((line + "\n").encode("utf-8"))
    stdout = _cp1252_stream()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    assert mcp.serve(url=API, token=token, transport=django_transport()) == 0
    stdout.flush()
    (reply,) = [json.loads(x) for x in stdout.buffer.getvalue().splitlines()]
    assert reply["result"]["isError"] is False, reply
    assert _payload(reply)["body"] == "ÁGUA kgf/cm²"


def test_cli_writes_utf8_on_a_cp1252_console(token, opened, monkeypatch):
    stdout = _cp1252_stream()
    monkeypatch.setattr(sys, "stdout", stdout)
    code = cli.main(
        ["--url", API, "--token", token, "set", "flow_units=m³/h", "--note", "² é"],
        transport=django_transport(),
    )
    assert code == 0
    stdout.flush()
    out = json.loads(stdout.buffer.getvalue().decode("utf-8"))
    assert out["changed"]["flow_units"][1] == "m³/h"


def test_cli_mcp_command(capsys, monkeypatch, token):
    monkeypatch.setattr(
        sys, "stdin", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"ping"}\n')
    )
    assert cli.main(["--url", API, "--token", token, "mcp"]) == 0
    out, _ = capsys.readouterr()
    assert json.loads(out) == {"jsonrpc": "2.0", "id": 1, "result": {}}


# --------------------------------------------------------------------------
# Launcher: the desktop agent session
# --------------------------------------------------------------------------


def test_launcher_writes_and_removes_the_agent_file(
    monkeypatch, tmp_path, settings, capsys
):
    settings.CCP_PROFILE = "desktop"
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path))
    exits = []
    monkeypatch.setattr(launcher.atexit, "register", exits.append)

    path = launcher.start_agent_session("http://127.0.0.1:8123/")
    assert path == tmp_path / "agent.json"
    assert "agent API: http://127.0.0.1:8123/api/agent/v1/" in capsys.readouterr().out
    data = discovery.read(path)
    first_plain = data["token"]
    first = AgentToken.authenticate(first_plain)
    assert first.owner.username == "local" and first.kind == AgentToken.DESKTOP
    assert first.can_write and data["pid"] == os.getpid()
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    # The client finds the app through the file and the token works.
    app = connect(transport=django_transport())
    assert app.url == "http://127.0.0.1:8123/api/agent/v1/"
    root = app.root()
    assert root["user"] == "local" and root["token"]["kind"] == "desktop"

    # A restart replaces the token; the old one stops working.
    launcher.start_agent_session("http://0.0.0.0:8124/")
    capsys.readouterr()
    data = discovery.read(path)
    assert data["url"] == "http://127.0.0.1:8124/"
    second_plain = data["token"]
    assert AgentToken.authenticate(first_plain) is None
    assert AgentToken.authenticate(second_plain) is not None
    assert AgentToken.objects.filter(kind=AgentToken.DESKTOP).count() == 1

    # At exit: file and token are gone.
    assert len(exits) == 2
    for stop in exits:
        stop()
    assert not path.exists()
    assert AgentToken.authenticate(second_plain) is None


def test_launcher_skips_the_agent_file_when_hosted(monkeypatch, tmp_path, settings):
    settings.CCP_PROFILE = "hosted"
    monkeypatch.setenv("CCP_DATA_DIR", str(tmp_path))
    assert launcher.start_agent_session("http://127.0.0.1:8123/") is None
    assert not (tmp_path / "agent.json").exists()
    assert not AgentToken.objects.exists()
