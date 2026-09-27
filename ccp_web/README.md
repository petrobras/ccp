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
