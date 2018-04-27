import numpy as np
import matplotlib.pyplot as plt
import warnings
from scipy.interpolate import UnivariateSpline
from ccp import Q_


def plot_func(self, attr):
    def inner(*args, **kwargs):
        ax = kwargs.pop('ax', None)

        if ax is None:
            ax = plt.gca()

        values = []

        for point in self:
            point_attr = getattr(point, attr)
            if callable(point_attr):
                values.append(getattr(point_attr(), 'magnitude'))
                units = getattr(getattr(point, attr)(), 'units')
            else:
                values.append(getattr(point_attr, 'magnitude'))
                units = getattr(getattr(point, attr), 'units')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            interpolated_curve = UnivariateSpline(
                self.flow_v.magnitude, values)

        flow_v_range = np.linspace(min(self.flow_v.magnitude),
                                   max(self.flow_v.magnitude),
                                   30)
        values_range = interpolated_curve(flow_v_range)

        ax.plot(flow_v_range, values_range, **kwargs)

        delta_x_graph = ax.get_xlim()[1] - ax.get_xlim()[0]
        delta_y_graph = ax.get_ylim()[1] - ax.get_ylim()[0]

        curve_tan = ((values_range[-1] - values_range[-2]) / delta_y_graph) / \
                    ((flow_v_range[-1] - flow_v_range[-2]) / delta_x_graph)
        text_angle = np.arctan(curve_tan)
        text_angle = Q_(text_angle, 'rad').to('deg').magnitude

        ax.text(flow_v_range[-1], values_range[-1], f'{self.speed:.0f}',
                ha='left', va='top', rotation=text_angle)
        ax.set_xlabel(f'Volumetric flow ({self.flow_v.units:P~})')
        ax.set_ylabel(f'{attr} ({units:P~})')

        if kwargs.get('draw_points') is True:
            ax.scatter(self.flow_v.magnitude, values)

        return ax

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
            plot = plot_func(self, attr)
            setattr(self, attr + '_plot', plot)

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

            plot = plot_func(self, param)
            setattr(self, param + '_plot', plot)

    def __getitem__(self, item):
        return self.points.__getitem__(item)


