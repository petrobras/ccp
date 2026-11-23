# Version 0.5.3

Version 0.5.3 adds gauge pressure support to the library.

## New features

- **Gauge pressure**
  ([#196](https://github.com/petrobras/ccp/pull/196)) — the units `barg`,
  `psig`, `kPag` and `MPag` are always available for input and output. ccp
  objects hold absolute pressures only:

  ```python
  s = ccp.State(p=Q_(10, "barg"), T=Q_(300, "degK"), fluid={"CO2": 1})
  s.p("bar")  # 11.01325 bar
  s.p("barg")  # 10 barg
  ```

  The gauge units are relative to `ccp.config.AMBIENT_PRESSURE`, 1 atm by
  default, which is changed with `ccp.set_ambient_pressure` or, for a block of
  code, with `ccp.ambient_pressure`:

  ```python
  with ccp.ambient_pressure(Q_(0.9, "bar")):
      s = ccp.State(p=Q_(10, "barg"), T=Q_(300, "degK"), fluid={"CO2": 1})
  ```

  `ccp.units.gauge_to_absolute` and `ccp.units.absolute_to_gauge` work with any
  pressure unit (e.g. kgf/cm²) and an explicit ambient pressure. A gauge
  quantity is converted with the ambient pressure in effect at that moment; see
  {ref}`gauge_pressure` for this and the other limits.

- **Gauge data in `Evaluation`**
  ([#196](https://github.com/petrobras/ccp/pull/196)) — `data_units` accepts
  gauge units for the pressures. The ambient pressure is given by the new
  `ambient_pressure` argument and saved with the evaluation, and the data is
  filtered by the absolute pressures.

- **Gauge units in the apps**
  ([#196](https://github.com/petrobras/ccp/pull/196)) — `psig`, `kPag` and
  `MPag` were added to the pressure units of the web and Streamlit apps. The
  ambient pressure of one session no longer changes the others.

## Changes

- **pint >= 0.24.4** is required
  ([#196](https://github.com/petrobras/ccp/pull/196)).

## Bug fixes

- **Gauge values in worker processes**
  ([#196](https://github.com/petrobras/ccp/pull/196)) — discharge pressure
  curves and `Evaluation` data in gauge units are converted to absolute before
  being sent to the worker processes, which do not have the ambient pressure of
  the main process.

- **Gauge units in pressure differences**
  ([#196](https://github.com/petrobras/ccp/pull/196)) — a `delta_p` in a gauge
  unit had the ambient pressure added to it. It now raises an error, and the
  apps no longer offer gauge units for pressure differences and for the ambient
  pressure.
