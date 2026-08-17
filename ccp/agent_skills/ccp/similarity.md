# Similarity and ASME PTC 10 Limits

Source: `ccp/similarity.py`, `ccp/point.py`

When a point is converted to another suction condition (see the conversion recipe), ASME PTC 10 defines how far the flow coefficient, volume ratio, Mach and Reynolds numbers may deviate for the test still to represent the specified operation.

## Quick check between two points

```python
import ccp

imp = ccp.impeller_example()
p_sp = imp.points[0]          # specified (reference) point
p_t = imp.points[1]           # test point

print(ccp.check_similarity(p_sp, p_t))
```

`check_similarity` returns a printable report with, line by line: flow coefficient ratio (limits 0.96–1.04), volume ratio ratio (limits 0.95–1.05), Mach number difference and Reynolds number ratio with their PTC 10 limits (which depend on the specified point's Mach and Reynolds values).

## Per-point similarity results

Converted points carry their deviation from the original point:

```python
Q_ = ccp.Q_

new_suc = ccp.State(p=Q_(5, "bar"), T=Q_(45, "degC"), fluid=p_sp.suc.fluid)
p_conv = ccp.Point.convert_from(p_sp, suc=new_suc)  # see the conversion recipe

p_conv.phi_ratio           # flow coefficient ratio (target: 0.96–1.04)
p_conv.volume_ratio_ratio  # volume ratio ratio (target: 0.95–1.05)
p_conv.mach_diff           # Mach difference vs. PTC 10 figure 3.2 limits
p_conv.reynolds_ratio      # Reynolds ratio vs. PTC 10 figure 3.3 limits
```

The PTC 10 ranges for a given point:

```python
p_conv.mach_limits()       # {"lower": ..., "upper": ..., "within_limits": bool}
p_conv.reynolds_limits()
```

## Plots and tables

```python
fig = p_conv.plot_mach()         # point and allowable Mach envelope
fig = p_conv.plot_reynolds()     # point and allowable Reynolds envelope
fig = p_conv.plot_similarity()   # combined view with table
fig = p_conv.similarity_table()  # plotly table with the values and limits
```

On impeller plots, `similarity=True` marks points that fall outside the limits:

```python
imp_conv = ccp.Impeller.convert_from(imp, suc=new_suc, speed="same")
imp_conv.head_plot(similarity=True)
```
