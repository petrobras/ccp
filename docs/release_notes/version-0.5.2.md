# Version 0.5.2

Version 0.5.2 adds a cone (V-cone) differential pressure flow meter, following
ISO 5167-5, and fixes the conversion of Hz to rotational speed.

## New features

- **Cone flow meter, `ccp.FlowCone`**
  ([#193](https://github.com/petrobras/ccp/pull/193)) — calculates mass and
  volume flow from the differential pressure of a cone meter, with an API
  mirroring `FlowOrifice`:

  ```python
  fc = ccp.FlowCone(state, delta_p=Q_(0.1, "bar"), D=Q_(250, "mm"), dc=Q_(180, "mm"))
  fc.flow_m, fc.flow_v
  ```

  The geometry is given by the pipe internal diameter `D` and either the cone
  diameter `dc` or the equivalent diameter `d = beta * D`. The discharge
  coefficient defaults to the ISO 5167-5 value of an uncalibrated meter
  (C = 0.82, 5 % uncertainty) and can be replaced by a calibrated value, a
  function `C(Re)` or a calibration table `(Re, C)`. A
  `ccp.fc.FlowMeterWarning` is emitted when D, beta or the Reynolds number is
  outside the limits of the uncalibrated C, when the Reynolds number is outside
  a calibration table, and when p2/p1 is below 0.75, the limit of the
  expansibility equation.

- **Cone meters in `Evaluation`**
  ([#193](https://github.com/petrobras/ccp/pull/193)) — `delta_p` data from a
  cone meter is converted to flow with `flow_meter="cone"` and `D`, `d` or
  `dc`, and optionally `C`. Each exceeded ISO 5167-5 limit is reported once,
  with the number of rows.

## Bug fixes

- **Hz is one revolution per second**
  ([#190](https://github.com/petrobras/ccp/pull/190)) — pint defines hertz as
  1/s and treats radians as dimensionless, so a speed of 1 Hz converted to
  1 rad/s (9.549 rpm) instead of 60 rpm. Speeds given in Hz are now converted
  correctly, which changes the results of any calculation that passed a speed
  in Hz.

- **`Evaluation` meter checks**
  ([#193](https://github.com/petrobras/ccp/pull/193)) — the `tappings` default
  is now `"flange"`, as documented; the previous default, `None`, was rejected
  by `FlowOrifice` and every row of a `delta_p` evaluation without explicit
  tappings was marked invalid. An invalid flow meter definition, or `delta_p`
  data without the meter geometry, now raises when the `Evaluation` is created
  instead of invalidating every row.
