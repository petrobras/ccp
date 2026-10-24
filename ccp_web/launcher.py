"""Desktop launcher: local server, task workers and the native window.

``desktop()`` opens a pywebview window; ``serve()`` does the same work but
opens the default browser (or nothing), which is also how the app runs on a
machine without a GUI toolkit for pywebview.

Both also open the agent API to local AI agents (desktop profile, unless
``--no-agent``): a fresh desktop token is issued at every start and written
with the server URL to the agent file (``agent/discovery.py``), which is
removed again at exit.
"""

import atexit
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser

log = logging.getLogger("ccp_web.launcher")

WORKER_QUEUES = ("default", "monitoring")


def free_port(host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def prepare():
    """Set up Django, apply migrations and recover interrupted jobs."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    import django

    django.setup()
    from django.core.management import call_command
    from django.utils import timezone

    call_command("migrate", interactive=False, verbosity=0)
    from ccp_web.core.models import Job

    Job.objects.filter(status__in=Job.ACTIVE).update(
        status=Job.FAILED,
        error="Interrupted: the application was closed while the job ran.",
        finished=timezone.now(),
    )


def start_workers(queues=WORKER_QUEUES):
    """One ``db_worker`` process per queue; stopped at exit."""
    procs = []
    env = dict(os.environ)
    env.setdefault("DJANGO_SETTINGS_MODULE", "ccp_web.settings")
    for queue in queues:
        if getattr(sys, "frozen", False):
            # PyInstaller bundle: the executable is the ccp_web CLI itself.
            cmd = [sys.executable, "worker", "--queue", queue]
        else:
            cmd = [sys.executable, "-m", "ccp_web.cli", "worker", "--queue", queue]
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        procs.append(subprocess.Popen(cmd, env=env, **kwargs))

    def stop():
        for p in procs:
            if p.poll() is None:
                p.terminate()
        deadline = time.monotonic() + 5
        for p in procs:
            try:
                p.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                p.kill()

    atexit.register(stop)
    return procs, stop


def _wsgi_server(host, port):
    from ccp_web.wsgi import application

    try:
        from waitress import create_server

        # Agent long-polls (up to 60 s each) share these threads with the
        # page's own requests: leave room for several at once.
        return create_server(application, host=host, port=port, threads=16)
    except ImportError:
        from socketserver import ThreadingMixIn
        from wsgiref.simple_server import WSGIServer, make_server

        class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
            daemon_threads = True

        return make_server(host, port, application, server_class=ThreadingWSGIServer)


def start_server(host="127.0.0.1", port=0):
    port = port or free_port(host)
    server = _wsgi_server(host, port)
    run = getattr(server, "run", None) or server.serve_forever
    thread = threading.Thread(target=run, name="ccp-web-server", daemon=True)
    thread.start()
    url = f"http://{host}:{port}/"
    _wait_until_up(host, port)
    return server, url


def _wait_until_up(host, port, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"ccp web server did not start on {host}:{port}")


def start_agent_session(url, pid=None, register_exit=True):
    """Issue the desktop agent token and write the agent file.

    Only in the desktop profile: the hosted service has no local agent file
    (its users create personal tokens in the browser). The local user's
    previous desktop tokens are deleted first, so a token from an earlier
    run stops working. Returns the agent file path, or None when skipped.
    """
    from django.conf import settings

    if getattr(settings, "CCP_PROFILE", None) != "desktop":
        return None
    from ccp_web.agent import discovery
    from ccp_web.agent.models import AgentToken
    from ccp_web.core.middleware import get_local_user

    user = get_local_user()
    AgentToken.objects.for_user(user).filter(kind=AgentToken.DESKTOP).delete()
    row, plaintext = AgentToken.issue(
        user, "desktop session", scope=AgentToken.WRITE, kind=AgentToken.DESKTOP
    )
    pid = os.getpid() if pid is None else pid
    # A server bound to every interface is reached locally on loopback.
    url = url.replace("//0.0.0.0:", "//127.0.0.1:")
    path = discovery.write(url, plaintext, pid=pid)

    def stop():
        discovery.remove_if_owned(pid, path=path)
        try:
            AgentToken.objects.filter(pk=row.pk).delete()
        except Exception:
            # The database may already be gone at interpreter exit; the next
            # start deletes the token anyway.
            log.debug("could not delete the desktop agent token", exc_info=True)

    if register_exit:
        atexit.register(stop)
    print(f"agent API: {discovery.api_url(url)} (token in {path})", flush=True)
    return path


def serve(host="127.0.0.1", port=0, open_browser=True, workers=True, agent=True):
    prepare()
    stop_workers = None
    if workers:
        _, stop_workers = start_workers()
    server, url = start_server(host, port)
    print(f"ccp is running at {url}  (Ctrl+C to stop)", flush=True)
    if agent:
        start_agent_session(url)
    if open_browser:
        webbrowser.open(url)
    try:
        signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
        while True:
            time.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if stop_workers:
            stop_workers()


def desktop(debug=False, agent=True):
    try:
        import webview
    except ImportError:
        print(
            "pywebview is not installed; install ccp-performance[desktop] or run "
            "'ccp-web serve' to use a browser.",
            file=sys.stderr,
        )
        sys.exit(1)
    prepare()
    _, stop_workers = start_workers()
    _, url = start_server()
    if agent:
        start_agent_session(url)
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window("ccp", url, width=1440, height=900, min_size=(900, 640))
    try:
        webview.start(debug=debug, private_mode=False)
    finally:
        stop_workers()
