# ccp web application

Django port of the Streamlit app in `ccp/app/`: straight-through and back-to-back
performance tests (ASME PTC 10), curves conversion, and performance evaluation of
plant data with online monitoring and an HTML report. It runs as a single-user
desktop application or, by switching a profile, as a multi-user hosted service.
`.ccp` files move freely between this app and the Streamlit app.

## Running

```bash
uv sync --extra desktop          # web stack + pywebview
uv run ccp-app                   # desktop window (browser if pywebview is missing)
uv run ccp-web serve             # local server + task workers, opens the browser
uv run ccp-app --streamlit       # the previous Streamlit app
```

The desktop profile keeps its SQLite database, uploaded files and results in the
user data directory (`platformdirs.user_data_dir("ccp")`, override with
`CCP_DATA_DIR`). The launcher applies migrations, starts two task workers (queues
`default` and `monitoring`) and serves the app on `127.0.0.1` with waitress.

## Profiles

`CCP_PROFILE` selects the settings module in `ccp_web/settings/`:

| Profile | Users | Database | Secrets (PI password, AI key) |
|---|---|---|---|
| `desktop` (default) | one local user, logged in automatically | SQLite in the user data dir | OS keyring when available |
| `hosted` | allauth accounts, login required | PostgreSQL (`CCP_DB_*`) | never stored; typed per run, or `CCP_PI_PASSWORD` / `CCP_AI_API_KEY` |
| `test` | desktop behaviour, or hosted with `CCP_TEST_MULTI_USER=1` | in-memory SQLite | session |

Every model row has an owner and every view filters by it, so both profiles share
the code. Secrets reach a background job through the cache under the job id and
are deleted when the job reads them; they are never written to a model or a
`.ccp` file.

Hosted deployment: `deploy/hosted/` (Dockerfile and a compose file with
PostgreSQL, gunicorn, two `default` workers and one `monitoring` worker). REFPROP
is mounted, never baked into an image. Desktop packaging: `build/ccp_web.spec`
(PyInstaller, one-folder app).

## Layout

```
ccp_web/
  settings/          base, desktop, hosted, test
  services/          pure Python (no Django): units, gas, schemas, ccpfile,
                     performance_test, curves, plant_data, evaluation
  core/              models, jobs, owner scoping, .ccp import/export views,
                     files, template tags, shared templates
  performance_test/  straight-through and back-to-back pages
  curves/            curves conversion page
  evaluation/        performance evaluation, report, online monitoring
  digitizer/         curves digitizer (performance-curve PDFs)
  agent/             agent API: tokens, revisions/undo, notes, the HTTP API,
                     page adapters; stdlib-only client, CLI and MCP server
  templates/ static/ launcher.py cli.py
```

- A case stores its inputs with the flat key names of the Streamlit
  `session_state.json` (`services/schemas.py` lists every key per page), so
  import and export are lossless and form inputs are named by those keys.
- Long calculations are `django-tasks` jobs (`core/jobs.py`); pages poll a job
  partial with htmx and swap in the results when it finishes.
- Figures of compressors and impellers render in the request from the stored
  TOML (cached per process); evaluation figures are built by the job because
  `Evaluation.load` takes seconds.
- `pint`'s `barg` unit and `ccp.config.POLYTROPIC_METHOD` are process globals;
  services set them inside `units.state_context(state)`, which holds a lock.

## Agent API

AI coding agents (Claude Code, Copilot, ...) work with the case the user has
open: they read its inputs and results, change its inputs, start its
calculation and post notes the user sees. Every agent write is undoable from
the browser. The agent-side cookbook is
`ccp/agent_skills/ccp/live_app.md`.

- **Auth.** The API (`agent/api.py`, at `api/agent/v1/`) takes a bearer token
  (`Authorization: Bearer ccpa_...` or `X-CCP-Token`), never the session: the
  desktop server logs every browser request in, so a session would let any
  local process act as the user. `LocalUserMiddleware` skips `/api/`, and API
  views are `login_not_required` and `csrf_exempt`. Tokens (`AgentToken`) store
  only a sha256 digest. Scope is `read` or `write` (403 on writes for a read
  token). The desktop launcher issues a `desktop` token at each start and
  writes it with the URL and pid to `<data dir>/agent.json` (0600), removed at
  exit (`--no-agent` skips it). Hosted users create `personal` tokens on
  `agent/tokens/`. Every query goes through `for_user(token.owner)`; secrets
  are never accepted or returned, so runs that need the PI password or the AI
  key are refused with a message to start them in the browser. The keys that
  decide where a remembered secret is sent (`revisions.AGENT_READONLY_KEYS`:
  PI server, auth method and user, AI provider and Azure endpoint) are
  read-only for the agent; a case it creates from a `.ccp` upload gets their
  defaults.
