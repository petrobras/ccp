"""CLI entry point for the ccp app.

``ccp-app`` opens the Django application (``ccp_web``) in a desktop window, or
in the browser when pywebview is not installed. ``ccp-app --streamlit`` runs
the previous Streamlit app, kept until the new app is signed off.
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
    try:
        import django  # noqa: F401
    except ImportError:
        try:
            import streamlit  # noqa: F401
        except ImportError:
            print(
                "The ccp app needs the web extra: pip install ccp-performance[desktop] "
                "(or [web] to use a browser)."
            )
            sys.exit(1)
        run_streamlit()
        return
    from ccp_web.cli import main as web_main

    try:
        import webview  # noqa: F401

        web_main(["desktop"] + args)
    except ImportError:
        web_main(["serve"] + args)


if __name__ == "__main__":
    main()
