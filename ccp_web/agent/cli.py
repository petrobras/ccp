"""``ccp-web agent <command>``: the agent API from a shell (stdlib only).

For agents without MCP (or without Python glue): every command prints JSON on
stdout; an error prints ``{"error": ..., "status": ..., "details": ...}`` on
stderr and exits 1 (2 for a usage error). ``--case`` defaults to the case the
user has open in the app.

    ccp-web agent status
    ccp-web agent get --keys suction_pressure_point_1,suction_pressure_units
    ccp-web agent set suction_pressure_point_1=4.5 --note "try 4.5 bar"
    ccp-web agent calc --wait 90
    ccp-web agent results
    ccp-web agent undo
    ccp-web agent note "Head is 2 % above the guarantee."
    ccp-web agent mcp   # MCP stdio server: claude mcp add ccp -- ccp-web agent mcp

``ccp_web/cli.py`` dispatches here before any Django setup, so this module
must not import Django.
"""

import argparse
import json
import math
import sys
from pathlib import Path

from .client import CcpApp, CcpAppError


class UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    """Usage errors raise instead of printing text and exiting."""

    def error(self, message):
        raise UsageError(f"{self.prog}: {message}")


def _reject_constant(name):
    raise ValueError(name)


def parse_value(text):
    """A command-line value: a JSON literal (true/false/number/object/array or a
    quoted string), else the text itself.

    ``4.5`` → 4.5, ``true`` → True, ``bar`` → "bar", ``'"001"'`` → "001".
    ``null``, ``NaN`` and ``Infinity`` stay strings.
    """
    try:
        value = json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        return text
    if value is None:
        return text
    if isinstance(value, float) and not math.isfinite(value):
        return text
    return value


def parse_assignments(items):
    """``["k=v", ...]`` → ``{k: parse_value(v)}``."""
    values = {}
    for item in items:
        key, sep, raw = item.partition("=")
        key = key.strip()
        if not sep or not key:
            raise UsageError(f"expected key=value, got {item!r}")
        values[key] = parse_value(raw)
    return values


def _json_object(text, what):
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise UsageError(f"{what} is not valid JSON: {exc}") from None
    if not isinstance(value, dict):
        raise UsageError(f"{what} must be a JSON object")
    return value


def build_parser():
    parser = _Parser(
        prog="ccp-web agent",
        description="Talk to the running ccp app (agent API). Output is JSON.",
    )
    parser.add_argument("--url", help="app URL (default: CCP_AGENT_URL or agent file)")
    parser.add_argument(
        "--token", help="token (default: CCP_AGENT_TOKEN or agent file)"
    )
    sub = parser.add_subparsers(dest="command", parser_class=_Parser, metavar="command")

    def add(name, help, case=False):
        p = sub.add_parser(name, help=help, description=help)
        if case:
            p.add_argument(
                "--case", type=int, help="case id (default: the case open in the app)"
            )
        return p

    add("status", "API info and what the user has open")
    add("context", "what the user has open and the recent cases")
    p = add("cases", "list cases")
    p.add_argument("--project", type=int)
    p.add_argument("--app-type")
    add("projects", "list projects")
    p = add("get", "a case: summary, state, files, jobs", case=True)
    p.add_argument("--keys", help="comma-separated state keys")
    p = add("schema", "state keys of an app type")
    p.add_argument("app_type")
    p.add_argument("--filter", help="only keys or labels containing this text")
    p = add("set", "write values (one undoable revision)", case=True)
    p.add_argument("values", nargs="*", metavar="key=value")
    p.add_argument("--note", default="", help="why (shown to the user)")
    p.add_argument("--json", help="values as a JSON object (key=value args win)")
    p = add("calc", "start the calculation", case=True)
    # Below the 120 s an agent's shell tool usually allows a command: a CLI
    # killed by it prints nothing, not even the job id to continue with.
    p.add_argument("--wait", type=float, default=90, help="seconds to wait (90)")
    p.add_argument(
        "--param", action="append", default=[], metavar="key=value", help="repeatable"
    )
    p = add("job", "a job (optionally wait for it)")
    p.add_argument("id", type=int)
    p.add_argument("--wait", type=float, default=0)
    p = add("cancel", "cancel a job")
    p.add_argument("id", type=int)
    add("results", "results of the last calculation", case=True)
    add("figures", "list figures", case=True)
    p = add("figure", "one figure", case=True)
    p.add_argument("id")
    p.add_argument("--format", choices=("data", "plotly", "png"), default="data")
    p.add_argument("--out", help="write to this file (required for png)")
    p = add("undo", "undo an agent revision (default: the latest)", case=True)
    p.add_argument("--revision", type=int, help="revision id")
    add("revisions", "agent revisions of a case", case=True)
    p = add("note", "post a note the user sees", case=True)
    p.add_argument("text", nargs="?")
    p.add_argument("--file", help="read the note from a file ('-' for stdin)")
    add("notes", "notes of a case", case=True)
    p = add("duplicate", "copy a case", case=True)
    p.add_argument("--name")
    p = add("open", "make the user's browser open a case")
    p.add_argument("case", type=int)
    p = add("export", "download a case as .ccp", case=True)
    p.add_argument("--out", required=True, help="file.ccp")
    p = add("create", "create a case (empty or from a .ccp file)")
    p.add_argument("app_type")
    p.add_argument("--name")
    p.add_argument("--project", type=int)
    p.add_argument("--from", dest="source", metavar="FILE.ccp")
    add("mcp", "run the MCP stdio server")
    return parser


