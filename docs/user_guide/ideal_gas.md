(ideal_gas)=
# Ideal gas model

```{warning}
This model exists only to replicate studies, vendor calculations and legacy
spreadsheets that assume ideal gas behavior. REFPROP (or another real-gas EOS)
provides much better and more accurate property models and should be preferred
for real analyses.
```

## Selecting the model

```{code-block} python
import ccp

Q_ = ccp.Q_
fluid = {"Methane": 0.9, "Ethane": 0.06, "CarbonDioxide": 0.04}

# Z = 1, cp(T) from the ideal-gas part of each component
suc = ccp.State(p=Q_(50, "bar"), T=Q_(40, "degC"), fluid=fluid, EOS="ideal")

# Z = 1, constant k
suc = ccp.State(p=Q_(50, "bar"), T=Q_(40, "degC"), fluid=fluid, EOS="ideal:k=1.3")

# Default for the states created from now on
ccp.config.EOS = "ideal"
```

A state's EOS is fixed when the state is built. The states derived from it
(discharge states, conversions, copies, worker processes, saved points) follow
it, and changing `ccp.config.EOS` only affects new states. A `Point`, `Curve`,
`Impeller` or `Evaluation` cannot combine an ideal gas with another model, and an
`Evaluation` of ideal gas impellers also evaluates its operating data as ideal gas.
A real map can still be converted to an ideal gas suction, and the reverse.

Creating an ideal gas state emits a `ccp.state.IdealGasWarning`, normally only once
with the default warning filters. To silence it:

```{code-block} python
import warnings

warnings.filterwarnings("ignore", category=ccp.state.IdealGasWarning)
```

## Model

With $x_i$ the mole fractions, $M = \sum x_i M_i$, $R = R_u / M$ and
$R_u$ = 8.31446261815324 J/(mol K) for every fluid:

$$\rho = \frac{p}{R T}, \qquad Z = 1, \qquad c_v = c_p - R, \qquad k = \frac{c_p}{c_v}$$

`EOS="ideal"`
: The ideal-gas part of each pure component, from CoolProp (HEOS), with mole
  fraction weighted molar properties. The enthalpy and entropy use the reference
  state of the source fluid. REFPROP is only used for the fluids HEOS does not
  have (`13Butadiene` and `1-Pentene`), so the thermodynamic properties do not
  depend on REFPROP being installed.

  $$c_p = \frac{1}{M}\sum x_i c^0_{p,i}(T), \qquad h = \frac{1}{M}\sum x_i h^0_i(T)$$

  $$s = \frac{1}{M}\left(\sum x_i s^0_i(T, p_0) - R_u \sum x_i \ln x_i\right) - R \ln\frac{p}{p_0}$$

`EOS="ideal:k=<k>"`
: Constant $k > 1$. The composition only supplies $M$. $h = s = 0$ at 25 degC and
  1 atm.

  $$c_p = \frac{k R}{k - 1}, \qquad h = c_p (T - T_0), \qquad s = c_p \ln\frac{T}{T_0} - R \ln\frac{p}{p_0}$$

Only enthalpy and entropy differences are meaningful for comparisons between
models with different reference states.

## Reproducing a study

Constant cp instead of k
: Convert it with the gas constant of the state:

  ```{code-block} python
  s = ccp.State(p=Q_(50, "bar"), T=Q_(40, "degC"), fluid=fluid, EOS="ideal")
  cp = Q_(2200, "J/(kg K)")
  R = s.gas_constant() / s.molar_mass()
  k = (cp / (cp - R)).to("dimensionless").m
  suc = ccp.State(p=s.p(), T=s.T(), fluid=fluid, EOS=f"ideal:k={k}")
  ```

The study gives k
: Pass the same value, `EOS="ideal:k=1.27"`, even if ccp would calculate another
  one. Otherwise the results will not match the study.

The study gives only the composition, with k(T) varying along the compression
: Use `EOS="ideal"`.

The study gives only the composition, with one k for the whole compression
: Calculate k once at the suction condition and pass the number:

  ```{code-block} python
  s = ccp.State(p=Q_(50, "bar"), T=Q_(40, "degC"), fluid=fluid, EOS="ideal")
  k = s.kv().m
  suc = ccp.State(p=s.p(), T=s.T(), fluid=fluid, EOS=f"ideal:k={k}")
  ```

  The states derived from `suc` keep this k. There is no option to calculate it
  inside the EOS string, because a discharge state would then calculate it again
  at its own temperature.

