# Importing Curves from Charts (Engauge)

Source: `docs/user_guide/engauge.md`, `docs/user_guide/evaluation_tutorial.ipynb`, `ccp/impeller.py`

Performance maps from datasheets are usually pictures. Digitize them with [Engauge Digitizer](https://markummitchell.github.io/engauge-digitizer/) and load the exported CSV files with `Impeller.load_from_engauge_csv`.

## CSV files expected

For a `curve_name` of `"sec1"`, place in `curve_path`:

- `sec1-head.csv` — head vs. flow, one curve per speed
- `sec1-eff.csv` — efficiency vs. flow

Optionally also `sec1-power.csv`, `sec1-power_shaft.csv`, `sec1-pressure_ratio.csv`, `sec1-disch_T.csv`, `sec1-disch_p.csv`.

In Engauge, name each digitized curve with its speed value (e.g. `10322` for 10322 RPM; for shaft power curves, `10322, 82` also records power losses of 82 in `power_losses_units`) and export with "Raw X's and Y's, one curve on each line".

## Load

```python
import ccp
from pathlib import Path

Q_ = ccp.Q_

data_dir = Path(ccp.__file__).parent / "tests/data"

suc = ccp.State(
    p=Q_(4.08, "bar"),
    T=Q_(33.6, "degC"),
    fluid={"methane": 58.976, "co2": 36.605, "ethane": 3.099,
           "propane": 0.6, "n2": 0.55, "n-butane": 0.08, "i-butane": 0.05,
           "n-pentane": 0.01, "i-pentane": 0.01, "h2s": 0.02},
)

imp = ccp.Impeller.load_from_engauge_csv(
    suc=suc,
    curve_name="lp-sec1-caso-a",
    curve_path=data_dir,
    b=Q_(5.7, "mm"),          # impeller width
    D=Q_(550, "mm"),          # impeller diameter
    flow_units="m³/h",        # units used when digitizing
    head_units="kJ/kg",
    speed_units="RPM",
    number_of_points=7,       # points interpolated per curve
)
```

Key arguments:

- `flow_units`, `head_units`, `eff_units`, `power_units`, `speed_units`, ...: the units of the axes as digitized. If head was in meters, use `head_units="m*g0"`.
- `flow_units_head`, `flow_units_eff`, ...: per-curve flow units when the charts use different flow axes.
- `number_of_points`: how many points to interpolate along each digitized curve.
- `b`, `D`: impeller width and diameter — required for meaningful `phi`/`psi`/Mach/Reynolds and for conversions.

The result is a normal `Impeller` — see the impellers recipe for plots and interpolation, and the conversion recipe to move it to other suction conditions.
