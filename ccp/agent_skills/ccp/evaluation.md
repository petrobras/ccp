# Evaluating Operational Data

Source: `docs/user_guide/evaluation_tutorial.ipynb`, `ccp/evaluation.py`

`Evaluation` compares plant operational data (a pandas DataFrame of pressures, temperatures, flows and speeds over time) against reference performance curves, computing for each sample the expected performance and the deviation from it.

## Run an evaluation

```python
import pandas as pd
from pathlib import Path
import ccp

Q_ = ccp.Q_
data_path = Path(ccp.__file__).parent / "tests/data"

df = pd.read_parquet(data_path / "data.parquet")
# df columns: ps, Ts, pd, Td, flow_v (or delta_p + p_downstream), speed

operation_fluid = {"methane": 44.04, "co2": 51.55, "ethane": 3.18,
                   "propane": 0.66, "n-butane": 0.15, "i-butane": 0.05,
                   "n-pentane": 0.03, "i-pentane": 0.02, "n2": 0.25, "h2s": 0.06}

# Reference impeller (e.g. loaded from digitized curves — see the engauge recipe)
test_fluid = {"methane": 58.976, "co2": 36.605, "ethane": 3.099,
              "propane": 0.6, "n-butane": 0.08, "i-butane": 0.05,
              "n-pentane": 0.01, "i-pentane": 0.01, "n2": 0.55, "h2s": 0.02}
suc_a = ccp.State(p=Q_(4, "bar"), T=Q_(40, "degC"), fluid=test_fluid)
imp_a = ccp.Impeller.load_from_engauge_csv(
    suc=suc_a, curve_name="eval-lp-sec1-caso-a", curve_path=data_path,
    flow_units="m³/h", head_units="kJ/kg", number_of_points=4,
)

evaluation = ccp.Evaluation(
    data=df,
    operation_fluid=operation_fluid,
    data_units={
        "ps": "bar", "Ts": "degC", "pd": "bar", "Td": "degC",
        "flow_v": "m³/s", "speed": "RPM",
    },
    impellers=[imp_a],     # reference curves; converted to each operating suction
    n_clusters=2,          # cluster operating conditions to reuse conversions
)
```

## Results

`evaluation.df` is the input DataFrame plus computed columns:

- `eff`, `head`, `power`, `p_disch`: actual values calculated from the data (SI units, except `p_disch` in bar)
- `expected_eff`, `expected_head`, `expected_power`, `expected_p_disch`: from the reference curves converted to the sample's suction condition
- `delta_eff`: `(eff - expected_eff) * 100` — difference in efficiency percentage points (positive = better than expected)
- `delta_head`, `delta_power`, `delta_p_disch`: relative deviation from the expected value in %

```python
evaluation.df["delta_eff"].mean()
```

## Flow from orifice delta-p

If the data has `delta_p` (and optionally `p_downstream`) instead of `flow_v`, pass the orifice geometry and ccp computes the flow internally:

```python
df_delta_p = pd.read_parquet(data_path / "data_delta_p.parquet")

evaluation = ccp.Evaluation(
    data=df_delta_p,
    operation_fluid=operation_fluid,
    data_units={"ps": "bar", "Ts": "degC", "pd": "bar", "Td": "degC",
                "delta_p": "mmH2O", "p_downstream": "bar", "speed": "RPM"},
    impellers=[imp_a],
    D=Q_(0.590550, "m"),   # pipe diameter
    d=Q_(0.366130, "m"),   # orifice diameter
    tappings="flange",
    n_clusters=2,
)
```

## Save / load

```python
evaluation.save("run1.ccp_eval")
loaded = ccp.Evaluation.load("run1.ccp_eval")
```

## Manual control

`calculate_points=False` creates the object without processing; then call `evaluation.calculate_points(df, drop_invalid_values=True)` on any subset.
