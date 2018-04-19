"""Module to define impeller class."""
from collections import UserList


class Impeller(UserList):
    """Impeller class.

    Impeller instance is initialized with the dimensional curve.
    The created instance will hold the dimensional curve used in instantiation
    a non dimensional curve generated from the given dimensional curve and
    another dimensional curve based on current suction condition and speed.

    """
    def __init__(self, curves, b=None, D=None):
        super().__init__(curves)

        self.b = b
        self.D = D

        for c in self.curves:
            setattr(self, f'curve_known_{c.speed:.0f}', c)




