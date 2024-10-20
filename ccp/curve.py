import csv

import numpy as np
import toml
from scipy.interpolate import interp1d
import plotly.graph_objects as go

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

    def __call__(self, *args, plot_kws=None, show_points=False, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments flow_v_units='...' and
        {attr}_units='...'. For the speed you can use speed_units='...'.

        Parameters
        ----------
        plot_kws: dict
            Keyword arguments to be passed to the plotly figure.
        show_points: bool, optional
            If True, the points will be plotted as markers.

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
        name = kwargs.get("name", str(round(curve_state_object.speed.to(speed_units))))

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
            ),
            **plot_kws,
        )
        if show_points:
            fig.add_trace(
                go.Scatter(
                    x=flow_v_points,
                    y=values_points,
                    marker=dict(color=color, symbol="circle-open"),
                    mode="markers",
                    name=name,
                    showlegend=False,
                )
            )

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

    def __init__(self, points, flow_v, speed):
        self.flow_v = flow_v
        self.points = points
        self.speed = speed

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

    def __init__(self, points):
        if len(points) < 2:
            raise TypeError("At least 2 points should be given.")
        self.points = sorted(points, key=lambda p: p.flow_v)

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
            [p.suc for p in self], flow_v=self.flow_v, speed=self.speed
        )
        self.disch = _CurveState(
            [p.disch for p in self], flow_v=self.flow_v, speed=self.speed
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
