"""Module to define impeller class."""
import numpy as np
from collections import UserList
from prf2 import check_units, Point, NonDimensionalCurve


class Impeller(UserList):
    """Impeller class.

    Impeller instance is initialized with the list of points.
    The created instance will hold the dimensional points used in instantiation
    non dimensional points generated from the given dimensional points and
    another list of dimensional points based on current suction condition.
    Curves will be generated from points close in similarity.

    """
    @check_units
    def __init__(self, points, b=None, D=None):
        super().__init__(points)

        self.b = b
        self.D = D
        self.points = points

        self._suc = None

        self.non_dimensional_points = None

        self._calc_non_dimensional_points()

    @property
    def suc(self):
        return self._suc

    @suc.setter
    def suc(self, new_suc):
        self._suc = new_suc

    def _calc_non_dimensional_points(self):
        """Create list with non dimensional points."""
        non_dimensional_points = []
        for point in self:
            phi = self.phi(point)
            psi = self.psi(point)
            eff = point.eff
            volume_ratio = point.volume_ratio
            u = self.u(point)
            mach = self.mach(point)
            reynolds = self.reynolds(point)

            non_dimensional_point = NonDimensionalPoint(
                self, phi, psi, eff, volume_ratio, mach, reynolds)
            non_dimensional_points.append(non_dimensional_point)

        self.non_dimensional_points = non_dimensional_points

    def _calc_new_points(self):
        """Calculate new dimensional points based on the suction condition."""
        #  keep volume ratio constant
        for point in self:
            new_point = Point()

    def u(self, point):
        """Impeller tip speed."""
        speed = point.speed

        u = speed * self.D / 2

        return u

    def phi(self, point):
        """Flow coefficient."""
        flow_v = point.flow_v

        u = self.u(point)

        phi = (flow_v * 4 /
               (np.pi * self.D**2 * u))

        return phi.to('dimensionless')

    def psi(self, point):
        """Head coefficient."""
        head = point.head

        u = self.u(point)

        psi = 2 * head / u**2

        return psi.to('dimensionless')

    def s(self, point):
        """Work input factor."""
        suc = point.suc
        disch = point.disch

        delta_h = disch.h() - suc.h()
        u = self.u(point)

        s = delta_h / u**2

        return s.to('dimensionless')

    def mach(self, point):
        """Mach number."""
        suc = point.suc

        u = self.u(point)
        a = suc.speed_sound()

        mach = u / a

        return mach.to('dimensionless')

    def reynolds(self, point):
        """Reynolds number."""
        suc = point.suc

        u = self.u(point)
        b = self.b
        v = suc.viscosity() / suc.rho()

        reynolds = u * b / v

        return reynolds.to('dimensionless')

    def sigma(self, point):
        """Specific speed."""
        phi = self.phi(point)
        psi = self.psi(point)

        sigma = phi**(1/2) / psi**(3/4)

        return sigma


class NonDimensionalPoint:
    """Non Dimensional point.

    Parameters:
    -----------
    phi : float
        Flow coefficient.
    psi : float
        Head coefficient.
    eff : float
        Efficiency.

    """
    def __init__(self, impeller, phi, psi, eff, volume_ratio, mach, reynolds):
        self.impeller
        self.phi = phi
        self.psi = psi
        self.eff = eff
        self.volume_ratio = volume_ratio
        self.mach = mach
        self.reynolds = reynolds