Which k to take from a real-gas EOS
: The ideal-gas k depends only on composition and temperature, and is the one
  consistent with $Z = 1$. At 1 Pa and 300 K, REFPROP's $c_p/c_v$ agrees with
  `EOS="ideal"` to 2e-6 for the mixture above. At higher pressure, a real-gas state
  gives different values, and `kv()` is not $c_p/c_v$ for a real gas. At 40 degC:

  | Pressure | `EOS="ideal"`, `kv()` = $c_p/c_v$ | `EOS="REFPROP"`, $c_p/c_v$ | `EOS="REFPROP"`, `kv()` |
  |---|---|---|---|
  | 5 bar | 1.286 | 1.298 | 1.287 |
  | 50 bar | 1.286 | 1.435 | 1.326 |
  | 150 bar | 1.286 | 1.802 | 1.706 |

  Combining a real-gas k with $Z = 1$ is not thermodynamically consistent. Do it only
  if the study being replicated did.

A study that only gives the molecular weight
: With constant k the composition only supplies $M$, so blend any two components
  to match it.

Rounded gas constants
: Sheets using R = 8.314 J/(mol K), or 287 J/(kg K) with `fluid={"Air": 1}`, only
  agree with ccp to about 6e-5 and 2e-4. For other air compositions, 287 J/(kg K)
  differs more because the molar mass differs.

## Polytropic methods and the closed forms

With $r = p_2/p_1$, $\sigma = (k-1)/(k\eta)$ and a constant k, the polytropic
compression is

$$\frac{T_2}{T_1} = r^\sigma, \qquad H = \frac{R T_1}{\sigma}\left(r^\sigma - 1\right) = \eta c_p (T_2 - T_1)$$

Not every polytropic method reproduces it. Deviation in head for given discharge
pressure and efficiency, with a suction at 300 K:

| Method | Constant k (k = 1.4, r = 4, η = 0.8) | cp(T) (methane, r = 4, η = 0.8) |
|---|---|---|
| `huntington` | exact | exact |
| `schultz` | exact | -2.4e-3 |
| `mallen_saville` | exact | +1.6e-3 |
| `sandberg_colby` (default), `sandberg_colby_f` | -6.2e-3 | -1.8e-3 |
| `sandberg_colby_multistep` | -1.5e-5 | -7.6e-6 |

Use `polytropic_method="huntington"` to reproduce a closed-form result. The default
method is deliberately not switched for ideal gas states, so a real versus ideal
comparison changes only the gas model.

The `polytropic_method` argument applies only to the point it is given to. Points
derived from it (`Impeller.convert_from`, `Impeller.point`, `Impeller.curve`, and
`Point.convert_from` without the argument) use `ccp.config.POLYTROPIC_METHOD`, so set
that as well when working with maps or conversions.

For `sandberg_colby` with given discharge state and constant k, with
$x = \ln(T_2/T_1)$ and $\eta = \frac{k-1}{k}\ln r / x$ the true path efficiency:

$$\frac{H_{SC}}{H} - 1 = -\left[\frac{x}{2}\coth\frac{x}{2} - 1\right]\frac{1-\eta}{\eta}$$

## Quantifying the deviation from a real gas

This example needs REFPROP. Without it, use `EOS="HEOS"` for the real gas.

```{code-block} python
kwargs = dict(
    disch_p=Q_(150, "bar"),
    eff=0.8,
    flow_m=Q_(10, "kg/s"),
    speed=Q_(9000, "RPM"),
    b=0.01,
    D=0.3,
    polytropic_method="huntington",
)
real = ccp.Point(
    suc=ccp.State(p=Q_(50, "bar"), T=Q_(40, "degC"), fluid=fluid, EOS="REFPROP"),
    **kwargs,
)
ideal = ccp.Point(
    suc=ccp.State(p=Q_(50, "bar"), T=Q_(40, "degC"), fluid=fluid, EOS="ideal"),
    **kwargs,
)
real.head / ideal.head - 1
```

## Limits

- `p_critical`, `T_critical`, `conductivity`, `plot_envelope`,
  `get_coolprop_state` and the raw CoolProp methods (`hmass`,
  `first_partial_deriv`, ...) raise `NotImplementedError`. Use the `ccp.State`
  properties (`h()`, `cp()`, `kv()`, ...).
- `h` depends on T only, so the pair (T, h) does not define a state and raises
  `ValueError`.
- The only phase is `"gas"`. Conditions where a real fluid would condense are still
  a gas.
- The viscosity is a dilute-gas estimate, independent of pressure (pure-component
  values at 1 Pa mixed with the Herning-Zipperer rule), used for the Reynolds
  number. HEOS has a viscosity model for only some fluids, and REFPROP supplies the
  others when it is installed (for example CarbonMonoxide, Ethylene, the butenes,
  Neopentane, Isohexane, SulfurDioxide). Without a model, the viscosity and the
  Reynolds number are NaN, with a warning, and conversions with
  `reynolds_correction` fail to converge.
- `13Butadiene` and `1-Pentene` need REFPROP.
- The ideal-gas heat capacity correlations are only refused when $c_p \le R$: stay
  within their ordinary temperature range.
- `ccp.config.POLYTROPIC_METHOD` set under the main guard does not reach the pool
  workers, which matters when loading maps and for conversions with the default
  speed. Set it at the top level of the script or use
  `ccp.config.PARALLEL = False`.
