"""Module to define impeller class."""
from collections import UserList


class Impeller(UserList):
    """Impeller class.

    Impeller instance is initialized with the list of points.
    The created instance will hold the dimensional points used in instantiation
    non dimensional points generated from the given dimensional points and
    another list of dimensional points based on current suction condition.
    Curves will be generated from points close in similarity.

    """
    def __init__(self, points, b=None, D=None):
        super().__init__(points)

        self.b = b
        self.D = D
        self.points = points

        self._suc = None

    @property
    def suc(self):
        return self._suc

    @suc.setter
    def suc(self, new_suc):
        self._suc = new_suc

    def tip_speed(self, point=None):
        """Impeller tip speed."""

        speed = point.speed

        u = speed * self.D / 2

        return u






