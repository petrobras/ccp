# Working with the open ccp app

Source: `ccp_web/agent/` (`cli.py`, `client.py`, `mcp.py`, `api.py`), `ccp_web/README.md`

The ccp web app (`ccp-app` desktop window or `ccp-web serve`) exposes an agent API. Through it you can see which case the user has open, read its inputs and results, change its inputs, run its calculation, and post notes that show up on the user's page.

Use it when the user refers to the running app: "the app", "what I have open", "this case", "these results", "change the suction pressure and recalculate". For standalone calculations in a script, use the library recipes instead.

**Requirements.** The CLI (`ccp-web agent ...`), the Python client (`ccp_web.agent.client`) and the MCP server need only the base `ccp-performance` package; they use the standard library. The app itself needs the `web` extra (`pip install "ccp-performance[desktop]"` or `[web]`) and must be running. On the same machine it writes its URL and a fresh token to `agent.json` in its data directory each time it starts. The CLI and client find that file automatically, so no configuration is needed.

## Workflow

```bash
ccp-web agent context          # what the user has open: presence.case (id 3 here), page, section, stale
ccp-web agent get --case 3 --keys suction_pressure_point_1,suction_pressure_units
ccp-web agent results --case 3 # the results the page shows
# ... explain, or change something:
ccp-web agent set --case 3 suction_pressure_point_1=5.4 --note "try 5.4 barg at point 1"
ccp-web agent calc --case 3 --wait 90   # the page's Calculate button; returns the job
ccp-web agent results --case 3
ccp-web agent note --case 3 "Point 1 at 5.4 barg: head ratio 1.01, inside the 4 % band."
```

`--case N` (available on `get`, `set`, `calc`, `results`, `figures`, `figure`, `undo`, `revisions`, `note`, `notes`, `duplicate`, `export`) selects the case. Without it, a command uses the case the user has open *at that moment*. Read `context` once and pass that id with `--case` on every later command: if the user has two windows open, or switches cases, commands without `--case` can land on different cases. `set` returns the `case` it wrote.

Every command prints JSON on stdout. On an error it prints `{"error", "status", "details"}` on stderr and exits with status 1, or 2 for a usage error.

## Conventions

