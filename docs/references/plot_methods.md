# Impeller plot methods

An impeller object has several plot methods available.
The documentation for these methods is as follows:

```{code-block} python3
"""Plot parameter versus volumetric flow.

Parameters
----------
flow_v : pint.Quantity, float
    Volumetric flow (m³/s) for a specific point in the plot.
speed : pint.Quantity, float
    Speed (rad/s) for a specific point in the plot.
flow_v_units : str, optional
    Flow units used for the plot. Default is m³/s.
{attr}_units : str, optional
    Units for the parameter being plotted (e.g. for a head plot we could use
    head_units='J/kg' or head_units='J/g'. Default is SI.
speed_units : str, optional
    Speed units for the plot. Default is 'rad/s'.

Returns
-------
fig : plotly.Figure
    Plotly figure that can be customized.
"""
```        

Here are some examples of how we can create some plots:

```{code-block} python3
import ccp
imp = ccp.impeller_example()
fig = imp.plot_head(
   flow_v=5.5,
   speed=900,
   flow_v_units='m³/h',
   head_units='j/kg',
   speed_units='RPM'
)
 ```

We can also use pint Quantities for the `flow_v` and `speed`:

```{code-block} python3
fig = imp.plot_head(
   flow_v=Q_(5.5, 'm³/s'),
   speed=Q_(8000, 'RPM'),
   flow_v_units='m³/h',
   head_units='j/kg',
   speed_units='RPM'
)
 ```

It is also possible to plot discharge state parameters such as `p`, `T`, `h` etc.

```{code-block} python3
fig = imp.disch.plot_T(
   flow_v=Q_(5.5, 'm³/s'),
   speed=Q_(8000, 'RPM'),
   flow_v_units='m³/h',
   T_units='degC',
   speed_units='RPM'
)
 ```
