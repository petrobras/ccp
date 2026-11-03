# Installation

To use ccp you will need python >= 3.9. The ccp application needs
python >= 3.10.

## Core Library

You can install the core `ccp` library with:

```{code-block}
pip install ccp-performance
```

## Application

ccp includes an application for performance tests (ASME PTC 10,
straight-through and back-to-back), curves conversion, curves digitizing and
performance evaluation of plant data. Install it with one of these extras:

```{code-block}
pip install "ccp-performance[desktop]"   # the app in a native window (pywebview)
pip install "ccp-performance[web]"       # the app in your browser
```

The `web` extra installs the Django application and its local server; the
`desktop` extra adds pywebview for the native window. On python 3.9 these
extras install nothing, and the app will not start.

Start the app with:

```{code-block}
ccp-app
```

`ccp-app` opens the app in a desktop window, or in your default browser when
the window cannot open: pywebview (the `desktop` extra) is not installed,
there is no graphical display or, on Linux, there is no Qt or GTK toolkit for
it (install `pywebview[qt]`, or
PyGObject and GTK, to get the window there). The `ccp-web` command gives more
control:

```{code-block}
ccp-web desktop                # native window (desktop extra; on Linux also Qt/GTK)
ccp-web serve                  # local server, opens the default browser
ccp-web serve --port 8000      # choose the port (by default a free one is picked)
ccp-web serve --no-browser     # only print the URL
```

`ccp-web` with no command does the same as `ccp-app`. Where console scripts
are not on the `PATH` (e.g. a locked environment), use `python -m ccp_web`,
`python -m ccp_web serve` or `python -m ccp_web desktop`.
The app runs on `127.0.0.1` and prints its URL; stop it with `Ctrl+C` or by
closing the window.

At start the app applies its database migrations and starts its background
workers. Your cases, uploaded files and results are kept in your user data
directory; set the `CCP_DATA_DIR` environment variable to keep them somewhere
else.

The curves digitizer page also needs the `digitize` extra and the
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract) binary:

```{code-block}
pip install "ccp-performance[desktop,digitize]"
```

### Streamlit Application

The previous Streamlit application is still available while the new
application is being signed off. Install it with the `app` extra and start it
with `ccp-app --streamlit`:

```{code-block}
pip install "ccp-performance[app]"
ccp-app --streamlit
```

`.ccp` files can be opened in both applications.

### Development Dependencies

For development work, clone the repository and install every extra and the
development tools with [uv](https://docs.astral.sh/uv/):

```{code-block}
uv sync --all-extras
```

See the {doc}`../contributing` guide for details.

## AI assistance

ccp ships with an agent skill — a set of concise compressor-performance
recipes in the [Agent Skills](https://agentskills.io) open standard that
teaches AI coding agents how to build states, points and impellers and run
performance analyses with ccp. After installing ccp, install the skill with:

```{code-block}
ccp-install-skill
```

This detects the AI coding agents on your machine (Claude Code, GitHub
Copilot, Cursor, Codex) and copies the skill to each one's personal skills
directory. Useful variations:

```{code-block}
ccp-install-skill --project          # install into the current project (shared with your team)
ccp-install-skill --agent claude     # install for a specific agent only
ccp-install-skill --uninstall        # remove the skill
```

Once installed, the skill activates automatically whenever you ask your agent
about centrifugal compressor performance with ccp — for example, "create an
impeller from these test points and convert the curves to the new suction
condition". In Claude Code you can also invoke it explicitly with the `/ccp`
slash command.

The skill is a snapshot of the recipes for the installed ccp version, so
re-run `ccp-install-skill` after upgrading ccp.

While the application is running, AI agents can also work with the case you
have open (read and change its inputs, run its calculation) through
`ccp-web agent`; every change they make can be undone from the app. This
needs no extra installation. See `ccp-web agent --help`, or connect an MCP
client with `ccp-web agent mcp`.

## REFPROP

REFPROP is optional. Without it, ccp warns at import and uses CoolProp
(`HEOS` backend) for the gas properties. To use `REFPROP`, install it and set
an environment variable called `RPPREFIX` pointing to the `REFPROP` path (on
Windows, `C:\Users\Public\REFPROP` is also found automatically).

If you have not set a `RPPREFIX` environment variable, you can do the following before importing ccp:

```{code-block} python
import os
os.environ['RPPREFIX'] = <path/to/REFPROP/folder>

import ccp
```

For the application, set `RPPREFIX` before running `ccp-app` or `ccp-web`.
