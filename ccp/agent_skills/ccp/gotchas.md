# Common Gotchas

## Units

- **Bare floats are SI**: `T=300` is kelvin, `p=101325` is Pa, `speed=900` is rad/s, `flow_v=5.5` is m³/s. For anything else use pint: `ccp.Q_(7941, "RPM")`, `Q_(40, "degC")`, `Q_(30, "bar")`, `Q_(34203.6, "kg/hr")`.
- Results are pint quantities: convert with `.to("kJ/kg")`, take the magnitude with `.m` or `.magnitude`. Never divide by 1000 by hand.
- Head in meters from a datasheet: multiply by g0 — `head_units="m*g0"` in `load_from_engauge_csv`, or `Q_(1500, "m*g0")`.
- Efficiency is a fraction (0.75), not a percent.

## States and fluids

- `State` properties are **methods**: `state.T()`, `state.rho()`, not attributes. Pass units to convert: `state.p("bar")`.
- The `fluid` dict uses **mole fractions** and is normalized automatically (percentages work). Repeated aliases that resolve to the same component (e.g. `"butane"` and `"n-butane"`) raise an error.
- Creating a `State` requires keyword arguments, including `fluid=`.
- Without REFPROP installed, ccp warns and falls back to CoolProp's `HEOS` backend — same API, slightly different property values. `ccp.config.EOS` controls the default.

## Points and impellers

- `b` (impeller width) and `D` (impeller diameter) have defaults (0.005 m / 0.5 m); head/eff/power are unaffected, but `phi`, `psi`, Mach, Reynolds — and therefore conversions and similarity checks — need the real geometry.
- A `Point` needs a *sufficient* argument combination (e.g. `suc + disch + speed + flow`); otherwise `ValueError` is raised listing what it received. Efficiency outside 0.3–1.0 is treated as out of range.
- `Impeller` deep-copies its points: changing `point0` afterwards does not change `imp.points[0]`.
- `Impeller.point(flow_v=..., speed=...)` interpolates and extrapolates without complaint — check the map range (`imp.flow_v`, `imp.speed`) or the returned point's `_extrapolated` flag.
- Speed grouping into curves is exact: points on the "same" curve must have identical speed values.

## Plotting

- All plot methods return a plotly `Figure` — call `fig.show()` to display or `fig.write_image("f.png")` to save.
- Default plot units are SI (flow in m³/s, speed in rad/s); pass `flow_v_units="m³/h"`, `speed_units="RPM"`, `head_units="kJ/kg"`, etc. for readable axes.
- `_plot` methods accept `flow_v`/`flow_m` and `speed` to highlight an interpolated point/curve; these arguments are in SI unless given as `Q_`.

## Multiprocessing

- ccp parallelizes impeller construction, conversion and evaluation internally with a **forkserver/spawn** multiprocessing context (`ccp/parallel.py`). Workers re-import your `__main__` module, so a plain script that builds an `Impeller` (including `load_from_engauge_csv`), calls `Impeller.convert_from` or creates an `Evaluation` at module top level cannot start its workers and fails with a `RuntimeError` telling you to guard the entry point:

```python
if __name__ == "__main__":
    imp = ccp.Impeller.load_from_engauge_csv(...)
```

- Interactive sessions (IPython, Jupyter, `python` REPL) are not affected.
- `ccp.config.PARALLEL = False` (or the `CCP_PARALLEL=0` environment variable) disables multiprocessing entirely — everything runs serially in the current process, no guard needed. Useful for debugging, small jobs and restricted environments (containers, sandboxes).
- `ccp.config.POOL_SIZE = 4` (or `CCP_POOL_SIZE=4`) caps the number of worker processes; the default is one per CPU, and every worker loads REFPROP.
- Worker startup is bounded by a 60 s deadline; on machines where it is genuinely slow (cold starts, antivirus-scanned spawn on Windows), raise it with `CCP_POOL_START_TIMEOUT=180` (seconds).

## Performance

- REFPROP flash calculations dominate runtime. With the default phase policy (`ccp.config.DEFAULT_PHASE = "gas"`, see states_and_fluids.md) a point costs a few milliseconds and an 18-point map converts in well under a second on REFPROP; the first multiprocessing pool of a process costs 1 to 2 s to start (`ccp.parallel.warm_up()` pays it early, e.g. from an application's startup).
- `Impeller.point()` and `Impeller.curve()` interpolate from cached curve data (one point solve per `point()` call); the cache lives on the impeller and is dropped when it is pickled.
- CoolProp `HEOS` is usable for multi-component mixtures only with the phase policy on: an unconstrained HEOS flash of a 10-component gas takes 10 to 200 ms and the historical unconstrained point solve took over a minute.
- `ccp.config.PHASE_CHECK = True` verifies every solved discharge with an unconstrained flash (a phase-stability analysis per point, up to ten times the point solve); it re-solves the point without an imposed phase and emits `ccp.point.PhaseWarning` when the discharge lies inside the phase envelope. Off by default.
- Prefer `state.update(...)` over creating new `State` objects in loops.
