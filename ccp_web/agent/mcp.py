"""Minimal MCP stdio server over the agent API (stdlib only).

    claude mcp add ccp -- ccp-web agent mcp

JSON-RPC 2.0, one message per line on stdin/stdout (MCP stdio transport,
protocol ``2025-06-18``). It handles ``initialize``, ``ping``, ``tools/list``
and ``tools/call``; notifications get no reply and other methods get
``-32601``. Each tool wraps one ``CcpApp`` call. A failing tool (app not
running, invalid value...) is a normal result with ``isError: true`` and the
API's error JSON as text, so the model can read and fix it.

The app is found again on every tool call: the desktop app issues a new token
each time it starts, so a long-lived MCP server keeps working across app
restarts. Nothing here imports Django.
"""

import base64
import json
import sys

from .client import CcpApp, CcpAppError

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = (PROTOCOL_VERSION, "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "ccp", "title": "ccp app", "version": "1"}

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

INSTRUCTIONS = (
    "Tools for the ccp (centrifugal compressor performance) app the user has "
    "open. Start with ccp_context to see the open case. Tools that take `case` "
    "default to that case. ccp_set_values edits the open case as one revision "
    "the user can undo in the browser: one call per logical change, always "
    "with a short `note`. Then ccp_calculate (it waits) and ccp_results. Use "
    "ccp_schema to discover state keys; a number is in the unit held by its "
    "field's `units_key`. Read ccp_context once and pass `case` on every later "
    "call, so a change of window cannot switch cases between your calls. "
    "ccp_calculate waits at most 45 s; continue an `active: true` job with "
    "ccp_job. Never ask for or send passwords or API keys; runs that need the "
    "PI password must be started in the browser."
)
# Below the 60 s request timeout of common MCP clients: this server handles
# one request at a time and sends no progress, so a longer call would time
# out in the client and block every request after it.
MAX_TOOL_WAIT = 45

_CASE = {
    "type": "integer",
    "description": "case id (default: the case the user has open)",
}


def _schema(properties=None, required=()):
    return {
        "type": "object",
        "properties": properties or {},
        "required": list(required),
        "additionalProperties": False,
    }


def _wait(value, limit, default=None):
    """Seconds to wait: ``value`` (default ``limit``) capped at ``limit``."""
    if value is None:
        return limit if default is None else default
    return max(0.0, min(float(value), limit))


def _keys(value):
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return value


class Content(list):
    """MCP content blocks a tool returns as they are (not as JSON text)."""


def _figure(app, args):
    if not args.get("id"):
        return app.figures(args.get("case"))
    fmt = args.get("format") or "data"
    if fmt != "png":
        return app.figure(args["id"], format=fmt, case=args.get("case"))
    try:
        png = app.figure(args["id"], format="png", case=args.get("case"))
    except CcpAppError as exc:
        if exc.status != 501:
            raise
        data = app.figure(args["id"], format="data", case=args.get("case"))
        return {"png_unavailable": exc.error, "figure": data}
    return Content(
        [
            {
                "type": "image",
                "data": base64.b64encode(png).decode("ascii"),
                "mimeType": "image/png",
            }
        ]
    )


# name -> (description, input schema, call(app, arguments))
TOOLS = {
    "ccp_context": (
        "What the user has open in the ccp app (case, page, section; "
        "`stale` when the browser has not reported for 2 min) and recent cases.",
        _schema(),
        lambda app, a: app.context(),
    ),
    "ccp_get_case": (
        "A case: summary, input state (all keys, or `keys`), files, latest "
        "jobs and whether results exist.",
        _schema(
            {
                "case": _CASE,
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "only these state keys",
                },
            }
        ),
        lambda app, a: app.case(a.get("case"), keys=_keys(a.get("keys"))),
    ),
    "ccp_schema": (
        "State keys of an app type (straight_through, back_to_back, "
        "curves_conversion, performance_evaluation, curves_digitizer) with "
        "kind, default, options, label and parameter units.",
        _schema(
            {
                "app_type": {"type": "string"},
                "filter": {
                    "type": "string",
                    "description": "only keys or labels containing this text",
                },
            },
            required=("app_type",),
        ),
        lambda app, a: app.schema(a["app_type"], filter=a.get("filter")),
    ),
    "ccp_set_values": (
        "Change inputs of the case (the open one by default) as ONE revision "
        "the user can undo in the browser. Unknown keys or invalid values are "
        "rejected with suggestions. Returns {revision, changed: {key: [old, "
        "new]}, warnings, revision_id}.",
        _schema(
            {
                "values": {
                    "type": "object",
                    "description": 'state key -> value, e.g. {"speed": 9000, '
                    '"speed_unit": "rpm"}',
                },
                "note": {
                    "type": "string",
                    "description": "one line shown to the user: why",
                },
                "case": _CASE,
            },
            required=("values", "note"),
        ),
        lambda app, a: app.set(a["values"], note=a.get("note", ""), case=a.get("case")),
    ),
    "ccp_calculate": (
        "Start the page's calculation and wait for it (up to 45 s). Returns "
        "the job; when it is still `active`, continue with ccp_job. Field "
        "errors come back as an error.",
        _schema(
            {
                "case": _CASE,
                "wait": {"type": "number", "description": "seconds (≤ 45)"},
                "params": {
                    "type": "object",
                    "description": "app-specific, see ccp_schema calculate_params",
                },
            }
        ),
        lambda app, a: app.calculate(
            a.get("case"),
            wait=_wait(a.get("wait"), MAX_TOOL_WAIT),
            **(a.get("params") or {}),
        ),
    ),
    "ccp_job": (
        "A job's status, progress, error and result; `wait` long-polls up to "
        "45 s until it finishes.",
        _schema(
            {"id": {"type": "integer"}, "wait": {"type": "number"}}, required=("id",)
        ),
        lambda app, a: app.job(a["id"], wait=_wait(a.get("wait"), MAX_TOOL_WAIT, 0)),
    ),
    "ccp_results": (
        "Results of the case's last calculation as tables of numbers "
        "({available: false, reason} before one).",
        _schema({"case": _CASE}),
        lambda app, a: app.results(a.get("case")),
    ),
    "ccp_figure": (
        "Without `id`: the list of figures. With `id`: one figure as compact "
        "data (default), full plotly JSON, or a PNG image when available.",
        _schema(
            {
                "id": {"type": "string"},
                "format": {"type": "string", "enum": ["data", "plotly", "png"]},
                "case": _CASE,
            }
        ),
        _figure,
    ),
    "ccp_undo": (
        "Undo an agent revision of the case (default: the newest one not "
        "undone; a plain undo is skipped, so repeated calls step back through "
        "the agent's changes). To redo, undo the undo revision by its "
        "`revision_id`.",
        _schema({"case": _CASE, "revision_id": {"type": "integer"}}),
        lambda app, a: app.undo(a.get("revision_id"), case=a.get("case")),
    ),
    "ccp_note": (
        "Post a note (plain text) the user sees on the case's page.",
        _schema({"body": {"type": "string"}, "case": _CASE}, required=("body",)),
        lambda app, a: app.note(a["body"], case=a.get("case")),
    ),
    "ccp_open_case": (
        "Make the user's browser open a case (within a few seconds).",
        _schema({"case": {"type": "integer"}}, required=("case",)),
        lambda app, a: app.open(a["case"]),
    ),
    "ccp_duplicate": (
        "Copy a case (the open one by default); returns the new case.",
        _schema({"case": _CASE, "name": {"type": "string"}}),
        lambda app, a: app.duplicate(a.get("case"), name=a.get("name")),
    ),
}


