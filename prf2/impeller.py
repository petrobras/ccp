"""Module to define impeller class."""
import weakref
import numpy as np
from collections import UserList
from copy import deepcopy
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
        self.b = b
        self.D = D

        self.points = deepcopy(points)

        for p in self.points:
            p.mach = self.mach(p)
            p.reynolds = self.reynolds(p)

        super().__init__(self.points)

        self._suc = None

        self.non_dimensional_points = None
        self.new_points = None

        self._calc_non_dimensional_points()

    @property
    def suc(self):
        return self._suc

    @suc.setter
    def suc(self, new_suc):
        self._suc = new_suc
        self._calc_new_points()

    def _calc_non_dimensional_points(self):
        """Create list with non dimensional points."""
        non_dimensional_points = []
        for point in self:
            if point.speed is None:
                raise ValueError('Point used to instantiate impeller needs'
                                 ' to have speed attribute.')
            phi = self.phi(point)
            psi = self.psi(point)
            eff = point.eff
            volume_ratio = point.volume_ratio
            mach = self.mach(point)
            reynolds = self.reynolds(point)

            non_dimensional_point = NonDimensionalPoint(
                self, phi, psi, eff, volume_ratio, mach, reynolds)
            non_dimensional_points.append(non_dimensional_point)

        self.non_dimensional_points = non_dimensional_points

    def _calc_new_points(self):
        """Calculate new dimensional points based on the suction condition."""
        #  keep volume ratio constant
        new_points = []
        for non_dim_point in self.non_dimensional_points:
            new_points.append(non_dim_point.calc_dim_point())

        self.new_points = new_points

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
    im
    phi : float
        Flow coefficient.
    psi : float
        Head coefficient.
    eff : float
        Efficiency.

    """
    def __init__(self, impeller, phi, psi, eff, volume_ratio, mach, reynolds):
        #  gc safe ref to impeller
        self.impeller = impeller
        self.phi = phi
        self.psi = psi
        self.eff = eff
        self.volume_ratio = volume_ratio
        self.mach = mach
        self.reynolds = reynolds

    def calc_dim_point(self):
        """Calculate dimensional point from non-dimensional.

        Point will be calculated considering the new impeller suction condition.
        """
        point = Point(suc=self.impeller.suc, eff=self.eff,
                      volume_ratio=self.volume_ratio)

        point.speed = self._speed_from_psi(point)
        point.flow_v = self._flow_from_phi(point)
        point.flow_m = point.flow_v * self.impeller.suc.rho()
        point.power = point._power_calc()

        return point

    def _u_from_psi(self, point):
        psi = self.psi
        head = point.head

        u = np.sqrt(2 * head / psi)

        return u.to('m/s')

    def _speed_from_psi(self, point):
        D = self.impeller.D
        u = self._u_from_psi(point)

        speed = 2 * u / D

        return speed.to('rad/s')

    def _flow_from_phi(self, point):
        # TODO get flow for point generated from suc-eff-vol_ratio
        phi = self.phi
        D = self.impeller.D
        u = self._u_from_psi(point)

        flow_v = phi * (np.pi * D**2 * u) / 4

        return flow_v

