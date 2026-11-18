# Cone Meter Metering (V-cone, ISO 5167-5)

Source: `ccp/fc.py`

`FlowCone` calculates mass flow from the differential pressure across a cone (V-cone) meter, following ISO 5167-5. The API mirrors `FlowOrifice`.

## Calculate flow from delta-p

```python
import ccp

Q_ = ccp.Q_

fluid = {"R134A": 0.018, "R1234ZE": 31.254, "N2": 67.588, "o2": 1.14}
state = ccp.State(p=Q_(10, "bar"), T=Q_(40, "degC"), fluid=fluid)

fc = ccp.FlowCone(
    state,
    delta_p=Q_(0.1, "bar"),  # upstream tapping minus back-of-cone tapping
    D=Q_(250, "mm"),  # measured pipe internal diameter at the meter
    dc=Q_(180, "mm"),  # cone diameter; or d=beta * D (equivalent diameter)
)

fc.flow_m.to("kg/h")  # mass flow
fc.flow_v  # volumetric flow at the upstream state, m³/s
fc.beta, fc.C, fc.epsilon, fc.reynolds  # diameter ratio, C, expansibility, ReD
```

- Geometry: give `D` and exactly one of `dc` (cone diameter at the beta edge) or `d` (equivalent diameter, beta = d/D). When the data sheet only gives beta, pass `d=beta * D`. Use the measured internal diameter, not the nominal size.
- `state` is the upstream state by default; pass `state_upstream=False` for a downstream state (ccp then uses p + delta_p and leaves the given state unchanged).
- Expansibility: ε = 1 − (0.649 + 0.696 β⁴) Δp / (κ p1), with κ = `state.kv()`.

## Discharge coefficient

```python
import numpy as np

ccp.FlowCone(state, Q_(0.1, "bar"), Q_(250, "mm"), dc=Q_(180, "mm"))  # ISO C = 0.82
ccp.FlowCone(state, Q_(0.1, "bar"), Q_(250, "mm"), dc=Q_(180, "mm"), C=0.805)  # calibrated

# calibration certificate as a table (Re, C): interpolated in log10(Re)
cal = ([2e5, 1e6, 5e6], [0.801, 0.804, 0.806])
ccp.FlowCone(state, Q_(0.1, "bar"), Q_(250, "mm"), dc=Q_(180, "mm"), C=cal)

# or any C(Re) function; C and ReD are iterated to agreement
ccp.FlowCone(
    state, Q_(0.1, "bar"), Q_(250, "mm"), dc=Q_(180, "mm"),
    C=lambda Re: 0.80 + 0.002 * np.log10(Re / 1e5),
)
```

## Limits and warnings

`ccp.fc.FlowMeterWarning` is raised as a warning, and `fc.outside_limits` (dict, empty when fine) lists what was exceeded:

- uncalibrated C = 0.82 (5 % uncertainty, k = 2): 50 mm ≤ D ≤ 500 mm, 0.45 ≤ β ≤ 0.75, 8e4 ≤ ReD ≤ 1.2e7 (meters with β > 0.75 must be calibrated);
- calibration table: ReD outside the calibrated range (C is held at the nearest end value; extrapolation is not permitted);
- any C: p2/p1 < 0.75, the validity limit of the expansibility equation.

A calibrated C (number, table or function) switches off the D, β and ReD checks of the uncalibrated value.

## In an evaluation

`ccp.Evaluation` computes the flow from `delta_p` with a cone meter when given `flow_meter="cone"` plus `D`, `d` or `dc`, and optionally `C` (see the evaluation recipe). Each exceeded limit is reported once with the number of rows.