- **Edit the open case directly.** Each `set` is one revision, and the user can undo it from the toast or the Agent drawer in the browser. Tell them so after you change something. Use `duplicate` only if the user asks for a copy.
- Make **one `set` per logical change**, always with a short `--note` saying why. The note is what the user sees next to the Undo button.
- After a `set`, the stored results are stale: `results` reports `inputs_saved_after_calculation: true`. Run `calc` again before you quote numbers. The page shows the new results by itself once the job finishes.
- If `presence.stale` is true (the page has not reported for more than 2 min) or `presence.case` is null, the app may not be showing that case. Say so, or ask the user to open it. `open <case>` makes the browser navigate to a case within about 2 s.
- **Never ask for, accept or send secrets** such as the PI password or the AI API key. The API refuses runs that need them. Ask the user to start a PI-data evaluation run, or a report with the AI analysis, in the browser. The keys that decide where those secrets go (`pi_server_name`, `pi_auth_method`, `pi_username`, `ai_provider`, `ai_azure_endpoint`, `ai_azure_deployment`) are read-only for the agent: ask the user to change them in the browser. A case the agent creates from a `.ccp` file gets their defaults (the reply's `warnings` lists the ones reset).
- Files (curve CSVs, PDFs, plant data spreadsheets) are uploaded by the user in the browser. The API cannot upload them; it can only create a whole case from a `.ccp` file.
- Notes are plain text, shown escaped. Markdown is not rendered.

## Values

- Find the keys with `ccp-web agent schema <app_type> [--filter text]` (the filter matches keys, labels and options). App types are `straight_through`, `back_to_back`, `curves_conversion`, `curves_digitizer` and `performance_evaluation`. Each field gives `key`, `kind`, `default`, `options`, `units_key` when the value has a unit and, when it has one, `param: {label, units, help}`. An unknown key is rejected with close-match suggestions.
- Kinds: `text` (a number kept as text: `5.4` and `"5.4"` are the same, and an empty string clears the field), `number` (stored as a JSON number; the curves conversion and evaluation pages), `string` (free text such as names and PI tags), `select` (one of `options`), `bool`, `gas` (the name of one of the six gases) and `json` (the gas table; use the `gas` key below). Use `.` as the decimal separator.
- Keys are the page's flat state names, e.g. `suction_pressure_point_1`, `speed_point_guarantee`, `flow_units`.
- **A number is in the unit held by its field's `units_key`.** Read that key before writing a number. Do not guess it from the name: `suction_pressure_point_1` is in `suction_pressure_units`, `speed_point_guarantee` in `speed_units_point_guarantee`, and on `back_to_back` both sections' guarantee values share section 1's key (`discharge_temperature_section_2_point_guarantee` is in `discharge_temperature_units_section_1_point_guarantee`). `get --keys ...` also returns `units_keys` for the keys you asked for.
- Units keys accept the listed options or any unit pint parses with the same dimension (a temperature unit for a pressure key is rejected). In the test-data tables, one units key covers the whole column (every point). Changing it re-labels the existing numbers; it **does not convert them**. To change units, send the converted numbers in the same `set`.
- On the CLI, `key=value` values are parsed as JSON literals (`4.5`, `true`, `{"a": 1}`), otherwise kept as text (`barg`). Quote a JSON string to keep it as text: `'key="001"'`. Use `--json '{...}'` for nested values; `key=value` arguments override `--json`.
- Gas compositions use the `gas` convenience key. Gases are `gas_0` … `gas_5`. Give each composition in mol % (the page's gas table is in mol %): the values are stored as given, and ccp normalizes them when it calculates. Component names are checked against the names and aliases of `ccp.fluid_list`. A gas you leave out keeps its composition.

```bash
ccp-web agent set --json '{"gas": {"gas_1": {"name": "lean", "composition": {"methane": 90, "ethane": 10}}}}' --note "lean gas for case B"
```

- Errors come back as HTTP 400. Unknown keys are in `details.unknown` (`{key: [close matches]}`), bad values in `details.invalid` (`{key: message}`), and fields the calculation refuses in `details.errors`, the same messages the page shows. Fix the input and retry.

## Calculations per page

`calc` runs the page's button. Pass parameters with `--param key=value` (repeatable). `schema` lists them under `calculate_params`.

| App type | `calc` | Notes |
|---|---|---|
| `straight_through`, `back_to_back` | `calc` | `--param calculate_speed=true` finds the speed that meets the guarantee discharge pressure |
| `curves_conversion` | `calc --param action=load --param letter=A`, then `calc` (`action=convert`, the default) | the curve files must already be uploaded |
| `performance_evaluation` | `calc` (`action=run`, `--param mode=full_rebuild` re-evaluates everything), `--param action=load --param letter=A` (a design case's Load button; a run needs one loaded, see `design_cases` in `results`), `--param action=report --param ai=false`, `action=monitoring_start` / `monitoring_stop` | data source `pi` needs the PI password: the user starts it in the browser. `monitoring_start` returns within seconds with the running job (its `result.view.figures` lists figure ids; read them with `figure`). `results` → `monitoring.metrics[]` give `value`/`units` and `delta`/`delta_units` (`%` relative to expected; `percentage points` for efficiency). The report is an HTML file the user opens in the browser (the Report button on the page); the agent cannot download it, so tell the user it is ready there |
| `curves_digitizer` | `calc` (no params) | pages come from the `digitize_pages` key |

`calc --wait S` (default 90) waits up to S seconds and returns the job (`status` is `succeeded`, `failed` or `cancelled`, or `pending`/`running` with `active: true` when the wait ran out). Continue with `job <id> --wait 60`, or stop it with `cancel <id>`. Keep each command under your shell tool's timeout (often 120 s): a killed command prints nothing, not even the job id. The server answers one call after at most 60 s; the CLI and client keep polling the job for the rest of the wait.

## Results and figures

```bash
ccp-web agent results                    # JSON tables: sections[].columns/rows, checks, all_ok
ccp-web agent figures                    # [{id, title, section}]
ccp-web agent figure head                # compact data: titles + traces x/y (6 significant digits)
ccp-web agent figure head --format plotly --out head.json
ccp-web agent figure head --format png --out head.png   # needs kaleido on the server, else 501
```

Column names carry their units, e.g. `Headₜ (kJ/kg)`. The ratio columns listed in `fraction_columns` are fractions (1.0 is 100 %). Results that are not computed yet come back as `{"available": false, "reason": ...}`.

To work on a case with the ccp library, export it: `ccp-web agent export --out case.ccp`. A `.ccp` is a zip archive with `session_state.json` (the inputs) and the stored TOML results. For a performance test, that TOML is `straight_through.toml` or `back_to_back.toml`:

```python
import zipfile

import toml
from ccp.compressor import StraightThrough

with zipfile.ZipFile("case.ccp") as z:
    compressor = StraightThrough.from_dict(
        toml.loads(z.read("straight_through.toml").decode())
    )
```

## CLI cheat sheet

| Command | Does |
|---|---|
| `status` | API version, user, token scope, app types, plus `context` |
| `context` | open case (`presence`) and recent cases |
| `cases [--project N] [--app-type T]`, `projects` | list |
| `get [--keys k1,k2]` | case summary, state, files, artifacts, latest jobs |
| `schema <app_type> [--filter text]` | state keys, kinds, options, units, calculate params |
| `set k=v ... [--note "..."] [--json '{...}']` | one undoable revision; returns `{case, revision, changed, warnings, revision_id}` |
| `calc [--wait S] [--param k=v]`, `job <id> [--wait S]`, `cancel <id>` | calculations |
| `results`, `figures`, `figure <id> [--format data\|plotly\|png] [--out f]` | outputs |
| `revisions`, `undo [--revision ID]` | agent revisions; `undo` takes back the newest agent change still in effect, so repeated `undo` steps back through your changes. To redo, `undo --revision <id of the undo revision>` (a revision with `redo: true` re-applied a change) |
| `note "text"` / `note --file f.txt` (`-` for stdin), `notes` | notes shown on the user's page |
| `open <case>`, `duplicate [--name]`, `export --out f.ccp`, `create <app_type> [--name] [--project N] [--from f.ccp]` | cases |
| `mcp` | MCP stdio server |

## Python client

```python
from ccp_web.agent.client import CcpAppError, connect

app = connect()  # finds the running app; nothing is sent yet
case = app.context()["presence"]["case"]  # None when no case is open
app.state(keys=["suction_pressure_point_1", "suction_pressure_units"])
app.set({"suction_pressure_point_1": 5.4}, note="try 5.4 barg at point 1")
job = app.calculate(wait=90)  # params as keywords, e.g. calculate_speed=True
results = app.results()
fig = app.figure("head")  # {"title", "x_title", "y_title", "traces": [...]}
app.undo()  # the newest agent revision
app.note("Head is 2 % above the guarantee at point 3.")
app.export(path="case.ccp")

try:
    app.set({"suction_presure_point_1": 5})
except CcpAppError as exc:
    print(
        exc.status, exc.error, exc.details
    )  # 400, unknown key(s): ..., {"unknown": {...}}
```

Methods that take `case=` (an id or a case summary dict) default to the open case: `case`, `state`, `set`, `calculate`, `results`, `figures`, `figure`, `revisions`, `undo`, `note`, `notes`, `duplicate`, `export`.

## MCP

```bash
claude mcp add ccp -- ccp-web agent mcp
```

The tools are `ccp_context`, `ccp_get_case`, `ccp_schema`, `ccp_set_values`, `ccp_calculate`, `ccp_job`, `ccp_results`, `ccp_figure` (without `id` it lists the figures), `ccp_undo`, `ccp_note`, `ccp_open_case` and `ccp_duplicate`. `ccp_calculate` and `ccp_job` wait at most 45 s (under the request timeout of common MCP clients); continue an `active: true` job with `ccp_job`. The server looks up the app on every call, so it keeps working across app restarts.

## Troubleshooting

- **`ccp app is not running — start it with ...`**: there is no agent file, or the process that wrote it has exited. Ask the user to start `ccp-app` or `ccp-web serve`. An app started with `--no-agent` writes no agent file.
- **401**: the token is stale. The app issues a new token at every start. Drop any `CCP_AGENT_TOKEN` you set by hand, or re-read the file.
- **WSL with the app on Windows**: point to the Windows file, e.g. `CCP_AGENT_FILE=/mnt/c/Users/<user>/AppData/Local/ccp/ccp/agent.json`. The app listens on Windows `127.0.0.1`, so this needs WSL mirrored networking; otherwise override the host with `CCP_AGENT_URL`. Alternatively set both `CCP_AGENT_URL` and `CCP_AGENT_TOKEN`.
- **Hosted app** (multi-user server): the user creates a personal token on the *Agent tokens* page (`/agent/tokens/`). Then set `CCP_AGENT_URL=https://<server>/` and `CCP_AGENT_TOKEN=ccpa_...`, or pass `--url` / `--token`. A read-scope token gets 403 on writes.
- **501 `not implemented`**: that page type has no adapter, or (for `--format png`) kaleido is missing. Use `--format data`.
- Resolution order for the URL and token is: `--url`/`--token`, then `CCP_AGENT_URL`/`CCP_AGENT_TOKEN`, then the file named by `CCP_AGENT_FILE`, then `agent.json` in the data directory (`$CCP_DATA_DIR`, or `~/.local/share/ccp`, `~/Library/Application Support/ccp`, `%LOCALAPPDATA%\ccp\ccp`).
