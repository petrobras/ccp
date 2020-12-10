import csv

import matplotlib.pyplot as plt
import numpy as np
import toml
from bokeh.models import ColumnDataSource, CDSView, IndexFilter
from scipy.interpolate import interp1d
import plotly.graph_objects as go

from ccp import Q_, ureg, Point
from ccp.config.units import change_data_units


def plot_func(self, attr):
    def inner(*args, plot_kws=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments flow_v_units='...' and
        {attr}_units='...'. For the speed you can use speed_units='...'.
        """
        fig = kwargs.pop("fig", None)

        if fig is None:
            fig = go.Figure()

        if plot_kws is None:
            plot_kws = {}

        x_units = kwargs.get("flow_v_units", self.flow_v.units)
        x_units = ureg.Unit(x_units)
        try:
            y_units = kwargs.get(f"{attr}_units", getattr(self, attr).units)
        except AttributeError:
            y_units = kwargs.get(f"{attr}_units", getattr(self, attr)().units)
        y_units = ureg.Unit(y_units)
        speed_units = kwargs.get("speed_units", self.speed.units)
        speed_units = ureg.Unit(speed_units)
        name = kwargs.get("name", str(round(self.speed.to(speed_units))))

        flow_v = self.flow_v

        interpolated_curve = getattr(self, attr + "_interpolated")

        flow_v_range = np.linspace(min(flow_v), max(flow_v), 30)

        values_range = interpolated_curve(flow_v_range)

        values_range = values_range.magnitude

        if x_units is not None:
            flow_v_range = Q_(flow_v_range, self.flow_v.units).to(x_units).m
        if y_units is not None:
            try:
                values_range = Q_(values_range, getattr(self, attr).units).to(y_units).m
            except AttributeError:
                values_range = Q_(values_range, getattr(self, attr)().units).to(y_units).m

        fig.add_trace(go.Scatter(x=flow_v_range, y=values_range, name=name), **plot_kws)

        fig.update_layout(
            xaxis=dict(title=f"Volume Flow ({x_units:~H})"),
            yaxis=dict(title=f"{attr.capitalize()} ({y_units:~H})")
        )

        return fig

    return inner


def _bokeh_source_func(curve, attr):
    def inner(*args, **kwargs):
        """Return source data for bokeh plots."""
        x_units = kwargs.get("x_units", None)
        y_units = kwargs.get("y_units", None)
        speed_units = kwargs.get("speed_units", None)

        min_flow = curve.flow_v[0]
        max_flow = curve.flow_v[-1]

        x_data = np.linspace(min_flow, max_flow, 30) * min_flow.units
        y_data = getattr(curve, attr + "_interpolated")(x_data)

        x_data, y_data = change_data_units(x_data, y_data, x_units, y_units)

        speed = curve.speed
        if speed_units is not None:
            speed = speed.to(speed_units)

        delta_x_graph = abs(x_data[-1].magnitude - x_data[0].magnitude)
        delta_y_graph = abs(y_data[-1].magnitude - y_data[0].magnitude)

        curve_tan = ((y_data.magnitude[-1] - y_data.magnitude[-2]) / delta_y_graph) / (
            (x_data[-1].magnitude - x_data[-2].magnitude) / delta_x_graph
        )

        text_angle = np.arctan(curve_tan)

        length = len(x_data)

        source = ColumnDataSource(
            dict(
                x=x_data.magnitude,
                y=y_data.magnitude,
                speed=[speed.magnitude] * length,
                text_x_pos=[x_data.magnitude[-1]] * length,
                text_y_pos=[y_data.magnitude[-1]] * length,
                text=[f"{speed:.0f~P}"] * length,
                angle=[text_angle] * length,
                font_size=["6pt"] * length,
                x_units=[f"{x_data.units:~P}"] * length,
                y_units=[f"{y_data.units:~P}"] * length,
                speed_units=[f"{speed.units:~P}"] * length,
            )
        )

        return source

    return inner


def _bokeh_plot_func(curve, attr):
    def inner(*args, fig=None, source=None, plot_kws=None, **kwargs):
        if plot_kws is None:
            plot_kws = {}

        plot_kws.setdefault("color", "navy")
        plot_kws.setdefault("line_width", 1)
        plot_kws.setdefault("alpha", 0.5)

        if source is None:
            source = getattr(curve, attr + "_bokeh_source")(*args, **kwargs)

        fig.line("x", "y", source=source, **plot_kws)

        speed = CDSView(source=source, filters=[IndexFilter([0])])

        fig.text(
            x="text_x_pos",
            y="text_y_pos",
            source=source,
            view=speed,
            angle=source.data["angle"][0],
            text_font_size="6pt",
        )

        x_units_str = source.data["x_units"][0]
        y_units_str = source.data["y_units"][0]
        fig.xaxis.axis_label = f"Flow ({x_units_str})"
        fig.yaxis.axis_label = f"{attr} ({y_units_str})"

        return fig

    return inner


def interpolated_function(obj, attr):
    def inner(*args, **kwargs):
        values = getattr(obj, attr)
        if callable(values):
            values = values()

        units = values.units

        if len(values) < 3:
            interpolation_degree = 1
        else:
            interpolation_degree = 3

        interpol_function = interp1d(
            obj.flow_v.magnitude,
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

    return inner


class _CurveState:
    """Class used to create list with states from curve.

    This enables the following call:
    >>> curve.suc.p()
    (100000, 100000) pascal

    """

    def __init__(self, points, flow_v, speed):
        self.flow_v = flow_v
        self.points = points
        self.speed = speed

        # set a method for each suction attribute in the list
        for attr in ["p", "T", "h", "s"]:
            func = self.state_parameter(attr)
            setattr(self, attr, func)

            interpol_func = interpolated_function(self, attr)
            setattr(self, f"{attr}_interpolated", interpol_func)

            plot = plot_func(self, attr)
            setattr(self, f"{attr}_plot", plot)

            bokeh_source = _bokeh_source_func(self, attr)
            setattr(self, f"{attr}_bokeh_source", bokeh_source)

            bokeh_plot = _bokeh_plot_func(self, attr)
            setattr(self, f"{attr}_bokeh_plot", bokeh_plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def state_parameter(self, attr):
        def inner(*args, **kwargs):
            values = []

            for point in self:
                values.append(getattr(getattr(point, attr)(), "magnitude"))

            units = getattr(getattr(point, attr)(), "units")

            return Q_(values, units)

        return inner


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

        for param in ["head", "eff", "power", "phi", "psi"]:
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

            bokeh_source = _bokeh_source_func(self, param)
            setattr(self, param + "_bokeh_source", bokeh_source)

            bokeh_plot = _bokeh_plot_func(self, param)
            setattr(self, param + "_bokeh_plot", bokeh_plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)

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
        if file_type is "toml":
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
