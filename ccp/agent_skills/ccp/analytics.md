# Evaluation analytics: KPIs, trends, reconciliation and fleets

Source: `ccp/evaluation.py`, `ccp/analytics/`

## KPI columns of an evaluation

Besides `delta_eff`, `delta_head`, `delta_power` and `delta_p_disch`, every calculated row of `Evaluation.df` has:

- `flow_dev`: flow-capacity deviation at equal head, % (`(Q - Q_exp(H)) / Q_exp(H)`, from the stable branch of the expected curve; NaN above the curve's peak head)
- `delta_Td`: measured minus expected discharge temperature, K
- `health_index`: `eff / expected_eff`
- `head_slope`: `d ln(head) / d ln(flow)` of the expected curve at the row's flow and speed; `eff_slope`: `d eff / d ln(flow)` (NaN beyond the curve's highest flow)
- `power_shaft`: gas power plus the curve's mechanical losses, W

With the driver power, the rows also get `power_coupling` (W) and `delta_power_balance` (driver power at the coupling minus `power_shaft`, % of `power_shaft`):

```python
df["power_driver"] = ...  # driver shaft power
evaluation = ccp.Evaluation(
    data=df,
    data_units={..., "power_driver": "kW"},
    transmission_efficiency=0.985,  # coupling and gearbox
    ...,
)
# or estimate it from motor measurements: driver=ccp.InductionMotor(...) and
# columns named driver_<argument of InductionMotor.estimate>, e.g.
# driver_input_power, driver_current, driver_voltage, driver_power_factor
```

The converted curve of each cluster uses the cluster's mean gas composition. Use `cluster_on_composition=True` to cluster on molar mass too, which gives rows with different gases their own curves.

## Trends, change points, time to threshold

```python
report = evaluation.trends()             # daily medians of the default KPIs
report = evaluation.trends(
    kpis=["delta_eff", "flow_dev"],
    freq="1D",                           # period of the medians
    thresholds={"delta_eff": -3.0},      # KPI units
    baseline_days=14,                    # relative to each cluster's first 14 days
)
report.to_frame()      # current, slope per 1000 h (with 95 % interval), change points, time to threshold (h)
t = report["delta_eff"]
t.change_points        # [{"time", "shift", "kind": "recovery" | "drop" | "shift"}]
t.segments             # [{"start", "end", "mean", "slope", "first", "last"}]
report.plot("delta_eff")
report.to_dict()       # JSON-ready
```

The change points come from PELT on a piecewise-linear model (`ccp.analytics.change_points`), so a ramp counts as degradation, not as a series of steps. The trend is the Theil-Sen slope of the last segment (`ccp.analytics.theil_sen`). Plant data are autocorrelated even as daily medians, so read the slope interval as optimistic.

## Data reconciliation of redundant tags

```python
from ccp.analytics import Reconciliation

rec = Reconciliation(
    sigmas={"ps_A": 0.02, "ps_B": 0.02, "flow_A": "1%", "flow_B": "1%", "flow_H": "1%"},
    redundancy={"ps": ["ps_A", "ps_B"]},                     # tags of one variable
    balances=[{"flow_H": 1, "flow_A": -1, "flow_B": -1}],   # sum(coef * x) = 0
)
result = rec.reconcile(df)   # one row per timestamp; NaN tags are left out of their row
result.variables             # reconciled variables ("ps", "flow_A", ...)
result.global_test           # statistic, dof, p_value per row
result.gross_errors          # measurements removed by serial elimination (never one of two tied tags)
result.biases                # rolling median of the adjustments (persistent bias)
result.summary()
```

## Fleet of compressors of one design (needs `pip install ccp-performance[bayes]`)

A hierarchical Bayesian model fitted with PyMC. It separates the design-level deviation from the vendor curve, each unit's as-built deviation (from manufacturing scatter, pinned by its shop test), site and installation offsets, instrument biases and each unit's health over time. The health is a degradation rate plus a Student-t random walk that follows washes, plus a transient disturbance per period. Rows near choke (`max_head_slope=1.5`) are left out.

```python
from ccp.analytics.fleet import Fleet, FleetUnit, FleetPriors

fleet = Fleet(
    [
        FleetUnit("A", evaluation=evaluation_a, site="Site 1", shop=straight_through_a),
        FleetUnit("B", evaluation=evaluation_b, site="Site 1", shop=straight_through_b),
        FleetUnit("C", evaluation=evaluation_c, site="Site 2"),
    ],
    priors=FleetPriors(tau_unit_eff=0.015),  # manufacturing scatter of efficiency
)
fleet.fit(draws=1000, tune=1000, chains=4, random_seed=1)
fleet.diagnostics()          # rank-normalised max_rhat (< 1.01, health included), min_ess, divergences (0); warns otherwise
fleet.summary()              # per unit, % (points): asbuilt_*, current_*, rate_* per 1000 h, p_worst_eff, ...
fleet.ranking()              # probability of each rank (1 = worst current efficiency)
fleet.events()               # steps of the health (washes, sudden losses)
fleet.time_to_threshold(threshold=-0.03)
fleet.plot_units(); fleet.plot_health("eff")
fleet.save("fleet.zip"); Fleet.load("fleet.zip")
```

`shop` is a `StraightThrough`, whose `points_flange_sp` are used, or a list of points at specified conditions. Evaluations must be calculated with a ccp version that has the KPI columns. Without driver power, a flow-meter bias and a flow-capacity deviation look the same, so `asbuilt_flow` then includes the meter bias. For a synthetic fleet with known truth, use `ccp.analytics.fleet.simulate_fleet()` and `Fleet.from_observations(field, shop)`.
