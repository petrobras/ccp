(gauge_pressure)=
# Gauge pressure

ccp objects hold absolute pressures only. Gauge pressures can be used for input
and output with the units `barg`, `psig`, `kPag` and `MPag`:

```python
import ccp

Q_ = ccp.Q_

s = ccp.State(p=Q_(10, "barg"), T=Q_(300, "degK"), fluid={"CO2": 1})
s.p("bar")   # 11.01325 bar
s.p("barg")  # 10 barg
```

## Ambient pressure

The gauge units are relative to `ccp.config.AMBIENT_PRESSURE`, in Pa, which is
1 atm (101325 Pa) by default. Change it for the whole process, or for a block of
code:

```python
ccp.set_ambient_pressure(Q_(0.95, "bar"))

with ccp.ambient_pressure(Q_(0.9, "bar")):
    s = ccp.State(p=Q_(10, "barg"), T=Q_(300, "degK"), fluid={"CO2": 1})

s.p("bar")  # 10.9 bar
```

The previous value is restored on exit. The context holds a lock, so contexts in
different threads run one at a time. Programs that serve several users in one
process should use the context, not `set_ambient_pressure`. Do not wait inside a
context for another thread that also enters one, and do not `await` or `yield` in
it: the lock belongs to the thread.

## Without global state

`gauge_to_absolute` and `absolute_to_gauge` work with any pressure unit,
including those that have no gauge version in pint, such as kgf/cm². The gauge
value is in a plain unit:

```python
ccp.units.gauge_to_absolute(Q_(10, "kgf/cm²"), ambient_pressure=Q_(0.95, "bar"))
ccp.units.absolute_to_gauge(Q_(11, "bar"), units="psi", ambient_pressure=Q_(0.95, "bar"))
```

Without `ambient_pressure`, `ccp.config.AMBIENT_PRESSURE` is used.

## Limits

- A gauge quantity is not bound to the ambient pressure it was created with: the
  value in effect when it is converted is used, also in other threads. Convert
  gauge values to absolute (or take `.m`) before changing the ambient pressure,
  and prefer the functions above when it varies.
- Worker processes have the default ambient pressure. ccp converts to absolute
  before sending values to its workers; do the same in your own.
- Gauge units are for input and display. Like degC in pint, they cannot be
  multiplied or divided, `Q_(3, "barg") - Q_(1, "barg")` is in `delta_barg`, and
  prefixes (`mbarg`) are not available. Calculate with absolute units.
- Pressure differences (`delta_p`) have no gauge unit: ccp raises an error, use
  `bar`.
- `Evaluation` data can be in gauge units (`data_units`). The ambient pressure is
  kept with the evaluation (`ambient_pressure` argument) and saved with it.
