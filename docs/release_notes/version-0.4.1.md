# Version 0.4.1

Version 0.4.1 adds a driver-side power estimation subpackage, explicit
controls over parallel execution, a packaged cookbook for AI coding agents,
and restores compatibility with plotly 7.

## Highlights

- New `ccp.drivers` subpackage with `InductionMotor` to estimate the shaft
  power delivered by the driver from field measurements and compare it with
  the thermodynamic shaft power computed by ccp.
- Parallel execution can now be disabled or capped globally
  (`ccp.config.PARALLEL`, `ccp.config.POOL_SIZE`), and a script missing the
  `if __name__ == "__main__"` guard fails fast with an actionable error
  instead of hanging.
- A ccp cookbook is shipped with the package as an agent skill and can be
  installed with the `ccp-install-skill` command.
- `import ccp` works on plotly 7.

## New features

- **Drivers subpackage with induction motor power estimation**
  ([#155](https://github.com/petrobras/ccp/pull/155)) — `ccp.drivers`
  estimates the shaft power delivered by the compressor driver so it can be
  compared with `Point.power_shaft`. `InductionMotor` implements the
  DOE/IEEE 112 field methods (input power, line current and slip, with
  voltage compensation and part-load efficiency curves) and supports VFD
  operation through `supply_frequency` and `vfd_efficiency`. The
  `Driver.compare()` helper returns a `PowerComparison` with driver power,
  power transmitted through coupling/gearbox, point shaft power and the
  absolute and relative deltas. Drivers are serializable to JSON and TOML.
  New electrical entries (voltage, current, power factor, frequency,
  efficiency) were added to the units checked by `check_units`.

- **Parallel execution controls and fail-fast pool startup**
  ([#158](https://github.com/petrobras/ccp/pull/158)) — every
  multiprocessing pool created by ccp (`Impeller.convert_from`,
  `Impeller.load_from_dict`, `Impeller.load_from_engauge_csv`, `Evaluation`)
  now goes through `ccp.parallel.create_pool()`:

  ```python
  import ccp

  ccp.config.PARALLEL = False  # run every ccp calculation serially
  ccp.config.POOL_SIZE = 4  # or cap the number of worker processes
  ```

  The `CCP_PARALLEL`, `CCP_POOL_SIZE` and `CCP_POOL_START_TIMEOUT`
  environment variables override the globals, so parallelism can be tuned in
  containers and sandboxes without touching code. Worker startup is verified
  with a no-op task: if a full worker generation dies before it completes
  (the symptom of a missing `if __name__ == "__main__"` guard), ccp raises
  a `RuntimeError` pointing at the cause and the serial escape hatch instead
  of repopulating dying workers forever. Invalid settings raise a
  `ValueError` naming the offending variable.

- **ccp cookbook as an agent skill**
  ([#157](https://github.com/petrobras/ccp/pull/157)) — nine self-contained
  recipe files plus a `SKILL.md` entry point, following the
  [Agent Skills](https://agentskills.io) open standard, cover states and
  fluids, performance points, impellers, Engauge curve import, conversion to
  new suction conditions, ASME PTC 10 similarity, flow orifice metering,
  operational data evaluation and common gotchas. The recipes ship in the
  wheel, and the new `ccp-install-skill` console script installs them into
  the personal skills directory of each detected AI coding agent (Claude
  Code, GitHub Copilot, Cursor, Codex), with `--agent`, `--project`,
  `--dest` and `--uninstall` options. The installed `SKILL.md` is stamped
  with the ccp version so agents can flag a stale skill after an upgrade.

## Bug fixes

- **plotly 7 compatibility**
  ([#162](https://github.com/petrobras/ccp/pull/162)) — plotly 7.0.0
  removed the `mapbox` layout key and the `scattermapbox` trace type, which
  the ccp plotly template still registered, so `import ccp` raised
  `ValueError: Invalid property specified ... 'scattermapbox'`. The entries
  were dropped; the template loads on plotly 5.x through 7.

- **Module doctests**
  ([#156](https://github.com/petrobras/ccp/pull/156)) — fixed the nine
  module doctests in `processing.py`, `units.py`, `fo.py` and `impeller.py`
  that failed when collected with `--doctest-modules`.

- **Docs dark mode**
  ([#159](https://github.com/petrobras/ccp/pull/159)) — the landing-page
  card icons no longer render on white boxes in dark mode.

## Infrastructure

- README badges updated: ruff replaces black, and a CI status badge was
  added ([#154](https://github.com/petrobras/ccp/pull/154)).
