# Impellers and Performance Maps

Source: `docs/user_guide/tutorial.ipynb`, `ccp/impeller.py`

An `Impeller` is a container of `Point` objects. Points with the same speed are grouped into `Curve` objects, forming the performance map.

## Build from points

```python
import ccp

Q_ = ccp.Q_

fluid = {"CarbonDioxide": 0.79585, "Nitrogen": 0.16751, "Oxygen": 0.02903}
suc = ccp.State(fluid=fluid, p=Q_(3, "bar"), T=300)

# see the points recipe for the ways to define a Point
point0 = ccp.Point(
    suc=suc,
    disch=ccp.State(fluid=fluid, p=Q_(7.255, "bar"), T=391.1),
    speed=Q_(7941, "RPM"),
    flow_m=Q_(34203.6, "kg/hr"),
    b=0.0285,
    D=0.365,
)
point1 = ccp.Point(
    suc=suc,
    disch=ccp.State(fluid=fluid, p=Q_(6.754, "bar"), T=382.1),
    speed=Q_(7941, "RPM"),
    flow_m=Q_(36204.8, "kg/hr"),
    b=0.0285,
    D=0.365,
)

imp = ccp.Impeller([point0, point1])
```

A ready-made example (natural gas + CO2 map loaded from digitized curves) is available for experimenting:

```python
imp = ccp.impeller_example()
```

## Interpolate a point or a curve anywhere in the map

```python
p = imp.point(flow_v=5.5, speed=900)        # SI: m³/s, rad/s
p = imp.point(flow_m=60, speed=Q_(8594, "RPM"))
c = imp.curve(speed=900)                    # a ccp.Curve at that speed
```

Speeds outside the mapped range are extrapolated (the returned objects carry an `_extrapolated` flag).

## Access data

```python
imp.points               # list of all points
imp.curves               # list of ccp.Curve (one per speed)
c = imp.curves[0]
c.speed                  # curve speed, rad/s
c.flow_v, c.head, c.eff, c.power   # arrays (pint) along the curve
c.disch.p()              # discharge pressure array along the curve
c.head_interpolated(5.5) # interpolate head at a flow_v (m³/s) on this curve
```

## Plotting

Every result has a `<attr>_plot` method returning a plotly Figure. Passing `flow_v` and `speed` also draws the interpolated curve and marks the point:

```python
fig = imp.head_plot(flow_v=5.5, speed=900)
fig = imp.eff_plot(speed_units="RPM", flow_v_units="m³/h")
fig = imp.power_plot()
fig = imp.disch.T_plot(flow_v=5.5, speed=900)   # discharge temperature
fig = imp.disch.p_plot(speed_units="RPM")       # discharge pressure
fig = imp.disch.rho_plot(
    flow_v=Q_(20000, "m³/h"),
    speed=Q_(8594, "RPM"),
    flow_v_units="m³/h",
    speed_units="RPM",
    rho_units="g/cm³",
)
```

Available on `imp`: `head_plot`, `eff_plot`, `power_plot`, `power_shaft_plot`, `torque_plot`, `phi_plot`, `psi_plot`, and `disch.p_plot`, `disch.T_plot`, `disch.h_plot`, `disch.s_plot`, `disch.rho_plot`. Unit keywords follow the pattern `<attr>_units`, plus `flow_v_units`/`flow_m_units` and `speed_units`.

To compare two impellers (e.g. original vs. converted): `imp.head_compare(other_imp)`, `imp.eff_compare(other_imp)`, etc.

## Save / load / export

```python
imp.save("map.toml")                 # .toml or .json
imp2 = ccp.Impeller.load("map.toml")
imp.export_to_excel("map.xlsx")      # one sheet per curve
```