def _run(app, args):
    """The command's result (JSON-able), or None when it printed nothing."""
    cmd = args.command
    case = getattr(args, "case", None)
    if cmd == "status":
        return {
            "url": app.url,
            "source": app.source,
            "api": app.root(),
            "context": app.context(),
        }
    if cmd == "context":
        return app.context()
    if cmd == "cases":
        return app.cases(project=args.project, app_type=args.app_type)
    if cmd == "projects":
        return app.projects()
    if cmd == "get":
        return app.case(case, keys=args.keys)
    if cmd == "schema":
        return app.schema(args.app_type, filter=args.filter)
    if cmd == "set":
        values = _json_object(args.json, "--json") if args.json else {}
        values.update(parse_assignments(args.values))
        if not values:
            raise UsageError("nothing to set: pass key=value or --json")
        return app.set(values, note=args.note, case=case)
    if cmd == "calc":
        params = parse_assignments(args.param)
        return app.calculate(case, wait=args.wait, **params)
    if cmd == "job":
        return app.job(args.id, wait=args.wait)
    if cmd == "cancel":
        return app.cancel(args.id)
    if cmd == "results":
        return app.results(case)
    if cmd == "figures":
        return app.figures(case)
    if cmd == "figure":
        if args.format == "png" and not args.out:
            raise UsageError("--format png needs --out file.png")
        data = app.figure(args.id, format=args.format, case=case)
        if not args.out:
            return data
        out = Path(args.out)
        if args.format == "png":
            out.write_bytes(data)
        else:
            out.write_text(_dumps(data), encoding="utf-8")
        return {"ok": True, "path": str(out.resolve())}
    if cmd == "undo":
        return app.undo(args.revision, case=case)
    if cmd == "revisions":
        return app.revisions(case)
    if cmd == "note":
        if args.file:
            if args.file == "-":
                # Bytes: the locale code page (cp1252 on Windows) would
                # garble the UTF-8 an agent pipes in.
                text = sys.stdin.buffer.read().decode("utf-8", "replace")
            else:
                text = Path(args.file).read_text(encoding="utf-8")
        else:
            text = args.text
        if not text or not text.strip():
            raise UsageError("pass the note text, or --file")
        return app.note(text, case=case)
    if cmd == "notes":
        return app.notes(case)
    if cmd == "duplicate":
        return app.duplicate(case, name=args.name)
    if cmd == "open":
        return app.open(args.case)
    if cmd == "export":
        content = app.export(case, args.out)
        return {
            "ok": True,
            "path": str(Path(args.out).resolve()),
            "bytes": len(content),
        }
    if cmd == "create":
        if args.source:
            return app.create_case(
                args.app_type, name=args.name, project=args.project, file=args.source
            )
        return app.create_case(args.app_type, name=args.name, project=args.project)
    raise UsageError(f"unknown command {cmd!r}")


def _dumps(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def _print(data, stream):
    text = _dumps(data)
    try:
        stream.write(text + "\n")
    except UnicodeEncodeError:
        # A console that cannot encode subscripts (Windows cp1252).
        stream.write(json.dumps(data, indent=2) + "\n")
    stream.flush()


def _utf8_streams():
    """Write UTF-8 to stdout/stderr whatever the locale.

    On Windows a pipe gets the ANSI code page (cp1252), which can encode
    ``kgf/cm²``: the agent reading the output as UTF-8 would see a
    replacement character and send it back in ``set``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        encoding = (getattr(stream, "encoding", None) or "").lower()
        if reconfigure is not None and encoding.replace("-", "") != "utf8":
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv=None, transport=None):
    """Run one command; returns the exit code (0, 1 error, 2 usage).

    ``transport`` is the client's test hook (see ``client.py``).
    """
    argv = sys.argv[1:] if argv is None else list(argv)
    _utf8_streams()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command is None:
            parser.print_help(sys.stderr)
            return 2
        if args.command == "mcp":
            from .mcp import serve

            return serve(url=args.url, token=args.token, transport=transport)
        app = CcpApp.connect(args.url, args.token, transport=transport)
        result = _run(app, args)
    except UsageError as exc:
        _print({"error": str(exc), "usage": parser.format_usage().strip()}, sys.stderr)
        return 2
    except CcpAppError as exc:
        _print(exc.as_dict(), sys.stderr)
        return 1
    except OSError as exc:
        _print({"error": f"{type(exc).__name__}: {exc}", "status": None}, sys.stderr)
        return 1
    except SystemExit as exc:
        # --help.
        return exc.code if isinstance(exc.code, int) else 0
    if result is not None:
        _print(result, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