- **Writes.** `agent/revisions.py` `record_agent_write` applies JSON values
  through `core.state.apply_values` (the form coercion, plus loud errors:
  unknown keys with close matches, invalid values, a `gas` convenience key),
  runs the page's post-save hooks (`core.state.POST_SAVE_HOOKS`) and records an
  `AgentRevision` with before/after of the changed keys (for the gas table,
  of the changed gases) under a row lock, plus the keys the write itself
  asked for (`requested`). Each revision bumps `Case.revision`. `undo` puts
  back the requested keys, runs the hooks again (undoing a flow method switch
  restores the measured flows) and then the other recorded keys, as a new
  revision; undoing an undo is a redo, and the default undo skips plain undos.
  `AgentNote` holds plain-text notes. Jobs update the state only where it
  still holds what they started from (`JobContext.update_state`), so a value
  an agent writes during a run is kept.
- **Stale-form guard.** Pages embed `Case.revision` (`ccp-case-rev` meta);
  htmx requests send it as `X-CCP-Rev`. `core.state.save_post` drops the keys
  agents changed after that revision before applying a form, so an autosave
  from a page rendered before an agent write cannot overwrite it; the response
  carries `HX-Refresh: true`, and calculate/run views start no job.
- **Browser side.** `static/ccp_web/js/agent.js` posts presence (case, page,
  section) to `agent/presence/`, polls `agent/poll/` (2 s visible, 10 s
  hidden), reloads to show agent changes with a highlight and an Undo toast
  (a banner instead while an input is focused, and never before a pending
  autosave is sent), shows notes and follows `open` navigations. The poll also
  reports the last job the agent started (`agent_job`), and the page reloads
  to show it. The top-bar Agent drawer (`agent/panel/<case>/`) lists
  revisions with Undo and the notes.
- **Adapters.** Calculate, results and figures are per page:
  `agent/adapters.py` maps app types to `<app>/agent.py` modules (`start`,
  `results`, `figures`, `figure`) that call the same functions as the page
  buttons (e.g. `performance_test.views.start_calculation`).

| Endpoint (under `api/agent/v1/`) | Does |
|---|---|
| `GET ""`, `GET context`, `POST context/open` | API info; what the user has open; make the browser open a case |
| `GET projects`, `GET\|POST cases` | list; create a case (JSON or a `.ccp` upload) |
| `GET cases/<id>`, `POST cases/<id>/duplicate`, `GET cases/<id>/export` | case detail; copy; `.ccp` download |
| `GET\|PATCH\|POST cases/<id>/state` | read; write `{values, note}` as one revision |
| `POST cases/<id>/calculate`, `GET jobs/<id>`, `POST jobs/<id>/cancel` | start the page's job (`{params, wait}`); long-poll (≤ 60 s per call, a few seconds for a monitoring job, whose `result.view.figures` lists figure ids instead of the figures); cancel |
| `GET cases/<id>/results`, `GET cases/<id>/figures[/<fig>]` | results JSON; figures as `data`, `plotly` or `png` (kaleido) |
| `GET cases/<id>/revisions`, `POST cases/<id>/undo` | agent revisions; undo |
| `GET\|POST cases/<id>/notes` | notes |
| `GET schema/<app_type>` | state keys with kinds, options, units keys, units, calculate params |

Errors are JSON `{"error", "details"}`: 400 for invalid input, 401/403 for the
token, 404 for another owner's rows or an unknown path, 501 for a page
without an adapter.

The agent side needs only the standard library (no Django), so it works where
ccp is installed without the `web` extra (`agent/discovery.py`, `client.py`,
`cli.py`, `mcp.py`; `cli.py` dispatches `ccp-web agent` before any Django
setup). It finds the app through `CCP_AGENT_URL` / `CCP_AGENT_TOKEN`,
`CCP_AGENT_FILE` or the agent file:

```bash
ccp-web agent context                       # JSON on stdout, errors on stderr
ccp-web agent set suction_pressure_point_1=5.4 --note "try 5.4 barg"
ccp-web agent calc --wait 90
ccp-web agent results
ccp-web agent undo
claude mcp add ccp -- ccp-web agent mcp     # MCP stdio server
```

## Frontend

htmx 2, Alpine.js 3 and Plotly are vendored in `static/ccp_web/vendor/` with the
fonts, so the desktop app works offline. Styles follow the "CCP Performance"
design (tokens in `static/ccp_web/css/input.css`) through Tailwind 4. The built
`app.css` is committed; rebuild it after changing templates or `input.css`:

```bash
TAILWINDCSS_VERSION=v4.1.14 uv run tailwindcss \
  -i ccp_web/static/ccp_web/css/input.css -o ccp_web/static/ccp_web/css/app.css --minify
```

htmx attribute inheritance is disabled (`htmx-config` meta tag): every element
names its own target.

## Tests

```bash
uv run pytest ccp_web/tests                        # desktop profile
CCP_TEST_MULTI_USER=1 uv run pytest ccp_web/tests  # hosted owner model
uv run pytest ccp_web/tests --run-full-evaluation  # adds a full Evaluation rebuild (minutes)
```

`test_flows.py` reproduces the flows of `ccp/tests/test_app.py` through the views.
