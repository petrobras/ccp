# Evaluation analytics and fleets

An {py:class}`ccp.Evaluation` compares plant data with the design curves converted to the operating suction. This page covers what comes after the deviations: health indicators, trends and change points, the reconciliation of redundant tags, and a statistical model for a fleet of compressors of one design.

## Indicators per row

Each calculated row of `evaluation.df` has, besides `delta_eff`, `delta_head`, `delta_power` and `delta_p_disch`:

| column | meaning |
|---|---|
| `flow_dev` | flow-capacity deviation at equal head, %: the measured flow against the flow of the expected curve at the measured head (stable branch) |
| `delta_Td` | measured minus expected discharge temperature, K |
| `health_index` | measured over expected polytropic efficiency |
| `head_slope`, `eff_slope` | slopes of the expected curve, `d ln(head)/d ln(flow)` and `d eff/d ln(flow)`, at the row's flow and speed |
| `power_shaft` | gas power plus the curve's mechanical losses, W |
| `power_coupling`, `delta_power_balance` | with the driver power: driver power at the coupling, and its difference from `power_shaft` in % |

The power balance compares two measurements of the same energy: the driver power and the gas power (mass flow times the enthalpy rise). A real loss of efficiency raises both, so the balance stays put. A bias of the discharge temperature or of the flow meter moves only the gas power. A drifting balance therefore points to an instrument, not to the machine.

Pass the driver power as a `power_driver` column (with its unit in `data_units`), or give `driver=ccp.InductionMotor(...)` and the motor measurements as `driver_*` columns. `transmission_efficiency` accounts for the coupling and the gearbox.

With `fluid_*` columns, the converted curve of each cluster uses the mean composition of the cluster's rows (earlier versions used the composition of its first row, so results with a varying composition change slightly). `cluster_on_composition=True` adds the molar mass to the clustering features, which gives rows with different gases their own curves.

## Trends and change points

```python
report = evaluation.trends(thresholds={"delta_eff": -3.0}, baseline_days=14)
report.to_frame()
report.plot("delta_eff")
```

Each KPI is reduced to daily medians. Change points are found with PELT on a piecewise-linear model: each segment is a line, so slow fouling is a slope and a wash or a damage is a step. The noise scale comes from the median absolute first difference, which neither steps nor slopes inflate. The trend is the Theil-Sen slope of the last segment, with its 95 % interval, and the time to threshold extrapolates that line; it is 0 when the KPI is already on the bad side of its threshold. With `baseline_days`, each KPI is taken relative to the median of the first days of each operating cluster, which removes the curve error of each operating region.

## Reconciliation of redundant tags

When a variable is measured by several tags, or tags are tied by a balance, {py:class}`ccp.Reconciliation` finds the values closest to the measurements (weighted least squares) that satisfy the balances, row by row. The adjustments give a global chi-square test, a measurement test per tag, the serial elimination of gross errors and the persistent bias of each tag (rolling median of its adjustments). Variables that the remaining measurements and balances do not fix are NaN. A gross error is removed only where its measurement test is the largest of the row; the tags of an equivalency set (the two tags of a dual transmitter, the tags of one balance) share the same test, so there nothing is removed, the row keeps failing the global test and the adjustment is split between them: three tags of a variable are needed to locate a biased one. A reading of 0 on a tag with a relative standard deviation (`"0.25%"`) is treated as missing. See Narasimhan and Jordache, *Data Reconciliation and Gross Error Detection* (2000).

## A fleet of compressors of one design

Compressors built to one design differ by manufacturing tolerances, installation, instruments and degradation. {py:class}`ccp.Fleet` pools the shop tests and the field data of every unit in one hierarchical Bayesian model fitted with PyMC (`pip install ccp-performance[bayes]`). Each unit is then judged against what is normal for its design:

- a unit with little data borrows strength from its siblings;
- a deviation shared by the whole fleet, such as an optimistic vendor curve or an equation-of-state bias, is attributed to the design, not to each unit;
- the spread between units is estimated, so a unit outside it stands out.

### Model

With $r_\psi = \ln(H/H_{exp})$ and $r_\eta = \eta - \eta_{exp}$ the residuals of a row against the expected curve, $s_\psi$ and $s_\eta$ the slopes of that curve, and unit $u$ at site $s(u)$:

