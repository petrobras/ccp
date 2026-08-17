# Flow Orifice Metering

Source: `ccp/fo.py`

`FlowOrifice` calculates mass flow from the differential pressure across an orifice plate (ISO 5167 flow coefficient correlation), which is how flow is usually measured around a compressor.

## Calculate flow from delta-p

```python
import ccp

Q_ = ccp.Q_

fluid = {"R134A": 0.018, "R1234ZE": 31.254, "N2": 67.588, "o2": 1.14}
state = ccp.State(p=Q_(10, "bar"), T=Q_(40, "degC"), fluid=fluid)

fo = ccp.FlowOrifice(
    state,
    delta_p=Q_(0.1, "bar"),   # pressure drop across the orifice
    D=Q_(250, "mm"),          # pipe internal diameter
    d=Q_(170, "mm"),          # orifice bore diameter
    tappings="flange",        # "flange" (default), "corner" or "D D/2"
)

fo.flow_m.to("kg/h")   # mass flow (also available as fo.qm)
fo.flow_v              # volumetric flow at the state conditions, m³/s
```

- `state` is the fluid state at the orifice. By default it is taken as the **upstream** state; pass `state_upstream=False` if the measurement is downstream of the plate (ccp then adds `delta_p` back).
- The discharge coefficient is iterated on the Reynolds number automatically.

Use the resulting `flow_m`/`flow_v` to build performance points (see the points recipe). The `Evaluation` class accepts `delta_p` data directly and does this internally (see the evaluation recipe).
