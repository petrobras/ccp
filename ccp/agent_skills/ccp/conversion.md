# Converting to New Suction Conditions

Source: `docs/user_guide/tutorial.ipynb`, `ccp/impeller.py`, `ccp/point.py`

Performance maps are measured (or specified) at one suction condition. To predict performance with a different gas, pressure or temperature, convert the map using similitude: for each point, volume ratio is kept constant and a new speed and discharge state are calculated.

## Convert an impeller

```python
import ccp

Q_ = ccp.Q_

imp = ccp.impeller_example()

new_fluid = {"co2": 0.7, "n2": 0.3}
new_suc = ccp.State(p=Q_(30, "bar"), T=Q_(40, "degC"), fluid=new_fluid)

imp_conv = ccp.Impeller.convert_from(imp, suc=new_suc)
```

- The converted impeller has new speeds computed from similarity. To keep the original speed values instead: `ccp.Impeller.convert_from(imp, suc=new_suc, speed="same")`.
- A **list** of impellers can be passed; the one with suction speed of sound closest to `new_suc` is used.
- `method="gp_surrogate"` fits a Gaussian-process surrogate `psi, eff = f(phi, M_tip)` over the points of all supplied maps instead of similarity rescaling — useful with several measured maps or dense/supercritical suctions (requires scikit-learn).

The converted impeller has all the usual methods:

```python
imp_conv.head_plot(similarity=True)   # shade points outside PTC 10 similarity limits
imp_conv.disch.p_plot(speed_units="RPM")
imp.head_compare(imp_conv)            # original vs converted on one figure
```

## Convert a single point

```python
p0 = imp.points[0]
p_conv = ccp.Point.convert_from(p0, suc=new_suc, find="speed")
```

- `find="speed"` (default): keep volume ratio, solve for the new speed.
- `find="volume_ratio"`: impose `speed=...`, solve for the new volume ratio.
- `reynolds_correction=True` applies the ASME PTC 10 (2022) Reynolds correction to efficiency, head and flow coefficients during conversion (`"ptc1997"` selects the 1997 correction).

The converted point records how far it moved from the original: `p_conv.phi_ratio`, `p_conv.psi_ratio`, `p_conv.volume_ratio_ratio`, `p_conv.reynolds_ratio`, `p_conv.mach_diff` — see the similarity recipe for the acceptable limits.
