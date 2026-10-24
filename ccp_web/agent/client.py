"""Python client for the agent API of a running ccp app (stdlib only).

    from ccp_web.agent.client import connect

    app = connect()                      # finds the running app (discovery.py)
    app.context()["presence"]["case"]    # what the user has open
    app.set({"suction_pressure_point_1": 4.5}, note="try 4.5 bar")
    job = app.calculate(wait=90)
    app.results()

Every method that takes ``case`` defaults to the case the user has open in
the app (from ``context()``), because the agent works on what the user is
looking at. Errors raise ``CcpAppError(status, error, details)`` carrying the
API's JSON error.

The module must not import Django: agents use it from environments that
install ccp without the ``web`` extra. ``transport`` replaces HTTP in tests:
``transport(method, url, body, headers) -> (status, headers, body)``.
"""

import http.client
import json
import mimetypes
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import discovery

DEFAULT_TIMEOUT = 30
# The server caps one calculate or job wait at 60 s (each holds one of its
# request threads); longer waits continue on ``job``.
MAX_CALCULATE_WAIT = 60
MAX_JOB_WAIT = 60


class CcpAppError(Exception):
    """An API error (``status`` is None when the app could not be reached)."""

    def __init__(self, status, error, details=None):
        super().__init__(error)
        self.status = status
        self.error = error
        self.details = details

    def as_dict(self):
        out = {"error": self.error, "status": self.status}
        if self.details:
            out["details"] = self.details
        return out

    def __str__(self):
        prefix = f"HTTP {self.status}: " if self.status else ""
        return prefix + str(self.error)


def _urllib_transport(method, url, body, headers, timeout):
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _multipart(fields, files):
    """``(content_type, body)`` of a multipart/form-data request."""
    boundary = "ccp-" + secrets.token_hex(16)
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )
    for name, (filename, content) in files.items():
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        safe = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="{name}"; filename="{safe}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode()
            + content
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


