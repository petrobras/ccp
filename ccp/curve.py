import csv

import numpy as np
import toml
from scipy.interpolate import interp1d
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from ccp import Q_, ureg, Point


class StateParameter:
    def __init__(self, curve_state_object, attr):
        self.curve_state_object = curve_state_object
        self.attr = attr

    def __call__(self, *args, **kwargs):
        values = []

        for point in self.curve_state_object:
            values.append(getattr(getattr(point, self.attr)(), "magnitude"))

        units = getattr(getattr(point, self.attr)(), "units")

        return Q_(values, units)


def state_parameter(curve_state_object, attr):
    return StateParameter(curve_state_object, attr)


class PlotFunction:
    def __init__(self, curve_state_object, attr):
        self.curve_state_object = curve_state_object
        self.attr = attr

    def __call__(
        self, *args, plot_kws=None, show_points=False, similarity=False, **kwargs
    ):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments flow_v_units='...' and
        {attr}_units='...'. For the speed you can use speed_units='...'.

        Parameters
        ----------
        plot_kws: dict
            Keyword arguments to be passed to the plotly figure.
        show_points: bool, optional
            If True, the points will be plotted as markers.
        similarity : bool, optional
            If True, the points shows a hover with similarity table and limits for converted values.

        """
        curve_state_object = self.curve_state_object
        attr = self.attr
        fig = kwargs.pop("fig", None)
        color = kwargs.pop("color", None)

        if fig is None:
            fig = go.Figure()

        if plot_kws is None:
            plot_kws = {}

        x_units = kwargs.get("flow_v_units", curve_state_object.flow_v.units)
        x_units = ureg.Unit(x_units)
        try:
            y_units = kwargs.get(
                f"{attr}_units", getattr(curve_state_object, attr).units
            )
        except AttributeError:
            y_units = kwargs.get(
                f"{attr}_units", getattr(curve_state_object, attr)().units
            )
        y_units = ureg.Unit(y_units)
        speed_units = kwargs.get("speed_units", curve_state_object.speed.units)
        speed_units = ureg.Unit(speed_units)
        # if curve was extrapolated from two other curves extrapolated is true
        try:
            curve_extrapolated = curve_state_object._extrapolated
        except:
            curve_extrapolated = False

        if curve_extrapolated:
            line = dict(dash="dashdot")
            name = kwargs.get(
                "name",
                str(round(curve_state_object.speed.to(speed_units), 0))
                + "<br>(extrapolated)",
            )
        else:
            line = None
            name = kwargs.get(
                "name", str(round(curve_state_object.speed.to(speed_units), 0))
            )

        flow_v = flow_v_points = curve_state_object.flow_v
        flow_v_range = np.linspace(min(flow_v), max(flow_v), 30)
        interpolated_curve = getattr(curve_state_object, attr + "_interpolated")

        values_range = interpolated_curve(flow_v_range)
        values_range = values_range.magnitude
        try:
            values_points = getattr(curve_state_object, attr).magnitude
        except AttributeError:
            values_points = getattr(curve_state_object, attr)().magnitude

        if x_units is not None:
            flow_v_range = (
                Q_(flow_v_range, curve_state_object.flow_v.units).to(x_units).m
            )
            flow_v_points = Q_(flow_v, curve_state_object.flow_v.units).to(x_units).m
        if y_units is not None:
            try:
                values_range = (
                    Q_(values_range, getattr(curve_state_object, attr).units)
                    .to(y_units)
                    .m
                )
                values_points = (
                    Q_(values_points, getattr(curve_state_object, attr).units)
                    .to(y_units)
                    .m
                )
            except AttributeError:
                values_range = (
                    Q_(values_range, getattr(curve_state_object, attr)().units)
                    .to(y_units)
                    .m
                )
                values_points = (
                    Q_(values_points, getattr(curve_state_object, attr)().units)
                    .to(y_units)
                    .m
                )

        fig.add_trace(
            go.Scatter(
                x=flow_v_range,
                y=values_range,
                name=name,
                line_color=color,
                line=line,
            ),
            **plot_kws,
        )

        if attr == "head" or attr == "eff":
            data_similarity = {
                "volume_ratio_ratio": [
                    p.volume_ratio_ratio.m for p in curve_state_object.points
                ],
                "phi_ratio": [p.phi_ratio.m for p in curve_state_object.points],
                "mach": [p.mach.m for p in curve_state_object.points],
                "reynolds": [p.reynolds.m for p in curve_state_object.points],
                "volume_ratio_limits": [
                    [
                        0.95,
                        1.05,
                        (
                            True
                            if p.volume_ratio_ratio > 0.95
                            and p.volume_ratio_ratio < 1.05
                            else False
                        ),
                    ]
                    for p in curve_state_object.points
                ],
                "phi_ratio_limits": [
                    [
                        0.96,
                        1.04,
                        True if p.phi_ratio > 0.96 and p.phi_ratio < 1.04 else False,
                    ]
                    for p in curve_state_object.points
                ],
                "mach_limits": [
                    [l["lower"].m, l["upper"].m, l["within_limits"]]
                    for l in [
                        p.mach_limits(mmsp=p.mach - p.mach_diff)
                        for p in curve_state_object.points
                    ]
                ],
                "reynolds_limits": [
                    [l["lower"].m, l["upper"].m, l["within_limits"]]
                    for l in [
                        p.reynolds_limits(remsp=p.reynolds / p.reynolds_ratio)
                        for p in curve_state_object.points
                    ]
                ],
            }
            df_similarity = pd.DataFrame(data_similarity)

        if show_points or similarity:
            hovertemplate = None
            customdata = None
            hoverlabel = None
            color_marker = color
            line = None
            hoverlabel = None
            size = None
            line = dict(color=color, width=1)

            for i in range(len(curve_state_object.points)):
                symbol = "circle"
                if similarity and (attr == "head" or attr == "eff"):
                    customdata = (
                        df_similarity[
                            [
                                "volume_ratio_ratio",
                                "phi_ratio",
                                "mach",
                                "reynolds",
                                "volume_ratio_limits",
                                "phi_ratio_limits",
                                "mach_limits",
                                "reynolds_limits",
                            ]
                        ]
                        .iloc[i]
                        .values.tolist()
                    )
                    color_marker = [
                        (
                            "#7EE38D"
                            if np.all([customdata[i][2] for i in range(4, 7)]) == True
                            else "#FC9FB0"
                        )
                    ]
                    size = 8
                    hoverlabel = dict(namelength=-1)
                    hovertemplate = (
                        "<b>(v<sub>i</sub> / v<sub>d</sub>)<sub>c</sub> / (v<sub>i</sub> / v<sub>d</sub>)<sub>o</sub>:</b> %{customdata[0]:.3f} "
                        "<b>limits:</b> %{customdata[4][0]:.3f} - %{customdata[4][1]:.3f}<br>"
                        + "<b>φ<sub>c</sub> / φ<sub>o</sub>:</b> %{customdata[1]:.3f} "
                        "             <b>limits:</b>     %{customdata[5][0]:.3f} - %{customdata[5][1]:.3f}<br>"
                        + "<b>Mm<sub>c</sub>:</b>  %{customdata[2]:.4f} "
                        "              <b>limits:</b> %{customdata[6][0]:.4f} - %{customdata[6][1]:.4f}<br>"
                        + "<b>Rem<sub>c</sub>:</b> %{customdata[3]:.3e} "
                        " <b>limits:</b> %{customdata[7][0]:.3e} - %{customdata[7][1]:.3e}"
                        + "<extra></extra>",
                    )
                else:
                    symbol = symbol + "-open"
                fig.add_trace(
                    go.Scatter(
                        x=[flow_v_points[i]],
                        y=[values_points[i]],
                        marker=dict(
                            color=color_marker, symbol=symbol, size=size, line=line
                        ),
                        mode="markers",
                        name=name,
                        showlegend=False,
                        customdata=[customdata],
                        hovertemplate=hovertemplate,
                        hoverlabel=hoverlabel,
                    )
                )
                if similarity:
                    fig.update_layout(hovermode="closest", hoverdistance=10)

        fig.update_layout(
            xaxis=dict(title=f"Volume Flow ({x_units:~H})"),
            yaxis=dict(title=f"{attr.capitalize()} ({y_units:~H})"),
        )

        return fig


def plot_func(curve_state_object, attr):
    return PlotFunction(curve_state_object, attr)


class InterpolatedFunction:
    def __init__(self, curve_state_object, attr):
        self.curve_state_object = curve_state_object
        self.attr = attr

    def __call__(self, *args, **kwargs):
        curve_state_object = self.curve_state_object
        attr = self.attr
        values = getattr(curve_state_object, attr)
        if callable(values):
            values = values()

        units = values.units

        if len(values) < 3:
            interpolation_degree = 1
        else:
            interpolation_degree = 3

        interpol_function = interp1d(
            curve_state_object.flow_v.magnitude,
            values.magnitude,
            kind=interpolation_degree,
            fill_value="extrapolate",
        )

        try:
            args = [arg.magnitude for arg in args]
        except AttributeError:
            pass

        result = Q_(interpol_function(*args, **kwargs), units)
        if isinstance(*args, (int, float)):
            result = Q_(float(result.magnitude), result.units)

        return result


def interpolated_function(curve_state_object, attr):
    return InterpolatedFunction(curve_state_object, attr)


class _CurveState:
    """Class used to create list with states from curve.

    This enables the following call:
    # >>> curve.suc.p()
    (100000, 100000) pascal

    """

    def __init__(self, points, flow_v, speed, extrapolated=False):
        self.flow_v = flow_v
        self.points = points
        self.speed = speed
        self._extrapolated = extrapolated

        # set a method for each suction attribute in the list
        for attr in ["p", "T", "h", "s", "rho"]:
            func = state_parameter(self, attr)
            setattr(self, attr, func)

            interpol_func = interpolated_function(self, attr)
            setattr(self, f"{attr}_interpolated", interpol_func)

            plot = plot_func(self, attr)
            setattr(self, f"{attr}_plot", plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)


class Curve:
    """Curve.

    A curve is a collection of points that share the same suction
    state and the same speed.

    Parameters
    ----------

    points : list
        List with the points
    """

    def __init__(self, points, extrapolated=False):
        if len(points) < 2:
            raise TypeError("At least 2 points should be given.")
        self.points = sorted(points, key=lambda p: p.flow_v)
        # if curve was extrapolated from two other curves extrapolated is true
        self._extrapolated = extrapolated
        if self._extrapolated:
            for p in points:
                p._extrapolated = True

        _flow_v_values = [p.flow_v.magnitude for p in self]
        _flow_v_units = self[0].flow_v.units
        self.flow_v = Q_(_flow_v_values, _flow_v_units)

        self.speed = self[0].speed
        self.power_losses = self.points[0].power_losses
        # change the following check in the future
        for point in self:
            if self.speed != point.speed:
                raise ValueError("Speed for each point should be equal")

        self.suc = _CurveState(
            [p.suc for p in self],
            flow_v=self.flow_v,
            speed=self.speed,
            extrapolated=extrapolated
        )
        self.disch = _CurveState(
            [p.disch for p in self],
            flow_v=self.flow_v,
            speed=self.speed,
            extrapolated=extrapolated
        )

        for param in [
            "head",
            "eff",
            "power",
            "power_shaft",
            "torque",
            "phi",
            "psi",
            "flow_m",
        ]:
            values = []
            for point in self:
                try:
                    values.append(getattr(getattr(point, param), "magnitude"))
                    units = getattr(getattr(point, param), "units")
                except AttributeError:
                    continue

            setattr(self, param, Q_(values, units))

            interpol_func = interpolated_function(self, param)
            setattr(self, f"{param}_interpolated", interpol_func)

            plot = plot_func(self, param)
            setattr(self, param + "_plot", plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def __iter__(self):
        for point in self.points:
            yield point

    def __len__(self):
        return len(self.points)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            for point_self, point_other in zip(self.points, other.points):
                if point_self != point_other:
                    return False
            else:
                return True

    def _dict_to_save(self):
        return {f"point{i}": point._dict_to_save() for i, point in enumerate(self)}

    def save(self, file_name, file_type="toml"):
        """Save curve to a file.

        Parameters
        ----------
        file_name: str
            Name of the file.
        file_type: str
            File type can be: toml.
        """
        if file_type == "toml":
            with open(file_name, mode="w") as f:
                toml.dump(self._dict_to_save(), f)

    def save_hysys_csv(self, curve_path):
        """Save curve to a csv with hysys format.

        curve_path: pathlib.Path
            Path where the curve file will be saved.
        """
        curve_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(curve_path), mode="w") as csv_file:
            field_names = ["Volume Flow (m3/h)", "Head (m)", "Efficiency (%)"]
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()
            for point in self:
                writer.writerow(
                    {
                        "Volume Flow (m3/h)": point.flow_v.to("m**3/h").m,
                        "Head (m)": point.head.m / 9.81,
                        "Efficiency (%)": 100 * point.eff.m,
                    }
                )

    @classmethod
    def load(cls, file_name):
        with open(file_name) as f:
            parameters = toml.load(f)

        return cls(
            [Point(**Point._dict_from_load(kwargs)) for kwargs in parameters.values()]
        )
