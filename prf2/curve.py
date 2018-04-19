import matplotlib.pyplot as plt
from collections import UserList
from prf2 import Q_


class _CurveState(UserList):
    """Class used to create list with states from curve.

    This enables the following call:
    >>> curve.suc.p()
    (100000, 100000) pascal

    """
    def __init__(self, points, flow_v):
        super().__init__(points)
        self.flow_v = flow_v

        # set a method for each suction attribute in the list
        for attr in ['p', 'T', 'h', 's']:
            func = self.state_parameter(attr)
            setattr(self, attr, func)
            plot_func = self.plot(attr)
            setattr(self, attr + '_plot', plot_func)

    def state_parameter(self, attr):
        def inner(*args, **kwargs):
            values = []

            for point in self:
                values.append(getattr(getattr(point, attr)(), 'magnitude'))

            units = getattr(getattr(point, attr)(), 'units')

            return Q_(values, units)

        return inner

    def plot(self, attr):
        def inner(*args, **kwargs):
            ax = kwargs.get('ax', None)

            if ax is None:
                ax = plt.gca()

            values = []

            for point in self:
                values.append(getattr(getattr(point, attr)(), 'magnitude'))

            units = getattr(getattr(point, attr)(), 'units')

            ax.plot(self.flow_v.magnitude, values)
            ax.set_xlabel(f'Volumetric flow ({self.flow_v.units:P~})')
            ax.set_ylabel(f'{attr} ({units:P~})')

            return ax

        return inner


class Curve(UserList):
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
        super().__init__(sorted(points, key=lambda p: p.flow_v))

        _flow_v_values = [p.flow_v.magnitude for p in self]
        _flow_v_units = self[0].flow_v.units
        self.flow_v = Q_(_flow_v_values, _flow_v_units)

        self.speed = self[0].speed
        # change the following check in the future
        for point in self:
            if self.speed != point.speed:
                raise ValueError('Speed for each point should be equal')

        self.suc = _CurveState([p.suc for p in self], flow_v=self.flow_v)
        self.disch = _CurveState([p.disch for p in self], flow_v=self.flow_v)

        for param in ['head', 'eff', 'power']:
            values = []
            for point in self:
                values.append(getattr(getattr(point, param), 'magnitude'))

            units = getattr(getattr(point, param), 'units')

            setattr(self, param, Q_(values, units))


class NonDimensionalCurve(UserList):
    """Non Dimensional Curve."""
    def __init__(self, points):
        if len(points) < 2:
            raise TypeError('At least 2 points should be given.')
        super().__init__(sorted(points, key=lambda p: p.phi))

        for param in ['phi', 'psi', 'eff']:
            values = []
            for point in self:
                values.append(getattr(getattr(point, param), 'magnitude'))

            units = getattr(getattr(point, param), 'units')

            setattr(self, param, Q_(values, units))

