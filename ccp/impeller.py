"""Module to define impeller class."""
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
from itertools import groupby
from ccp.config.utilities import r_getattr
from ccp import check_units, Point, Curve


class Impeller:
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
        # TODO group points with the same speed in curves

        for p in self.points:
            self._add_non_dimensional_attributes(p)

        curves = []
        for speed, grouped_points in groupby(
                sorted(self.points, key=lambda point: point.speed),
                key=lambda point: point.speed):
            points = [point for point in grouped_points]
            curves.append(Curve(points))
        self.curves = curves

        for attr in ['disch.p', 'disch.T', 'head', 'eff', 'power']:
            setattr(self, attr.replace('.', '_') + '_plot',
                    self.plot_func(attr))

        self._suc = None

        self.non_dimensional_points = None
        self.new_points = None

        self._calc_non_dimensional_points()

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def _add_non_dimensional_attributes(self, point):
        additional_point_attributes = ['phi', 'psi', 'mach', 'reynolds']
        for attr in additional_point_attributes:
            setattr(point, attr, getattr(self, '_' + attr)(point))

    def plot_func(self, attr):
        def inner(*args, **kwargs):
            ax = kwargs.get('ax')
            if ax is None:
                ax = plt.gca()

            for curve in self.curves:
                ax = r_getattr(curve, attr + '_plot')(ax=ax)
            return ax
        return inner

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
            phi = self._phi(point)
            psi = self._psi(point)
            eff = point.eff
            volume_ratio = point.volume_ratio
            mach = self._mach(point)
            reynolds = self._reynolds(point)

            non_dimensional_point = NonDimensionalPoint(
                self, phi, psi, eff, volume_ratio, mach, reynolds)
            non_dimensional_points.append(non_dimensional_point)

        self.non_dimensional_points = non_dimensional_points

    def _calc_new_points(self):
        """Calculate new dimensional points based on the suction condition."""
        #  keep volume ratio constant
        # new_curves = []
        # for curve in self.curves:
        #     new_points = []
        #     for point in curve:
        #         new_points.append(self._calc_from_non_dimensional(point))
        #
        #     speed_mean = np.mean([p.speed.magnitude for p in new_points])
        #     speed_std = np.mean([p.speed.magnitude for p in new_points])
        #
        #     if speed_std < 5:
        #         for p in new_points:
        #             p.speed = Q_(speed_mean, p.speed.units)

        new_points = []
        for non_dim_point in self.non_dimensional_points:
            new_point = non_dim_point.calc_dim_point()
            self._add_non_dimensional_attributes(new_point)

            new_points.append(new_point)

        self.new_points = new_points

    def _u(self, point):
        """Impeller tip speed."""
        speed = point.speed

        u = speed * self.D / 2

        return u

    def _phi(self, point):
        """Flow coefficient."""
        flow_v = point.flow_v

        u = self._u(point)

        phi = (flow_v * 4 /
               (np.pi * self.D**2 * u))

        return phi.to('dimensionless')

    def _psi(self, point):
        """Head coefficient."""
        head = point.head

        u = self._u(point)

        psi = 2 * head / u**2

        return psi.to('dimensionless')

    def _work_input_factor(self, point):
        """Work input factor."""
        suc = point.suc
        disch = point.disch

        delta_h = disch.h() - suc.h()
        u = self._u(point)

        s = delta_h / u**2

        return s.to('dimensionless')

    def _mach(self, point):
        """Mach number."""
        suc = point.suc

        u = self._u(point)
        a = suc.speed_sound()

        mach = u / a

        return mach.to('dimensionless')

    def _reynolds(self, point):
        """Reynolds number."""
        suc = point.suc

        u = self._u(point)
        b = self.b
        v = suc.viscosity() / suc.rho()

        reynolds = u * b / v

        return reynolds.to('dimensionless')

    def sigma(self, point):
        """Specific speed."""
        phi = self._phi(point)
        psi = self._psi(point)

        sigma = phi**(1/2) / psi**(3/4)

        return sigma

    def _calc_from_non_dimensional(self, point):
        """Calculate dimensional point from non-dimensional.

        Point will be calculated considering the new impeller suction condition.
        """
        point = Point(suc=self.suc, eff=point.eff,
                      volume_ratio=point.volume_ratio)

        point.speed = self._speed_from_psi(point)
        point.flow_v = self._flow_from_phi(point)
        point.flow_m = point.flow_v * self.suc.rho()
        point.power = point._power_calc()

        return point

    def _u_from_psi(self, point):
        psi = point.psi
        head = point.head

        u = np.sqrt(2 * head / psi)

        return u.to('m/s')

    def _speed_from_psi(self, point):
        D = self.D
        u = self._u_from_psi(point)

        speed = 2 * u / D

        return speed.to('rad/s')

    def _flow_from_phi(self, point):
        # TODO get flow for point generated from suc-eff-vol_ratio
        phi = point.phi
        D = self.D
        u = self._u_from_psi(point)

        flow_v = phi * (np.pi * D**2 * u) / 4

        return flow_v


class NonDimensionalPoint:
    """Non Dimensional point.

    Parameters:
    -----------
    im
    _phi : float
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

