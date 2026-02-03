"""
Streamlit launcher for standalone executable builds.

This script:
1. Sets CCP_STANDALONE environment variable to disable Sentry
2. Monkey-patches Streamlit to output {"port": XXXX} JSON for Electron detection
3. Runs Streamlit in headless mode with file watcher disabled

Compatible with PyInstaller bundling.
"""

import os
import sys
import json

# Set standalone mode to disable Sentry
os.environ["CCP_STANDALONE"] = "1"


def get_app_path():
    """
    Get the path to ccp_app.py, handling both normal execution and PyInstaller bundle.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        # PyInstaller extracts to _MEIPASS temp directory
        base_path = sys._MEIPASS
    else:
        # Running as normal Python script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, "ccp", "app", "ccp_app.py")


def patch_streamlit_server():
    """
    Monkey-patch Streamlit's server to print port as JSON when server starts.
    This allows Electron to detect when the server is ready and on which port.
    """
    from streamlit.web.server import server
    from streamlit import config

    original_start = server.Server.start

    async def patched_start(self, *args, **kwargs):
        result = await original_start(self, *args, **kwargs)
        # Get port from streamlit config
        port = config.get_option("server.port")
        # Output port as JSON for Electron to parse
        port_info = {"port": port}
        print(json.dumps(port_info), flush=True)
        return result

    server.Server.start = patched_start


def main():
    # Apply the monkey-patch before importing streamlit CLI
    patch_streamlit_server()

    # Import streamlit CLI after patching
    from streamlit.web import cli as stcli

    # Get the app path (handles PyInstaller bundle)
    app_path = get_app_path()

    # Build arguments for streamlit
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
        "--client.toolbarMode=minimal",
    ]

    # Run streamlit
    stcli.main()


if __name__ == "__main__":
    main()
