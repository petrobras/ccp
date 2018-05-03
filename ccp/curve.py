import numpy as np
import matplotlib.pyplot as plt
import warnings
from scipy.interpolate import interp1d
from ccp import Q_


def plot_func(self, attr):
    def inner(*args, plot_kws=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments x_units='...' and
        y_units='...'. For the speed you can use speed_units='...'.
        """
        ax = kwargs.pop('ax', None)

        if ax is None:
            ax = plt.gca()

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


def interpolated_function(obj, attr):
    def inner(*args, **kwargs):
        values = getattr(obj, attr)
        if callable(values):
            values = values()

        units = values.units

        number_of_points = len(values)
        if number_of_points % 2 == 0:
            number_of_points = number_of_points - 1

        interpol_function = interp1d(
            obj.flow_v.magnitude, values.magnitude,
            kind=number_of_points, fill_value='extrapolate')

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

    def __getitem__(self, item):
        return self.points.__getitem__(item)


