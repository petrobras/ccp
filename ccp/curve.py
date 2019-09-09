import csv

import matplotlib.pyplot as plt
import numpy as np
import toml
from bokeh.models import ColumnDataSource, CDSView, IndexFilter
from scipy.interpolate import interp1d

from ccp import Q_, Point
from ccp.config.units import change_data_units


def plot_func(self, attr):
    def inner(*args, plot_kws=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments x_units='...' and
        y_units='...'. For the speed you can use speed_units='...'.
        """
        ax = kwargs.pop('ax', None)

        if ax is None:
            ax = plt.gca()

        if plot_kws is None:
            plot_kws = {}

        x_units = kwargs.get('x_units', None)
        y_units = kwargs.get('y_units', None)
        speed_units = kwargs.get('speed_units', None)

        values = []

        for point in self:
            point_attr = getattr(point, attr)
            if callable(point_attr):
                point_attr = point_attr()

            if y_units is not None:
                point_attr = point_attr.to(y_units)

            values.append(getattr(point_attr, 'magnitude'))
            units = getattr(point_attr, 'units')

        flow_v = self.flow_v

        if x_units is not None:
            flow_v = flow_v.to(x_units)

        interpolated_curve = getattr(self, attr + '_interpolated')

        flow_v_range = np.linspace(min(flow_v),
                                   max(flow_v),
                                   30)

        values_range = interpolated_curve(flow_v_range)
        if y_units is not None:
            values_range = values_range.to(y_units)

        values_range = values_range.magnitude

        if kwargs.pop('draw_points', None) is True:
            ax.scatter(flow_v, values, **plot_kws)
        if kwargs.pop('draw_current_point', True) is True:
            pass
            #  TODO implement plot of the current point with hline and vline.

        ax.plot(flow_v_range, values_range, **plot_kws)

        delta_x_graph = ax.get_xlim()[1] - ax.get_xlim()[0]
        delta_y_graph = ax.get_ylim()[1] - ax.get_ylim()[0]

        curve_tan = ((values_range[-1] - values_range[-2]) / delta_y_graph) / \
                    ((flow_v_range[-1] - flow_v_range[-2]) / delta_x_graph)
        text_angle = np.arctan(curve_tan)
        text_angle = Q_(text_angle, 'rad').to('deg').magnitude

        speed = self.speed
        if speed_units is not None:
            speed = speed.to(speed_units)
        ax.text(flow_v_range[-1], values_range[-1], f'{speed:P~.0f}',
                ha='left', va='top', rotation=text_angle, clip_on=True)

        ax.set_xlabel(f'Volumetric flow ({flow_v.units:P~})')
        ax.set_ylabel(f'{attr} ({units:P~})')

        return ax

    return inner


def _bokeh_source_func(curve, attr):
    def inner(*args, **kwargs):
        """Return source data for bokeh plots."""
        x_units = kwargs.get('x_units', None)
        y_units = kwargs.get('y_units', None)
        speed_units = kwargs.get('speed_units', None)

        min_flow = curve.flow_v[0]
        max_flow = curve.flow_v[-1]

        x_data = np.linspace(min_flow, max_flow, 30) * min_flow.units
        y_data = getattr(curve, attr + '_interpolated')(x_data)

        x_data, y_data = change_data_units(x_data, y_data, x_units, y_units)

        speed = curve.speed
        if speed_units is not None:
            speed = speed.to(speed_units)

        delta_x_graph = abs(x_data[-1].magnitude - x_data[0].magnitude)
        delta_y_graph = abs(y_data[-1].magnitude - y_data[0].magnitude)

        curve_tan = (((y_data.magnitude[-1] - y_data.magnitude[-2]) / delta_y_graph)
                     / ((x_data[-1].magnitude - x_data[-2].magnitude) / delta_x_graph))

        text_angle = np.arctan(curve_tan)

        length = len(x_data)

        source = ColumnDataSource(
            dict(x=x_data.magnitude,
                 y=y_data.magnitude,
                 speed=[speed.magnitude] * length,
                 text_x_pos=[x_data.magnitude[-1]] * length,
                 text_y_pos=[y_data.magnitude[-1]] * length,
                 text=[f'{speed:.0f~P}'] * length,
                 angle=[text_angle] * length,
                 font_size=['6pt'] * length,
                 x_units=[f'{x_data.units:~P}'] * length,
                 y_units=[f'{y_data.units:~P}'] * length,
                 speed_units=[f'{speed.units:~P}'] * length)
                                  )

        return source
    return inner


def _bokeh_plot_func(curve, attr):
    def inner(*args, fig=None, source=None, plot_kws=None, **kwargs):
        if plot_kws is None:
            plot_kws = {}

        plot_kws.setdefault('color', 'navy')
        plot_kws.setdefault('line_width', 1)
        plot_kws.setdefault('alpha', 0.5)

        if source is None:
            source = getattr(curve, attr + '_bokeh_source')(*args, **kwargs)

        fig.line('x', 'y', source=source, **plot_kws)

        speed = CDSView(source=source, filters=[IndexFilter([0])])

        fig.text(x='text_x_pos', y='text_y_pos', source=source, view=speed,
                 angle=source.data['angle'][0], text_font_size='6pt')

        x_units_str = source.data["x_units"][0]
        y_units_str = source.data["y_units"][0]
        fig.xaxis.axis_label = f'Flow ({x_units_str})'
        fig.yaxis.axis_label = f'{attr} ({y_units_str})'

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
            obj.flow_v.magnitude, values.magnitude,
            kind=interpolation_degree, fill_value='extrapolate')

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
        for attr in ['p', 'T', 'h', 's']:
            func = self.state_parameter(attr)
            setattr(self, attr, func)

            interpol_func = interpolated_function(self, attr)
            setattr(self, f'{attr}_interpolated', interpol_func)

            plot = plot_func(self, attr)
            setattr(self, f'{attr}_plot', plot)

            bokeh_source = _bokeh_source_func(self, attr)
            setattr(self, f'{attr}_bokeh_source', bokeh_source)

            bokeh_plot = _bokeh_plot_func(self, attr)
            setattr(self, f'{attr}_bokeh_plot', bokeh_plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def state_parameter(self, attr):
        def inner(*args, **kwargs):
            values = []

            for point in self:
                values.append(getattr(getattr(point, attr)(), 'magnitude'))

            units = getattr(getattr(point, attr)(), 'units')

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
            raise TypeError('At least 2 points should be given.')
        self.points = sorted(points, key=lambda p: p.flow_v)

        _flow_v_values = [p.flow_v.magnitude for p in self]
        _flow_v_units = self[0].flow_v.units
        self.flow_v = Q_(_flow_v_values, _flow_v_units)

        self.speed = self[0].speed
        # change the following check in the future
        for point in self:
            if self.speed != point.speed:
                raise ValueError('Speed for each point should be equal')

        self.suc = _CurveState([p.suc for p in self],
                               flow_v=self.flow_v, speed=self.speed)
        self.disch = _CurveState([p.disch for p in self],
                                 flow_v=self.flow_v, speed=self.speed)

        for param in ['head', 'eff', 'power', 'phi', 'psi']:
            values = []
            for point in self:
                try:
                    values.append(getattr(getattr(point, param), 'magnitude'))
                    units = getattr(getattr(point, param), 'units')
                except AttributeError:
                    continue

            setattr(self, param, Q_(values, units))

            interpol_func = interpolated_function(self, param)
            setattr(self, f'{param}_interpolated', interpol_func)

            plot = plot_func(self, param)
            setattr(self, param + '_plot', plot)

            bokeh_source = _bokeh_source_func(self, param)
            setattr(self, param + '_bokeh_source', bokeh_source)

            bokeh_plot = _bokeh_plot_func(self, param)
            setattr(self, param + '_bokeh_plot', bokeh_plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def _dict_to_save(self):
        return {f'point{i}': point._dict_to_save() for i, point in enumerate(self)}

    def save(self, file_name, file_type='toml'):
        """Save curve to a file.

        Parameters
        ----------
        file_name: str
            Name of the file.
        file_type: str
            File type can be: toml.
        """
        if file_type is 'toml':
            with open(file_name, mode='w') as f:
                toml.dump(self._dict_to_save(), f)

    def save_hysys_csv(self, curve_path):
        """Save curve to a csv with hysys format.

        curve_path: pathlib.Path
            Path where the curve file will be saved.
        """
        curve_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(curve_path), mode='w') as csv_file:
            field_names = ['Volume Flow (m3/h)', 'Head (m)', 'Efficiency (%)']
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()
            for point in self:
                writer.writerow(
                    {
                        'Volume Flow (m3/h)': point.flow_v.to('m**3/h').m,
                        'Head (m)': point.head.m / 9.81,
                        'Efficiency (%)': 100 * point.eff.m
                    }
                )

    @classmethod
    def load(cls, file_name):
        with open(file_name) as f:
            parameters = toml.load(f)

        return cls(
            [Point(**Point._dict_from_load(kwargs)) for kwargs in parameters.values()]
        )
