"""``ccp-web`` command line.

    ccp-web desktop            native window (pywebview) around a local server
    ccp-web serve [--port N]   local server and task workers, open in a browser
    ccp-web worker [--queue Q] one task worker (hosted deployments run several)
    ccp-web manage <args>      Django management commands (migrate, createsuperuser...)

``CCP_PROFILE`` selects the settings profile (``desktop`` by default).
"""

import argparse
import os
import sys


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
    if argv and argv[0] == "manage":
        manage(argv[1:])
        return
    parser = argparse.ArgumentParser(
        prog="ccp-web", description=__doc__.splitlines()[0]
    )
    sub = parser.add_subparsers(dest="command")
    p_desktop = sub.add_parser("desktop", help="native desktop window")
    p_desktop.add_argument("--debug", action="store_true")
    p_serve = sub.add_parser("serve", help="local server and workers")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=0, help="0 picks a free port")
    p_serve.add_argument("--no-browser", action="store_true")
    p_serve.add_argument("--no-workers", action="store_true")
    p_worker = sub.add_parser("worker", help="one task worker")
    p_worker.add_argument("--queue", default="default")
    p_worker.add_argument("--interval", type=float, default=1.0)
    sub.add_parser("manage", help="Django management commands")
    args = parser.parse_args(argv)

    if args.command == "worker":
        worker(args.queue, args.interval)
    elif args.command == "serve":
        from .launcher import serve

        serve(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            workers=not args.no_workers,
        )
    elif args.command == "desktop" or args.command is None:
        from .launcher import desktop

        desktop(debug=getattr(args, "debug", False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
