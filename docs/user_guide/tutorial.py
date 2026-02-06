import marimo

__generated_with = "0.19.8"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    (tutorial)=
    # Tutorial
    """)
    return


@app.cell
def _():
    import ccp

    Q_ = ccp.Q_
    return Q_, ccp


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `ccp` uses pint to handle units. Q_ is a pint quantity.

    Here lets define a suction pressure `ps` and a suction temperature `Ts`.

    For the suction pressure we are going to use pint$.$
    """)
    return


@app.cell
def _(Q_):
    ps = Q_(3, "bar")
    Ts = 300
    return Ts, ps


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The pint objects hold the magnitude and units for a variable and can be used for unit conversion:
    """)
    return


@app.cell
def _(ps):
    print(
        f"ps: {ps}\n"
        f"ps magnitude: {ps.magnitude}\n"
        f"ps units: {ps.units}\n"
        f"convert to atm: {ps.to('atm')}\n"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The fluid composition is defined as a dictionary:
    """)
    return


@app.cell
def _():
    fluid = {
        "CarbonDioxide": 0.79585,
        "Nitrogen": 0.16751,
        "Oxygen": 0.02903,
    }
    return (fluid,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    We can create the suction and discharge states using the `State` class:
    """)
    return


@app.cell
def _(Q_, Ts, ccp, fluid, ps):
    suc0 = ccp.State(fluid=fluid, p=ps, T=Ts)
    disch0 = ccp.State(fluid=fluid, p=Q_(7.255, "bar"), T=391.1)
    return disch0, suc0


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Notice that in the cell above we defined the states using pint quantities mixed with pure floats.

    The way that `ccp` works is by assuming that float are in the SI units system, so

    ```python
    disch0 = ccp.State(fluid=fluid, p=Q_(7.255, 'bar'), T=391.1)
    ```

    is the same as

    ```python
    disch0 = ccp.State(fluid=fluid, p=Q_(7.255, 'bar'), T=Q_(391.1, 'degK'))
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Create performance point(s):
    """)
    return


@app.cell
def _(Q_, ccp, disch0, suc0):
    point0 = ccp.Point(
        suc=suc0,
        disch=disch0,
        speed=Q_(7941, "RPM"),
        flow_m=Q_(34203.6, "kg/hr"),
        b=0.0285,
        D=0.365,
    )
    point1 = ccp.Point(
        suc=suc0,
        disch=disch0,
        speed=Q_(7941, "RPM"),
        flow_m=Q_(37203.6, "kg/hr"),
        b=0.0285,
        D=0.365,
    )
    return point0, point1


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Now we can create an impeller, which is basically a container for points.
    """)
    return


@app.cell
def _(ccp, point0, point1):
    imp = ccp.Impeller([point0, point1])
    return (imp,)


@app.cell
def _(imp):
    imp
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    To show other ccp features we are going to load an impeller from `csv` files created with the [Engauge Digitizer](https://markummitchell.github.io/engauge-digitizer/) application.
    For more information on how to use ccp with Engaguge Digitizer see {ref}`this How-to Guide <engauge>`
    """)
    return


@app.cell
def _(ccp):
    imp_1 = ccp.impeller.impeller_example()
    return (imp_1,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The impeller object stores all points in the `.points` attribute.

    It is also possible to get an specific point in the performance map using the `.point()` method:
    """)
    return


@app.cell
def _(imp_1):
    p = imp_1.point(flow_v=5.5, speed=900)
    p
    return (p,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    We can access the suction or discharge condition for this point with `p.suc` or `p.disch` and get some properties for this states:
    """)
    return


@app.cell
def _(p):
    p.disch.rho()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    We can also plot the phase envelope:
    """)
    return


@app.cell
def _(p):
    p.disch.plot_envelope()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    We can also plot performance parameters such as the polytropic head.
    In this case we can choose a flow and speed and the correspondent curve and point will also be plotted:
    """)
    return


@app.cell
def _(imp_1):
    _fig = imp_1.head_plot(flow_v=5.5, speed=900)
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    It is also possible to plot discharge parameters such as T (temperature), p (pressure), rho (specific mass) and so on:
    """)
    return


@app.cell
def _(imp_1):
    _fig = imp_1.disch.T_plot(flow_v=5.5, speed=900)
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    In these plots we can also choose the units used for plotting:
    """)
    return


@app.cell
def _(imp_1):
    _fig = imp_1.disch.rho_plot(
        flow_v=5.5, speed=900, flow_v_units="m³/h", speed_units="RPM", rho_units="g/cm³"
    )
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Notice that by default the units used in the `flow_v` and `speed` arguments are the SI units, but you can also provide pint quantities:
    """)
    return


@app.cell
def _(Q_, imp_1):
    _fig = imp_1.disch.rho_plot(
        flow_v=Q_(20000, "m³/h"),
        speed=Q_(8594, "RPM"),
        flow_v_units="m³/h",
        speed_units="RPM",
        rho_units="g/cm³",
    )
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Now we are going to convert the performance map from an impeller to a different suction condition:
    """)
    return


@app.cell
def _(Q_, ccp, imp_1):
    new_fluid = {"co2": 0.7, "n2": 0.3}
    new_suc = ccp.State(p=Q_(30, "bar"), T=Q_(40, "degC"), fluid=new_fluid)
    imp_conv = ccp.Impeller.convert_from(imp_1, suc=new_suc)
    return imp_conv, new_suc


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The conversion calculates new speeds based on similarity.

    The new impeller has the same attributes and methods as the original one:
    """)
    return


@app.cell
def _(imp_conv):
    imp_conv.disch.p_plot(speed_units="RPM")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    There is also an option to keep the same speeds as the original impeller during the conversion:
    """)
    return


@app.cell
def _(ccp, imp_1, new_suc):
    imp_conv_1 = ccp.Impeller.convert_from(imp_1, suc=new_suc, speed="same")
    return (imp_conv_1,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    We can also compare the curves from the original impeller with the converted one using the `_compare` methods:
    """)
    return


@app.cell
def _(imp_1, imp_conv_1):
    imp_1.head_compare(imp_conv_1)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    It is also possible to check if the converted points are within the similarity limits by passing `similarity=True` when plotting:
    """)
    return


@app.cell
def _(imp_conv_1):
    imp_conv_1.head_plot(similarity=True)
    return


if __name__ == "__main__":
    app.run()
