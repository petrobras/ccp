"""ccp-web: the ccp web application.

    ccp-web                    desktop window when available, otherwise browser
    ccp-web desktop            native window (pywebview) around a local server
    ccp-web serve [--port N]   local server and task workers, open in a browser
    ccp-web worker [--queue Q] one task worker (hosted deployments run several)
    ccp-web manage <args>      Django management commands (migrate, createsuperuser...)
    ccp-web agent <command>    talk to the running app as an AI agent (JSON out;
                               ``ccp-web agent --help``, ``ccp-web agent mcp``)

``python -m ccp_web`` is the same command. ``desktop`` and ``serve`` open
the agent API for local agents unless
``--no-agent`` is given. ``CCP_PROFILE`` selects the settings profile
(``desktop`` by default). ``agent`` runs before any Django setup: it only
needs the standard library, so it works where the ``web`` extra is missing.
"""

import argparse
import importlib.util
import os
import sys

# Imported by every profile; the rest of the web extra is imported lazily.
WEB_EXTRA_MODULES = (
    "django",
    "django_htmx",
    "template_partials",
    "django_tasks",
    "django_tasks_db",
    "allauth",
    "whitenoise",
    "platformdirs",
)
WEB_EXTRA_MISSING = (
    "The ccp web app needs Python >= 3.10 and the web extra: "
    'pip install "ccp-performance[web]" ("[desktop]" for the native window).'
)


def web_extra_installed():
    return all(importlib.util.find_spec(name) for name in WEB_EXTRA_MODULES)


def require_web_extra():
    """Exit with an install hint when the ``web`` extra is missing."""
    if not web_extra_installed():
        hint = WEB_EXTRA_MISSING
        if sys.version_info < (3, 10):
            hint += f" This is Python {sys.version.split()[0]}."
        sys.exit(hint)


def _setup():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    import django

    django.setup()


def manage(argv):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(["ccp-web"] + list(argv))


def worker(queue="default", interval=1.0):
    _setup()
    from django.core.management import call_command

    call_command(
        "db_worker",
        queue_name=queue,
        interval=interval,
        startup_delay=False,
    )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "probe-gui":
        # Internal: the child process of ``launcher.desktop_unavailable``.
        from .launcher import probe_gui

        reason = probe_gui()
        if reason:
            print(reason, flush=True)
        sys.exit(1 if reason else 0)
    if argv and argv[0] == "agent":
        from .agent.cli import main as agent_main

        sys.exit(agent_main(argv[1:]))
    if argv and argv[0] == "manage":
        require_web_extra()
        manage(argv[1:])
        return
    parser = argparse.ArgumentParser(
        prog="ccp-web", description=__doc__.splitlines()[0]
    )
    sub = parser.add_subparsers(dest="command")
    p_desktop = sub.add_parser("desktop", help="native desktop window")
    p_desktop.add_argument("--debug", action="store_true")
    p_desktop.add_argument(
        "--no-agent", action="store_true", help="do not open the agent API"
    )
    p_serve = sub.add_parser("serve", help="local server and workers")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=0, help="0 picks a free port")
    p_serve.add_argument("--no-browser", action="store_true")
    p_serve.add_argument("--no-workers", action="store_true")
    p_serve.add_argument(
        "--no-agent", action="store_true", help="do not open the agent API"
    )
    p_worker = sub.add_parser("worker", help="one task worker")
    p_worker.add_argument("--queue", default="default")
    p_worker.add_argument("--interval", type=float, default=1.0)
    sub.add_parser("manage", help="Django management commands")
    sub.add_parser("agent", help="talk to the running app as an AI agent")
    args = parser.parse_args(argv)
    if args.command in (None, "desktop", "serve", "worker"):
        require_web_extra()

    if args.command == "worker":
        worker(args.queue, args.interval)
    elif args.command == "serve":
        from .launcher import serve

        serve(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            workers=not args.no_workers,
            agent=not args.no_agent,
        )
    elif args.command == "desktop":
        from .launcher import desktop

        desktop(debug=args.debug, agent=not args.no_agent)
    elif args.command is None:
        from .launcher import app

        app()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
