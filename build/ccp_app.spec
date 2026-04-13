# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CCP Streamlit application.
Build with:
    pyinstaller --distpath=pyinstaller_build --workpath=pyinstaller_work ccp_app.spec
"""

import json
import os
import re
import sys
import importlib
import importlib.metadata

# Sync version from ccp/__init__.py to electron/package.json
_init_file = os.path.join(os.path.dirname(SPECPATH), "ccp", "__init__.py")
with open(_init_file) as _f:
    _match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', _f.read())
    _ccp_version = _match.group(1) if _match else "0.0.0"

_pkg_json_path = os.path.join(SPECPATH, "electron", "package.json")
with open(_pkg_json_path) as _f:
    _pkg = json.load(_f)
if _pkg.get("version") != _ccp_version:
    _pkg["version"] = _ccp_version
    with open(_pkg_json_path, "w") as _f:
        json.dump(_pkg, _f, indent=2)
        _f.write("\n")
    print(f"Updated electron/package.json version to {_ccp_version}")

block_cipher = None

# Get paths to key packages
def get_package_path(package_name):
    mod = importlib.import_module(package_name)
    return os.path.dirname(mod.__file__)

def get_dist_info(package_name):
    """Get the dist-info directory path for a package (needed for importlib.metadata)."""
    dist = importlib.metadata.distribution(package_name)
    dist_path = str(dist._path)
    parent = os.path.dirname(dist_path)
    basename = os.path.basename(dist_path)
    return (dist_path, basename)

streamlit_path = get_package_path("streamlit")
altair_path = get_package_path("altair")
plotly_path = get_package_path("plotly")
coolprop_path = get_package_path("CoolProp")
pint_path = get_package_path("pint")
pandaspi_path = get_package_path("pandaspi")

# Collect dist-info directories for packages that use importlib.metadata
metadata_packages = [
    'streamlit', 'altair', 'plotly', 'CoolProp', 'pint', 'numpy', 'scipy',
    'pandas', 'sentry-sdk', 'markdown', 'toml', 'ccp-performance',
    'tornado', 'pyarrow', 'packaging', 'openpyxl', 'xlsxwriter',
    'scikit-learn', 'tqdm', 'Pillow', 'click', 'rich', 'watchdog', 'pandaspi',
    'pythonnet', 'clr_loader',
    'protobuf', 'cachetools', 'gitpython', 'pydeck', 'typing_extensions',
    'tenacity', 'jinja2', 'certifi', 'charset-normalizer', 'requests',
    'urllib3', 'idna', 'blinker',
]
dist_info_datas = []
for pkg in metadata_packages:
    try:
        src, dest = get_dist_info(pkg)
        dist_info_datas.append((src, dest))
    except Exception:
        pass  # Package not installed, skip

# Project root (one level up from build/)
project_root = os.path.dirname(SPECPATH)

a = Analysis(
    [os.path.join(project_root, 'ccp', 'app', 'run_streamlit.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # CCP package
        (os.path.join(project_root, 'ccp'), 'ccp'),
        # Streamlit static files and runtime
        (streamlit_path, 'streamlit'),
        # Altair schemas
        (altair_path, 'altair'),
        # Plotly templates
        (plotly_path, 'plotly'),
        # CoolProp data
        (coolprop_path, 'CoolProp'),
        # Pint unit definitions
        (pint_path, 'pint')
    ] + dist_info_datas,
    hiddenimports=[
        # Streamlit and web
        'streamlit',
        'streamlit.web.cli',
        'streamlit.web.server',
        'streamlit.web.server.server',
        'streamlit.runtime',
        'streamlit.runtime.scriptrunner',
        # Scientific packages
        'numpy',
        'scipy',
        'scipy.stats',
        'scipy.optimize',
        'scipy.interpolate',
        'pandas',
        'pandas.io.formats.style',
        # CoolProp
        'CoolProp',
        'CoolProp.CoolProp',
        'CoolProp.HumidAirProp',
        # Plotting
        'plotly',
        'plotly.graph_objects',
        'plotly.express',
        'plotly.io',
        # CCP
        'ccp',
        'ccp.state',
        'ccp.point',
        'ccp.curve',
        'ccp.impeller',
        'ccp.compressor',
        'ccp.fo',
        'ccp.evaluation',
        'ccp.similarity',
        'ccp.config',
        'ccp.config.fluids',
        'ccp.config.units',
        'ccp.config.utilities',
        'ccp.app',
        'ccp.app.common',
        'ccp.app.report',
        'ccp.app.ai_analysis',
        'ccp.plotly_theme',
        # Other deps
        'pint',
        'toml',
        'openpyxl',
        'xlsxwriter',
        'pyarrow',
        'sklearn',
        'sklearn.linear_model',
        'tqdm',
        'packaging',
        'packaging.version',
        'sentry_sdk',
        'markdown',
        'google.generativeai',
        'ctREFPROP',
        'altair',
        # pandaspi (Petrobras)
        'pandaspi',
        'pandaspi.webapi',
        'pandaspi.webapi.session',
        'pandaspi.webapi.read_attributes',
        'pandaspi.webapi.osisoft',
        'pandaspi.webapi.osisoft.pidevclub',
        'pandaspi.webapi.osisoft.pidevclub.piwebapi',
        'pandaspi.session',
        # pythonnet (needed by pandaspi to pass import clr check)
        'clr',
        'clr_loader',
        'pythonnet',
        # Tornado (for streamlit server)
        'tornado',
        'tornado.web',
        'tornado.websocket',
        'tornado.ioloop',
        # Other
        'PIL',
        'json',
        'email.mime.text',
        'email.mime.multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ccp_streamlit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console needed for Electron to read stdout
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, 'electron', 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ccp_streamlit',
)
