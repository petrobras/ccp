# Version 0.5.0

Version 0.5.0 ships the new ccp application, a Django web app that replaces
the Streamlit app and runs as a desktop window or in the browser. It also
adds automatic digitizing of performance-curve PDFs, an agent API so AI
agents can work with the case open in the app, a faster thermodynamic core
and a more robust point solver.

## Highlights

- The new ccp application (`ccp_web`) is included in the package. Install it
  (python >= 3.10) with `pip install "ccp-performance[desktop]"` (or `[web]`
  for the browser only) and start it with `ccp-app`.
- `ccp-app` now opens the new application. The Streamlit app is still
  available with `ccp-app --streamlit`.
- New `ccp.digitize` reads vendor performance-curve PDFs, with a curves
  digitizer page in the app.
- AI agents can read and change the case open in the app, run its
  calculation and post notes, through `ccp-web agent` or an MCP server.
- Point creation converges for every polytropic method and fluid of the
  Evans and Huble case set, and the calculation pipelines are faster.

## Running the application

```{code-block}
pip install "ccp-performance[desktop]"   # native window (pywebview)
pip install "ccp-performance[web]"       # browser only
ccp-app                                  # desktop window, or the browser if it cannot open
ccp-web serve --port 8000                # always the browser, on a chosen port
python -m ccp_web                        # same as ccp-app, where console scripts are not on the PATH
```

The `web`, `desktop` and `hosted` extras need python >= 3.10; on python 3.9
they install nothing, and `ccp-web` says so. `ccp-app`, `ccp-web` and
`python -m ccp_web` open the desktop window when pywebview, a GUI toolkit for
it and a display are available (on Linux the `desktop` extra installs no
toolkit: install `pywebview[qt]`, or `pywebview[gtk]` with the WebKit2GTK
system libraries) and fall back to the browser otherwise; `ccp-web desktop`
reports the missing piece instead. The app applies its migrations at start
and keeps cases, files and results in the user data directory
(`CCP_DATA_DIR` overrides it). REFPROP is optional: without `RPPREFIX` ccp
uses CoolProp. The curves digitizer page also needs the `digitize` extra and
the Tesseract OCR binary.

## New features

