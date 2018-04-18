from collections import UserList
from prf2 import Q_


class _CurveState(UserList):
    """Class used to create list with states from curve.

    This enables the following call:
    >>> curve.suc.p()
    (100000, 100000) pascal

    """

    def __init__(self, points):
        super().__init__(points)

        # set a method for each attribute in the list
        for attr in ['p', 'T', 'h', 's']:
            func = self.state_list(attr)
            setattr(self, attr, func)

    def state_list(self, attr):
        def inner():
            values = []

            for point in self:
                values.append(getattr(getattr(point, attr)(), 'magnitude'))

                units = getattr(getattr(point, attr)(), 'units')

            return Q_(values, units)
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

        self.suc = _CurveState([p.suc for p in self])
        self.disch = _CurveState([p.disch for p in self])

        for param in ['head', 'eff']:
            values = []
            for point in self:
                values.append(getattr(getattr(point, param), 'magnitude'))

            units = getattr(getattr(point, param), 'units')
            print(values)

            setattr(self, param, Q_(values, units))

