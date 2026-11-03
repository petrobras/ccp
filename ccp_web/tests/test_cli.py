"""``ccp-web`` / ``python -m ccp_web`` / ``ccp-app``: what starts, and the
messages when the desktop window or the web extra is not available."""

import logging
import sys
import types

import pytest

from ccp.app import cli as app_cli
from ccp_web import cli, launcher


@pytest.fixture
def launched(monkeypatch):
    """Record serve() and desktop() calls instead of starting the app."""
    calls = []
    for name in ("serve", "desktop"):
        monkeypatch.setattr(
            launcher, name, lambda name=name, **kw: calls.append((name, kw))
        )
    return calls


def fake_guilib(monkeypatch, initialize):
    module = types.ModuleType("webview.guilib")
    module.initialize = initialize
    monkeypatch.setitem(sys.modules, "webview", types.ModuleType("webview"))
    monkeypatch.setitem(sys.modules, "webview.guilib", module)


def test_no_command_runs_app(monkeypatch):
    calls = []
    monkeypatch.setattr(launcher, "app", lambda **kw: calls.append(kw))
    cli.main([])
    assert calls == [{}]


def test_app_opens_the_window_when_available(monkeypatch, launched):
    monkeypatch.setattr(launcher, "desktop_unavailable", lambda: None)
    launcher.app(debug=True, agent=False)
    assert launched == [("desktop", {"debug": True, "agent": False})]


def test_app_falls_back_to_the_browser(monkeypatch, launched, capsys):
    monkeypatch.setattr(launcher, "desktop_unavailable", lambda: "no toolkit")
    launcher.app(agent=False)
    assert launched == [("serve", {"agent": False})]
    assert "no toolkit; opening ccp in the browser" in capsys.readouterr().err


def test_desktop_command_fails_before_starting(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "desktop_unavailable", lambda: "no toolkit")
    monkeypatch.setattr(launcher, "prepare", pytest.fail)
    with pytest.raises(SystemExit) as exc:
        launcher.desktop()
    assert exc.value.code == 1
    assert "ccp-web serve" in capsys.readouterr().err


@pytest.fixture
def unavailable(monkeypatch):
    """desktop_unavailable() without its cache, on a Linux desktop."""
    launcher.desktop_unavailable.cache_clear()
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(launcher.importlib.util, "find_spec", lambda name: True)
    yield launcher.desktop_unavailable
    launcher.desktop_unavailable.cache_clear()


def test_probe_gui_without_pywebview(monkeypatch):
    monkeypatch.setitem(sys.modules, "webview.guilib", None)
    assert "pywebview is not installed" in launcher.probe_gui()


def test_probe_gui_mutes_pywebview_tracebacks(monkeypatch, capsys):
    def initialize():
        try:
            raise ModuleNotFoundError("No module named 'gi'")
        except ModuleNotFoundError:
            logging.getLogger("pywebview").exception("GTK cannot be loaded")
        raise RuntimeError("You must have either QT or GTK")

    fake_guilib(monkeypatch, initialize)
    assert "QT or GTK" in launcher.probe_gui()
    assert "GTK cannot be loaded" not in capsys.readouterr().err
    assert not logging.getLogger("pywebview").disabled


def test_probe_gui_available(monkeypatch):
    fake_guilib(monkeypatch, lambda: None)
    assert launcher.probe_gui() is None


def test_desktop_unavailable_without_pywebview(unavailable, monkeypatch):
    monkeypatch.setattr(launcher.importlib.util, "find_spec", lambda name: None)
    assert "pywebview is not installed" in unavailable()


def test_desktop_unavailable_without_a_display(unavailable, monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert unavailable() == "no graphical display"


@pytest.mark.parametrize(
    "code, reason",
    [
        ("pass", None),
        ("print('pywebview found no GUI toolkit (x)'); raise SystemExit(1)", "(x)"),
        # Qt aborts the process when it cannot reach the display.
        ("import os; os.abort()", "failed to start"),
    ],
)
def test_desktop_unavailable_probes_in_a_child(unavailable, monkeypatch, code, reason):
    monkeypatch.setattr(
        launcher, "_probe_command", lambda: [sys.executable, "-c", code]
    )
    result = unavailable()
    assert result is None if reason is None else reason in result


def test_probe_gui_command(monkeypatch, capsys):
    monkeypatch.setattr(launcher, "probe_gui", lambda: "no toolkit")
    with pytest.raises(SystemExit) as exc:
        cli.main(["probe-gui"])
    assert exc.value.code == 1
    assert capsys.readouterr().out == "no toolkit\n"


@pytest.mark.parametrize("argv", [[], ["serve"], ["worker"], ["manage", "check"]])
def test_missing_web_extra_is_reported(monkeypatch, argv):
    monkeypatch.setattr(
        cli.importlib.util,
        "find_spec",
        lambda name: None if name == "django_htmx" else True,
    )
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert "ccp-performance[web]" in str(exc.value.code)
    assert "Python >= 3.10" in str(exc.value.code)


def test_ccp_app_without_arguments_runs_app(monkeypatch):
    calls = []
    monkeypatch.setattr(launcher, "app", lambda **kw: calls.append(kw))
    monkeypatch.setattr(sys, "argv", ["ccp-app"])
    app_cli.main()
    assert calls == [{}]


@pytest.mark.parametrize("probe, command", [(None, "desktop"), ("no toolkit", "serve")])
def test_ccp_app_with_arguments_checks_the_window(monkeypatch, probe, command):
    calls = []
    monkeypatch.setattr(cli, "main", calls.append)
    monkeypatch.setattr(launcher, "desktop_unavailable", lambda: probe)
    monkeypatch.setattr(sys, "argv", ["ccp-app", "--no-agent"])
    app_cli.main()
    assert calls == [[command, "--no-agent"]]


def test_ccp_app_without_the_web_extra(monkeypatch, capsys):
    monkeypatch.setattr(cli, "web_extra_installed", lambda: False)
    monkeypatch.setitem(sys.modules, "streamlit", None)
    monkeypatch.setattr(sys, "argv", ["ccp-app"])
    with pytest.raises(SystemExit) as exc:
        app_cli.main()
    assert "ccp-performance[web]" in str(exc.value.code)
