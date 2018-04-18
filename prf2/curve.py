from collections import UserList


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
        super().__init__(sorted(points, key=lambda point: point.flow_v))