class CcpApp:
    """A connection to one running ccp app (URL of the agent API + token)."""

    def __init__(self, url, token, transport=None, source=None):
        self.url = discovery.api_url(url)
        self.token = token
        self.source = source
        self._transport = transport

    @classmethod
    def connect(cls, url=None, token=None, transport=None):
        """Connect to the app given, or the one ``discovery.resolve`` finds.

        Nothing is sent yet; the first call fails with ``CcpAppError`` when the
        app is not reachable.
        """
        try:
            api, token, source = discovery.resolve(url, token)
        except discovery.DiscoveryError as exc:
            raise CcpAppError(None, str(exc)) from None
        return cls(api, token, transport=transport, source=source)

    def __repr__(self):
        return f"CcpApp({self.url!r})"

    # ----------------------------------------------------------------------
    # HTTP
    # ----------------------------------------------------------------------

    def request(self, method, path, data=None, params=None, timeout=None, raw=False):
        """Call ``path`` (relative to the API root); the decoded JSON body.

        ``data`` is sent as JSON, or as multipart when it is a
        ``(fields, files)`` tuple. ``raw=True`` returns the response bytes.
        """
        url = self.url + path.lstrip("/")
        params = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "*/*"}
        body = None
        if isinstance(data, tuple):
            headers["Content-Type"], body = _multipart(*data)
        elif data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        timeout = timeout or DEFAULT_TIMEOUT
        try:
            if self._transport is not None:
                status, resp_headers, content = self._transport(
                    method, url, body, headers
                )
            else:
                status, resp_headers, content = _urllib_transport(
                    method, url, body, headers, timeout
                )
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                # socket.timeout is TimeoutError: the app is there, but busy.
                raise CcpAppError(
                    None,
                    f"the ccp app at {self.url} did not answer within "
                    f"{timeout:.0f} s; it may still be working (check `job <id>` "
                    "or `context`)",
                ) from None
            if isinstance(exc, http.client.HTTPException):
                raise CcpAppError(
                    None,
                    f"the ccp app at {self.url} sent an invalid HTTP response "
                    f"({type(exc).__name__}: {exc}); is that the ccp app, and is "
                    "it still running?",
                ) from None
            raise CcpAppError(
                None,
                f"cannot reach the ccp app at {self.url} ({reason}); "
                f"{discovery.NOT_RUNNING}",
            ) from None
        if not 200 <= status < 300:
            raise self._error(status, content)
        if raw:
            return content
        if not content:
            return None
        try:
            return json.loads(content)
        except ValueError:
            raise CcpAppError(
                status, f"the app returned non-JSON content for {path}"
            ) from None

    @staticmethod
    def _error(status, content):
        try:
            body = json.loads(content)
        except (ValueError, TypeError):
            body = None
        if isinstance(body, dict) and "error" in body:
            return CcpAppError(status, body["error"], body.get("details"))
        text = (content or b"").decode("utf-8", "replace").strip()[:500]
        return CcpAppError(status, text or f"HTTP {status}")

    def get(self, path, **params):
        return self.request("GET", path, params=params)

    def post(self, path, data=None, timeout=None):
        return self.request(
            "POST", path, data=data if data is not None else {}, timeout=timeout
        )

    # ----------------------------------------------------------------------
    # Context
    # ----------------------------------------------------------------------

    def root(self):
        """API version, user, token scope and the app types."""
        return self.get("")

    def context(self):
        """What the user has open (``presence``) and the recent cases."""
        return self.get("context")

    def case_id(self, case=None):
        """``case`` as an id, or the id of the case the user has open."""
        if isinstance(case, dict):
            case = case.get("id")
        if case not in (None, ""):
            try:
                return int(case)
            except (TypeError, ValueError):
                raise CcpAppError(None, f"case must be an id, got {case!r}") from None
        current = (self.context().get("presence") or {}).get("case")
        if not current:
            raise CcpAppError(
                None,
                "no case is open in the app: open one in the browser, or pass a "
                "case id (see `cases`)",
            )
        return current["id"]

    def open(self, case):
        """Make the user's browser open ``case`` (within a few seconds)."""
        return self.post("context/open", {"case": self.case_id(case)})

    def projects(self):
        return self.get("projects")

    def cases(self, project=None, app_type=None):
        return self.get("cases", project=project, app_type=app_type)

    # ----------------------------------------------------------------------
    # Cases
    # ----------------------------------------------------------------------

    @staticmethod
    def _keys(keys):
        if keys is None or isinstance(keys, str):
            return keys
        return ",".join(keys)

    def case(self, pk=None, keys=None):
        """Summary, state, files, artifacts, latest jobs of a case."""
        return self.get(f"cases/{self.case_id(pk)}", keys=self._keys(keys))

    def state(self, case=None, keys=None):
        """``{revision, state}``; ``keys`` limits the state to those keys."""
        return self.get(f"cases/{self.case_id(case)}/state", keys=self._keys(keys))

    def set(self, values, note="", case=None):
        """Write ``values`` as one undoable revision of the case."""
        if not isinstance(values, dict):
            raise CcpAppError(None, "values must be a dict of state keys")
        return self.request(
            "PATCH",
            f"cases/{self.case_id(case)}/state",
            data={"values": values, "note": note or ""},
        )

    def calculate(self, case=None, wait=90, **params):
        """Start the page's calculation; wait up to ``wait`` seconds for it.

        Waits longer than one server call allows continue on ``job``. A
        monitoring job runs until stopped: it is returned as soon as the
        server answers (within seconds), not polled for the whole ``wait``.
        """
        wait = max(0.0, float(wait or 0))
        first = min(wait, MAX_CALCULATE_WAIT)
        job = self.post(
            f"cases/{self.case_id(case)}/calculate",
            {"params": params, "wait": first},
            timeout=first + 30,
        )
        remaining = wait - first
        while job.get("active") and job.get("kind") != "monitoring" and remaining > 0:
            step = min(remaining, MAX_JOB_WAIT)
            job = self.job(job["id"], wait=step)
            remaining -= step
        return job

    def job(self, id, wait=0):
        """A job; ``wait`` long-polls until it finishes (≤ 60 s per call)."""
        wait = max(0.0, min(float(wait or 0), MAX_JOB_WAIT))
        return self.request(
            "GET", f"jobs/{int(id)}", params={"wait": wait or None}, timeout=wait + 30
        )

    def cancel(self, id):
        return self.post(f"jobs/{int(id)}/cancel")

    def results(self, case=None):
        """The page's results (``{available: false, reason}`` before a run)."""
        return self.get(f"cases/{self.case_id(case)}/results")

    def figures(self, case=None):
        """``[{id, title, section}]`` of the case's figures."""
        return self.get(f"cases/{self.case_id(case)}/figures")

    def figure(self, id, format="data", case=None, template=False):
        """One figure: compact data, plotly JSON, or PNG bytes."""
        path = f"cases/{self.case_id(case)}/figures/{urllib.parse.quote(str(id))}"
        params = {"format": format, "template": "1" if template else None}
        return self.request("GET", path, params=params, raw=format == "png")

    def revisions(self, case=None):
        """The case's agent revisions, newest first."""
        return self.get(f"cases/{self.case_id(case)}/revisions")

    def undo(self, revision_id=None, case=None):
        """Undo an agent revision (default: the newest one not undone)."""
        data = {"revision_id": revision_id} if revision_id is not None else {}
        return self.post(f"cases/{self.case_id(case)}/undo", data)

    def note(self, body, case=None):
        """Post a note the user sees on the case's page."""
        return self.post(f"cases/{self.case_id(case)}/notes", {"body": body})

    def notes(self, case=None):
        return self.get(f"cases/{self.case_id(case)}/notes")

    def duplicate(self, case=None, name=None):
        """Copy a case (new case summary)."""
        data = {"name": name} if name else {}
        return self.post(f"cases/{self.case_id(case)}/duplicate", data)

    def export(self, case=None, path=None):
        """The case as ``.ccp`` bytes; also written to ``path`` when given."""
        content = self.request(
            "GET", f"cases/{self.case_id(case)}/export", raw=True, timeout=120
        )
        if path is not None:
            Path(path).write_bytes(content)
        return content

    def create_case(
        self, app_type=None, name=None, project=None, state=None, file=None
    ):
        """Create a case: empty (``app_type``, optional ``state``) or from a
        ``.ccp`` file (``file`` = path or ``(filename, bytes)``)."""
        if file is not None:
            if isinstance(file, tuple):
                filename, content = file
            else:
                filename, content = Path(file).name, Path(file).read_bytes()
            fields = {
                k: v
                for k, v in {
                    "name": name,
                    "project": project,
                    "app_type": app_type,
                }.items()
                if v not in (None, "")
            }
            return self.request(
                "POST",
                "cases",
                data=(fields, {"file": (filename, content)}),
                timeout=300,
            )
        if not app_type:
            raise CcpAppError(None, "app_type is required without a file")
        data = {"app_type": app_type}
        for key, value in (("name", name), ("project", project), ("state", state)):
            if value not in (None, ""):
                data[key] = value
        return self.post("cases", data)

    def schema(self, app_type, filter=None):
        """The state keys of an app type with kinds, options and units."""
        return self.get(f"schema/{app_type}", filter=filter)


def connect(url=None, token=None, transport=None):
    """``CcpApp.connect``: the running app, found through ``discovery``."""
    return CcpApp.connect(url, token, transport=transport)
