"""Where a running ccp app is: the agent file the launcher writes.

The desktop launcher issues a fresh bearer token at every start and writes it,
with the server URL and its pid, to ``<data dir>/agent.json`` (mode 0600).
Agent-side tools (``client.py``, the ``ccp-web agent`` CLI, the MCP server)
read it, so the agent needs no configuration on the same machine.

This module is stdlib only and must stay importable without Django or
platformdirs: the agent side runs in environments that install ccp without the
``web`` extra. ``platformdirs`` is used when importable, else the same paths
are computed here.

Resolution order of the URL and token (each field separately):

1. explicit arguments;
2. ``CCP_AGENT_URL`` and ``CCP_AGENT_TOKEN``;
3. the file named by ``CCP_AGENT_FILE``;
4. ``agent_file()`` (``AGENT_FILE``).

Explicit values win, so on WSL ``CCP_AGENT_FILE`` can point at the Windows
file while ``CCP_AGENT_URL`` overrides the host.
"""

import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path

APP_NAME = "ccp"
FILE_NAME = "agent.json"
API_PATH = "api/agent/v1/"
NOT_RUNNING = "ccp app is not running — start it with `ccp-web serve` / `ccp-app`"


class DiscoveryError(RuntimeError):
    """No usable app URL and token could be found."""


def _fallback_data_dir():
    """``platformdirs.user_data_dir("ccp", "ccp")`` without platformdirs."""
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / APP_NAME / APP_NAME
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME", "").strip() or str(home / ".local" / "share")
    return Path(base) / APP_NAME


def data_dir():
    """The desktop data directory: ``$CCP_DATA_DIR`` or the user data dir.

    The same rule as ``ccp_web.settings.desktop``, so the launcher and the
    agent tools agree on where the agent file is.
    """
    override = os.environ.get("CCP_DATA_DIR")
    if override:
        return Path(override)
    try:
        from platformdirs import user_data_dir
    except ImportError:
        return _fallback_data_dir()
    return Path(user_data_dir(APP_NAME, APP_NAME))


def agent_file():
    """The default agent file, ``data_dir() / "agent.json"``."""
    return data_dir() / FILE_NAME


def __getattr__(name):
    # ``AGENT_FILE`` follows ``CCP_DATA_DIR`` at the time it is read.
    if name == "AGENT_FILE":
        return agent_file()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def api_url(url):
    """The agent API root for ``url``: the server root or the API root itself."""
    url = url.strip()
    if not url.endswith("/"):
        url += "/"
    if url.endswith("/" + API_PATH):
        return url
    return url + API_PATH


def write(url, token, pid=None, path=None):
    """Write the agent file atomically, readable by the owner only.

    The file holds a bearer token, so it is created 0600 in a temporary file
    next to the target and moved into place: a reader never sees a partial
    file or a moment of wider permissions.
    """
    path = Path(path) if path is not None else agent_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "url": url,
        "api_url": api_url(url),
        "token": token,
        "pid": os.getpid() if pid is None else pid,
        "host": socket.gethostname(),
        "platform": sys.platform,
        "created": time.time(),
    }
    fd, tmp = tempfile.mkstemp(prefix=".agent-", suffix=".json", dir=path.parent)
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def read(path=None):
    """The agent file's content, or None when it is missing or unreadable."""
    path = Path(path) if path is not None else agent_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def remove_if_owned(pid=None, path=None):
    """Delete the agent file if it was written by ``pid`` (default: this process).

    A second app started on the same data dir rewrites the file; the first
    one must not delete it when it exits.
    """
    path = Path(path) if path is not None else agent_file()
    pid = os.getpid() if pid is None else pid
    data = read(path)
    if data is None or data.get("pid") != pid:
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def pid_alive(pid):
    """Best effort: False only when ``pid`` surely does not exist.

    Windows is not checked (``os.kill`` would terminate the process there).
    """
    if not isinstance(pid, int) or pid <= 0 or os.name != "posix":
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        # EPERM: it exists but belongs to someone else.
        return True
    return True


def _same_machine(data):
    """A pid is only meaningful on the machine (and OS) that wrote it.

    A WSL shell reading the Windows app's file cannot see Windows pids.
    """
    return data.get("host") in (None, socket.gethostname()) and data.get(
        "platform"
    ) in (None, sys.platform)


def resolve(url=None, token=None):
    """``(api_url, token, source)`` of the app to talk to.

    Raises ``DiscoveryError`` with a message an agent can show the user when
    nothing is configured, the file is missing, or the app that wrote it is no
    longer running.
    """
    url = url or os.environ.get("CCP_AGENT_URL") or None
    token = token or os.environ.get("CCP_AGENT_TOKEN") or None
    if url and token:
        return api_url(url), token, "arguments or environment"
    env_file = os.environ.get("CCP_AGENT_FILE")
    path = Path(env_file) if env_file else agent_file()
    data = read(path)
    if data is None:
        if url and not token:
            raise DiscoveryError(
                f"CCP_AGENT_URL is set but no token: set CCP_AGENT_TOKEN, or "
                f"CCP_AGENT_FILE to the app's agent file (no file at {path})"
            )
        raise DiscoveryError(f"{NOT_RUNNING} (no agent file at {path})")
    pid = data.get("pid")
    if not url and _same_machine(data) and not pid_alive(pid):
        raise DiscoveryError(
            f"{NOT_RUNNING} (the agent file {path} was left by process {pid}, "
            "which is no longer running)"
        )
    url = url or data.get("api_url") or data.get("url")
    token = token or data.get("token")
    if not url or not token:
        raise DiscoveryError(f"the agent file {path} has no url or token")
    return api_url(url), token, str(path)