- **ccp web application**
  ([#170](https://github.com/petrobras/ccp/pull/170)) — the `ccp_web`
  Django app ports the four Streamlit pages: straight-through and
  back-to-back performance tests (ASME PTC 10), curves conversion, and
  performance evaluation of plant data with online monitoring and the HTML
  report. Calculations run as background jobs with progress and cancel.
  `.ccp` files import and export losslessly in both apps. The app runs as a
  single-user desktop application (SQLite in the user data directory,
  secrets in the OS keyring) or, with `CCP_PROFILE=hosted` and the `hosted`
  extra, as a multi-user service (`deploy/hosted/`). New console script
  `ccp-web` (`desktop`, `serve`, `worker`, `manage`, `agent`) and new extras
  `web`, `desktop` and `hosted`.

- **Curves digitizing**
  ([#171](https://github.com/petrobras/ccp/pull/171)) — `ccp.digitize`
  (`digitize_pdf`) reads a vendor performance-curve document and returns
  every operating case with its speed lines, legend speeds and suction
  conditions, from the PDF vector content or from the rendered image for
  scans. The app gets a curves digitizer page with a plot editor to review
  the traced points. Needs the new `digitize` extra and Tesseract OCR.

- **Agent API**
  ([#174](https://github.com/petrobras/ccp/pull/174)) — AI agents can see
  what the user has open in the app, read inputs and results, change the
  open case, run its calculation and post notes the user sees. Every agent
  write is undoable from the app. The desktop launcher issues a fresh token
  at each start (`--no-agent` turns it off); the `ccp-web agent` CLI and the
  MCP server (`ccp-web agent mcp`) need only the base package. The agent
  skill gains a `live_app` recipe.

- **Faster thermodynamic core**
  ([#168](https://github.com/petrobras/ccp/pull/168)) — states built
  without a phase get it imposed after the first flash
  (`ccp.config.DEFAULT_PHASE`), which removes the phase-stability analysis
  from the point solver flashes, and `Impeller` interpolates and shares
  points instead of deep-copying them.

## Bug fixes

- **Point solver robustness**
  ([#169](https://github.com/petrobras/ccp/pull/169)) — every discharge
  closure is bracketed by the suction and the isentropic discharge and
  solved with `ccp.roots.solve_monotone`, so Point creation converges for
  every polytropic method and fluid of the Evans and Huble 2017 case set.

- **`sandberg_colby_multistep` points**
  ([#164](https://github.com/petrobras/ccp/pull/164)) — `Point` with
  `polytropic_method="sandberg_colby_multistep"` no longer raises
  `TypeError`.

- **Point solver errors**
  ([#166](https://github.com/petrobras/ccp/pull/166)) — a point that cannot
  be calculated raises `ValueError` naming the solver error instead of an
  `AttributeError` later on.

- **`State.T_critical` units**
  ([#167](https://github.com/petrobras/ccp/pull/167)) — the `units`
  argument is honored; docs now state that the default polytropic method is
  `sandberg_colby`.

- **Lossless compressor test points**
  ([#170](https://github.com/petrobras/ccp/pull/170)) — `StraightThrough`
  and `BackToBack` save points defined by a measured discharge with
  `disch_p` and `disch_T`, so a reloaded compressor converts its points
  exactly; older files still load.

## API changes

- `ccp-app` opens the new application instead of the Streamlit app; the
  Streamlit app is started with `ccp-app --streamlit` (`app` extra)
  ([#170](https://github.com/petrobras/ccp/pull/170)).
- Without the `web` extra (or on python 3.9), `ccp-web` prints how to install
  it instead of failing with `ModuleNotFoundError`; `ccp-app` runs the
  Streamlit app when only the `app` extra is installed and otherwise prints
  the same hint.
- States built without a phase get `ccp.config.DEFAULT_PHASE = "gas"` imposed
  when the density check confirms it; set `ccp.config.DEFAULT_PHASE = None`
  to restore the previous behaviour, or pass `phase=False` to a single state
  ([#168](https://github.com/petrobras/ccp/pull/168)).
- `Impeller` shares the points it is given instead of deep-copying them
  ([#168](https://github.com/petrobras/ccp/pull/168)).
- `Point` raises a `ValueError` for a suction with vapour quality between 0
  and 1 before solving; `Evaluation` instead emits a `PhaseWarning` for a wet
  cluster-centre suction and converts with the unconstrained state
  ([#169](https://github.com/petrobras/ccp/pull/169),
  [#170](https://github.com/petrobras/ccp/pull/170)).
- `head_pol_sandberg_colby_multistep` and `eff_pol_sandberg_colby_multistep`
  take `disch_s` as their third argument; `nstep` moved to the fourth
  position ([#164](https://github.com/petrobras/ccp/pull/164)).
- `check_similarity` reports the PTC 10-2022 Reynolds envelope shared with
  `Point.reynolds_limits`, and the unused `phi3` was removed
  ([#169](https://github.com/petrobras/ccp/pull/169)).

## Infrastructure and packaging

- **The wheel ships `ccp_web`**
  ([#175](https://github.com/petrobras/ccp/issues/175)) — the published
  wheel and sdist contain the `ccp_web` package with its templates, static
  files and migrations. The release workflow builds the wheel from the sdist
  and checks both before upload: every file git tracks under `ccp/` and
  `ccp_web/` must be in them, and no compiled bytecode may be. A CI job
  installs the wheel with the `web` extra in a clean environment (python
  3.10 and 3.13), applies the migrations and serves a page.
- `packaging` is now a declared dependency (it was only installed through
  plotly), and the `web` extra requires `django-allauth>=65.5`, the first
  version that honours the hosted profile's e-mail login settings. The
  license is declared as an SPDX expression (setuptools >= 77 to build), and
  the Python classifiers list 3.9 to 3.13.
- CI runs the web app tests in both the desktop and the hosted profile
  ([#170](https://github.com/petrobras/ccp/pull/170)).
- A PyInstaller spec for the desktop app (`build/ccp_web.spec`) and a Docker
  setup for hosted deployments (`deploy/hosted/`) were added to the
  repository ([#170](https://github.com/petrobras/ccp/pull/170)).
