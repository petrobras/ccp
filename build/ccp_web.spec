# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the ccp desktop app (Django + pywebview).

Build from the repository root with the desktop extra installed:
    uv sync --extra desktop
    uv run pyinstaller --noconfirm --distpath=build/dist --workpath=build/pyinstaller_work build/ccp_web.spec

The result is a one-folder app, build/dist/ccp/ccp(.exe). Starting it with no
arguments opens the window; "ccp worker --queue <q>" is how the app starts its
task workers, and "ccp serve" runs it in the browser instead.

REFPROP is not bundled (NIST licence): ccp finds it through RPPREFIX, or in
C:\\Users\\Public\\REFPROP on Windows; without it ccp falls back to CoolProp.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

project_root = os.path.dirname(SPECPATH)

datas = []
binaries = []
hiddenimports = []

for package in [
    "ccp",
    "ccp_web",
    "django",
    "django_htmx",
    "template_partials",
    "django_tasks",
    "django_tasks_db",
    "whitenoise",
    "waitress",
    "plotly",
    "CoolProp",
    "pint",
    "sklearn",
    "webview",
]:
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

for dist in [
    "ccp-performance",
    "django",
    "django-tasks",
    "django-tasks-db",
    "plotly",
    "pint",
    "scikit-learn",
    "numpy",
    "scipy",
    "pandas",
    "pyarrow",
    "toml",
    "markdown",
    "platformdirs",
    "keyring",
]:
    try:
        datas += copy_metadata(dist)
    except Exception:
        pass

hiddenimports += collect_submodules("keyring.backends")
hiddenimports += ["ccp_web.settings.desktop", "ccp_web.settings.base"]

a = Analysis(
    [os.path.join(project_root, "ccp_web", "__main__.py")],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["streamlit", "tkinter", "IPython", "notebook", "sphinx", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ccp",
    console=False,
    icon=os.path.join(SPECPATH, "electron", "icon.ico") if sys.platform == "win32" else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="ccp")
