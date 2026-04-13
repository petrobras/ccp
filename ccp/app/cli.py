"""CLI entry point for launching the CCP Streamlit app."""

import sys
from pathlib import Path


def main():
    try:
        from streamlit.web.cli import main as st_main
    except ImportError:
        print(
            "Streamlit is required to run ccp-app. "
            "Install it with: pip install ccp-performance[app]"
        )
        sys.exit(1)

    app_path = str(Path(__file__).parent / "ccp_app.py")
    sys.argv = ["streamlit", "run", app_path, "--server.headless=true"]
    st_main()


if __name__ == "__main__":
    main()
