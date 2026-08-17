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

- ccp parallelizes impeller construction, conversion and evaluation internally with a **forkserver/spawn** multiprocessing context (`ccp/parallel.py`). Workers re-import your `__main__` module, so a plain script that builds an `Impeller` (including `load_from_engauge_csv`), calls `Impeller.convert_from` or creates an `Evaluation` at module top level dies with `RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase`. Put the code under a guard:

```python
if __name__ == "__main__":
    imp = ccp.Impeller.load_from_engauge_csv(...)
```

- Interactive sessions (IPython, Jupyter, `python` REPL) are not affected.

## Performance

- REFPROP flash calculations dominate runtime. Creating points (especially `Impeller` construction and `convert_from`) takes seconds — expect map conversions to take minutes for many curves; ccp parallelizes conversions internally with multiprocessing.
- Prefer `state.update(...)` over creating new `State` objects in loops.