$$
\theta_{u,k} \sim N(\mu_k, \tau_k), \quad k \in \{\text{flow}, \text{head}, \text{eff}\}
$$

$$
L_{u,f}(t) = \theta_{u,f} + \text{site}_{s(u),f} + \text{install}_{u,f} + h_{u,f}(t) + d_{u,f}(t)
$$

$$
r_\psi = L_{u,\text{head}}(t) - (\theta_{u,\text{flow}} + \beta^Q_u)\, s_\psi + k^T_\psi \beta^T_u + k^p_\psi \beta^p_u + \varepsilon
$$

$$
r_\eta = L_{u,\text{eff}}(t) - (\theta_{u,\text{flow}} + \beta^Q_u)\, s_\eta + k^T_\eta \beta^T_u + k^p_\eta \beta^p_u + \varepsilon
$$

$$
\ln(P_{driver}/P_{shaft}) = \beta^{drv}_u - w\,(\beta^Q_u + \beta^T_u/\Delta T) + \varepsilon
$$

- $\theta$ is the as-built deviation of the unit from the vendor curve, drawn from the design-level mean $\mu$ with the manufacturing scatter $\tau$. A shop test observes it directly: $r_\psi = \theta_{\text{head}} - \theta_{\text{flow}} s_\psi$, and likewise for efficiency.
- The health $h$ is zero on average over the unit's first 14 days of data. It follows a degradation rate (pooled over the fleet) plus a Student-t random walk, whose heavy tail lets washes and sudden losses appear as steps. $d$ is a transient disturbance of one period (process, ambient) that is not carried over, so a disturbed day is not read as two opposite steps.
- $\beta^T$ (temperature rise, K), $\beta^p$ (pressure ratio), $\beta^Q$ (flow meter) and $\beta^{drv}$ (driver power) are instrument biases. Their sensitivities $k$ are the ideal-gas ones at each row. A 1 K error on the discharge temperature moves the polytropic efficiency by about 3 points at a pressure ratio of 1.3 and by about 1 point at 2.0, so separating instruments from machines matters most on low-ratio machines.
- Without the driver power, a flow-meter bias and a flow-capacity deviation have the same signature, and only their sum is learned.
- Rows have Student-t errors plus a model-error floor (0.2 % by default). The model is linear in the deviations, a first-order approximation valid for deviations of a few percent away from choke. Rows where the curve is steeper than `max_head_slope` (1.5 in `d ln(head)/d ln(flow)`) are left out: there a 1 or 2 % flow shift changes the head far from linearly. A unit left with no field rows is kept for its shop test, with a warning; its current level, rate, ranking and time to threshold are NaN.

### Use

```python
from ccp.analytics.fleet import Fleet, FleetUnit

fleet = Fleet([
    FleetUnit("A", evaluation=evaluation_a, site="Site 1", shop=straight_through_a),
    FleetUnit("B", evaluation=evaluation_b, site="Site 1", shop=straight_through_b),
    FleetUnit("C", evaluation=evaluation_c, site="Site 2", shop=straight_through_c),
])
fleet.fit(random_seed=1)        # 4 chains of 1000 draws
fleet.diagnostics()             # check max_rhat < 1.01 and divergences == 0 (warns otherwise)
fleet.summary()                 # as-built and current deviations, rates, P(worst), ...
fleet.ranking()
fleet.events()                  # washes and sudden losses
fleet.time_to_threshold(threshold=-0.03)
fleet.plot_units()
fleet.plot_health("eff")
```

`ccp.analytics.fleet.simulate_fleet()` builds a synthetic fleet with known truth. Use it with `Fleet.from_observations(field, shop)` to see what the model recovers with your number of units and your amount of data before trusting it on plant data.

The prior scales are in {py:class}`ccp.FleetPriors`. The defaults follow the scatter reported between identical units in the field, about ±2 % head and 1.5 % efficiency (Tavares, Sivadas and Gatewood, 2nd Middle East Turbomachinery Symposium, 2013). With 2 to 6 units, the data say little about the scatter itself, so its prior matters (Gelman, *Bayesian Analysis* 1(3), 2006). Set it from your own shop-test history when you have one.
