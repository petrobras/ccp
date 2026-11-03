"""CLI entry point for the ccp app.

``ccp-app`` opens the Django application (``ccp_web``) in a desktop window, or
in the browser when pywebview or a GUI toolkit for it is not available.
``ccp-app --streamlit`` runs the previous Streamlit app, kept until the new app
is signed off.
"""

import sys
from pathlib import Path


def run_streamlit():
    try:
        from streamlit.web.cli import main as st_main
    except ImportError:
        print(
            "Streamlit is required to run the Streamlit app. "
            "Install it with: pip install ccp-performance[app]"
        )
        sys.exit(1)

    app_path = str(Path(__file__).parent / "ccp_app.py")
    sys.argv = ["streamlit", "run", app_path]
    st_main()


def main():
    args = sys.argv[1:]
    if "--streamlit" in args:
        run_streamlit()
        return
    # ccp_web.cli only needs the standard library to import.
    from ccp_web import cli as web_cli

    if not web_cli.web_extra_installed():
        try:
            import streamlit  # noqa: F401
        except ImportError:
            web_cli.require_web_extra()
        run_streamlit()
        return
    if not args:
        web_cli.main([])
        return
    from ccp_web.launcher import desktop_unavailable

    command = "desktop" if desktop_unavailable() is None else "serve"
    web_cli.main([command] + args)


if __name__ == "__main__":
    main()
