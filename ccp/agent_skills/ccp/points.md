# Performance Points

Source: `docs/user_guide/tutorial.ipynb`, `docs/user_guide/polytropic_methods.ipynb`, `ccp/point.py`

A `Point` is one operating point of the compressor map. Give it a sufficient combination of arguments and ccp solves for everything else (head, efficiency, power, discharge state, ...).

## From suction + discharge states (test data)

```python
import ccp

Q_ = ccp.Q_

fluid = {"CarbonDioxide": 0.79585, "Nitrogen": 0.16751, "Oxygen": 0.02903}
suc = ccp.State(fluid=fluid, p=Q_(3, "bar"), T=300)
disch = ccp.State(fluid=fluid, p=Q_(7.255, "bar"), T=391.1)

point = ccp.Point(
    suc=suc,
    disch=disch,
    speed=Q_(7941, "RPM"),
    flow_m=Q_(34203.6, "kg/hr"),
    b=0.0285,   # impeller width at outer blade diameter (m)
    D=0.365,    # impeller outer diameter (m)
)
```

## Other sufficient combinations

Always with `speed`, one flow (`flow_v` or `flow_m`), `b` and `D`:

- `suc`, `disch` — measured suction and discharge states
- `suc`, `disch_p`, `eff` — design data with discharge pressure and efficiency
- `suc`, `head`, `eff` — design data with head (J/kg) and efficiency
- `suc`, `head`, `power` — head and gas power (W)
- `suc`, `head`, `power_shaft`, `power_losses` — with shaft power and mechanical losses
- `suc`, `eff`, `volume_ratio` — used internally for conversions
- `suc`, `pressure_ratio`, `disch_T` — pressure ratio and discharge temperature

Optional extras: `power_shaft`, `power_losses`, `torque`, `surface_roughness`, and casing heat-loss inputs (`casing_area`, `casing_temperature`, `ambient_temperature`, `convection_constant`).

## Results

```python
point.head          # polytropic head, J/kg
point.eff           # polytropic efficiency, dimensionless
point.power         # gas power, W
point.power_shaft   # shaft power, W (includes losses)
point.disch.T()     # solved discharge state (a ccp.State)
point.flow_v        # m³/s
point.phi           # flow coefficient
point.psi           # head coefficient
point.volume_ratio  # suc.v() / disch.v()
point.mach          # impeller tip Mach number
point.reynolds      # Reynolds number
```

All are pint quantities: convert with `.to("kJ/kg")`, take magnitude with `.m`.

`print(point)` shows a summary table. `point.save("point.toml")` / `ccp.Point.load("point.toml")` persist a point (`.toml` or `.json`).

## Polytropic methods

The default head/efficiency calculation is Schultz (`"schultz"`, as in ASME PTC 10). Change globally or per point:

```python
ccp.config.POLYTROPIC_METHOD = "huntington"   # global — affects every Point created afterwards
ccp.config.POLYTROPIC_METHOD = "schultz"      # restore the default when done

# or per point, leaving the global default alone:
point = ccp.Point(
    suc=suc,
    disch=disch,
    speed=Q_(7941, "RPM"),
    flow_m=Q_(34203.6, "kg/hr"),
    b=0.0285,
    D=0.365,
    polytropic_method="sandberg_colby",
)
```

Options: `"schultz"`, `"huntington"` (3-point, most accurate vs. reference integration, slower), `"mallen_saville"`, `"sandberg_colby"`, `"sandberg_colby_multistep"`.

The individual functions are also available, taking suction and discharge states:

```python
ccp.point.head_pol_schultz(suc, disch)         # and eff_pol_schultz
ccp.point.head_pol_huntington(suc, disch)      # and eff_pol_huntington
ccp.point.head_pol_mallen_saville(suc, disch)
ccp.point.head_pol_sandberg_colby(suc, disch)
ccp.point.head_reference_2017(suc, disch)      # reference integration → (head, eff)
ccp.point.head_isentropic(suc, disch)          # and eff_isentropic
```