def tool_list():
    return [
        {"name": name, "description": description, "inputSchema": schema}
        for name, (description, schema, _) in TOOLS.items()
    ]


def _text(data):
    return [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]


class Server:
    """Dispatch JSON-RPC messages to the tools.

    ``connect`` returns a ``CcpApp``; it is called for every tool call.
    """

    def __init__(self, connect):
        self.connect = connect

    def call_tool(self, name, arguments):
        """The ``tools/call`` result for one tool."""
        _, _, call = TOOLS[name]
        try:
            data = call(self.connect(), arguments)
        except CcpAppError as exc:
            return {"content": _text(exc.as_dict()), "isError": True}
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "content": _text({"error": f"invalid arguments: {exc}"}),
                "isError": True,
            }
        except Exception as exc:
            return {
                "content": _text({"error": f"{type(exc).__name__}: {exc}"}),
                "isError": True,
            }
        if isinstance(data, Content):
            return {"content": list(data), "isError": False}
        return {"content": _text(data), "isError": False}

    def handle(self, message):
        """The response to one message (None for a notification)."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _error(None, INVALID_REQUEST, "not a JSON-RPC 2.0 message")
        method = message.get("method")
        msg_id = message.get("id")
        if "id" not in message:
            return None  # notifications/initialized, cancelled, ...
        if not isinstance(method, str):
            # A response from the client (we never send requests): ignore.
            return None
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(msg_id, INVALID_PARAMS, "params must be an object")
        if method == "initialize":
            requested = params.get("protocolVersion")
            version = requested if requested in SUPPORTED_VERSIONS else PROTOCOL_VERSION
            return _result(
                msg_id,
                {
                    "protocolVersion": version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": SERVER_INFO,
                    "instructions": INSTRUCTIONS,
                },
            )
        if method == "ping":
            return _result(msg_id, {})
        if method == "tools/list":
            return _result(msg_id, {"tools": tool_list()})
        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name not in TOOLS:
                return _error(msg_id, INVALID_PARAMS, f"unknown tool {name!r}")
            if not isinstance(arguments, dict):
                return _error(msg_id, INVALID_PARAMS, "arguments must be an object")
            return _result(msg_id, self.call_tool(name, arguments))
        return _error(msg_id, METHOD_NOT_FOUND, f"method not found: {method}")

    def handle_line(self, line):
        """The response line for one input line (None: nothing to send)."""
        line = line.strip()
        if not line:
            return None
        try:
            message = json.loads(line)
        except ValueError as exc:
            return _dump(_error(None, PARSE_ERROR, f"parse error: {exc}"))
        if isinstance(message, list):
            replies = [r for r in map(self._safe_handle, message) if r is not None]
            return _dump(replies) if replies else None
        reply = self._safe_handle(message)
        return _dump(reply) if reply is not None else None

    def _safe_handle(self, message):
        """``handle``, with an unexpected error as a JSON-RPC error reply.

        Used for batch members too: one bad member must not end the server.
        """
        try:
            return self.handle(message)
        except Exception as exc:
            msg_id = message.get("id") if isinstance(message, dict) else None
            return _error(msg_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")

    def run(self, stdin, stdout):
        for line in stdin:
            reply = self.handle_line(line)
            if reply is not None:
                stdout.write(reply + "\n")
                stdout.flush()


def _result(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _dump(message):
    # One line per message: no indentation, and escapes keep it ASCII-safe.
    return json.dumps(message, separators=(",", ":"))


def _utf8(stream, **options):
    """``stream`` reconfigured to UTF-8 when it can be (a real stdio stream).

    MCP clients send UTF-8, but Python decodes a Windows pipe with the ANSI
    code page: 'kgf/cm²' arrives garbled, and a byte cp1252 does not define
    (as in 'ÁGUA') would end the server with a UnicodeDecodeError.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", **options)
        except (ValueError, OSError):
            pass
    return stream


def serve(url=None, token=None, transport=None, stdin=None, stdout=None):
    """Run the server until stdin closes; returns the exit code."""
    if stdin is None:
        stdin = _utf8(sys.stdin, errors="replace")
    if stdout is None:
        stdout = _utf8(sys.stdout, newline="\n")
    server = Server(lambda: CcpApp.connect(url, token, transport=transport))
    try:
        server.run(stdin, stdout)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(serve())
