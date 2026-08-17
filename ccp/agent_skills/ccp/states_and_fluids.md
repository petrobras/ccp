# Thermodynamic States and Fluids

Source: `docs/user_guide/tutorial.ipynb`, `ccp/state.py`, `ccp/config/fluids.py`

## Create a State

```python
import ccp

Q_ = ccp.Q_

fluid = {
    "CarbonDioxide": 0.79585,
    "Nitrogen": 0.16751,
    "Oxygen": 0.02903,
}

suc = ccp.State(fluid=fluid, p=Q_(3, "bar"), T=300)
```

- `fluid` (dict, required keyword): component name → mole fraction. Fractions are normalized automatically, so percentages (summing to 100) work as well.
- Any **two** of `p`, `T`, `h`, `s`, `rho` define the state (e.g. `ccp.State(fluid=fluid, h=..., s=...)` for an isentropic discharge).
- Plain floats are SI: `T=300` means 300 K, `p=101325` means Pa. Use `Q_` for anything else: `T=Q_(40, "degC")`, `p=Q_(30, "bar")`.
- `EOS` (str, optional): `"REFPROP"` (default when available), `"HEOS"` (CoolProp), `"PR"` or `"SRK"`. The global default is `ccp.config.EOS`; ccp automatically falls back to `"HEOS"` when REFPROP is not installed.
- `phase` (str, optional): skip the phase flash by declaring `"gas"`, `"liquid"`, `"supercritical"`, etc.

## Fluid names

Names are case-insensitive and common aliases are accepted: `"co2"`, `"n2"`, `"o2"`, `"h2s"`, `"methane"`, `"propane"`, `"i-butane"`, `"n-pentane"`, ... The full table is in `ccp.fluid_list` (maps CoolProp names to their accepted aliases). Mixing aliases that resolve to the same component (e.g. `"butane"` and `"n-butane"`) raises an error.

## Properties

All properties are methods that return pint quantities in SI; pass a unit string to convert:

```python
suc.T()            # Quantity in kelvin
suc.p("bar")       # Quantity in bar
suc.rho()          # kg/m³
suc.h()            # J/kg
suc.s()            # J/(kg·K)
suc.z()            # compressibility factor (dimensionless)
suc.molar_mass("g/mol")
suc.cp()           # J/(kg·K)
suc.cv()
suc.speed_sound()  # m/s
suc.viscosity()    # Pa·s
suc.kinematic_viscosity()
suc.v()            # specific volume m³/kg
suc.p_critical(), suc.T_critical()
```

Take the magnitude with `.m` or `.magnitude`: `suc.rho().m`.

## Update a state in place

```python
suc.update(p=Q_(5, "bar"), T=Q_(50, "degC"))
```

## Phase envelope

```python
fig = suc.plot_envelope()   # plotly Figure with the P-T envelope
fig = suc.plot_point(fig=fig)  # mark the state point on the envelope
```
