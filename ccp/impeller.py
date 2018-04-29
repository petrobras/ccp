"""Module to define impeller class."""
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
from itertools import groupby
from ccp.config.utilities import r_getattr
from ccp import Q_, check_units, Point, Curve


class Impeller:
    """Impeller class.

    Impeller instance is initialized with the list of points.
    The created instance will hold the dimensional points used in instantiation
    non dimensional points generated from the given dimensional points and
    another list of dimensional points based on current suction condition.
    Curves will be generated from points close in similarity.

    """
    @check_units
    def __init__(self, points, b=None, D=None, _suc=None):
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
            curve = Curve(points)
            curves.append(curve)
            setattr(self, f'curve_{int(curve.speed.magnitude)}', curve)
        self.curves = curves

        for attr in ['disch.p', 'disch.T', 'head', 'eff', 'power']:
            setattr(self, attr.replace('.', '_') + '_plot',
                    self.plot_func(attr))

        self._suc = _suc

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def _add_non_dimensional_attributes(self, point):
        additional_point_attributes = ['phi', 'psi', 'mach', 'reynolds']
        for attr in additional_point_attributes:
            setattr(point, attr, getattr(self, '_' + attr)(point))

    def plot_func(self, attr):
        def inner(*args, **kwargs):
            ax = kwargs.pop('ax', None)
            if ax is None:
                ax = plt.gca()

            for curve in self.curves:
                ax = r_getattr(curve, attr + '_plot')(ax=ax, **kwargs)

            return ax

        inner.__doc__ = r_getattr(self.curves[0], attr + '_plot').__doc__

        return inner

    @property
    def suc(self):
        return self._suc

    @suc.setter
    def suc(self, new_suc):
        self._suc = new_suc
        self._calc_new_points()

    def _calc_new_points(self):
        """Calculate new dimensional points based on the suction condition."""
        #  keep volume ratio constant
        all_points = []
        for curve in self.curves:
            new_points = []
            for point in curve:
                new_points.append(self._calc_from_non_dimensional(point))

            speed_mean = np.mean([p.speed.magnitude for p in new_points])
            speed_std = np.std([p.speed.magnitude for p in new_points])

            if speed_std < 5:
                for p in new_points:
                    p.speed = Q_(speed_mean, p.speed.units)
            else:
                raise NotImplementedError('Coerce to same speed'
                                          ' not implemented')

            all_points += new_points

        self.new = self.__class__(all_points, b=self.b,
                                  D=self.D, _suc=self.suc)

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

    def _sigma(self, point):
        """Specific speed."""
        phi = self._phi(point)
        psi = self._psi(point)

        sigma = phi**(1/2) / psi**(3/4)

        return sigma

    def _calc_from_non_dimensional(self, point):
        """Calculate dimensional point from non-dimensional.

        Point will be calculated considering the new impeller suction condition.
        """
        new_point = Point(suc=self.suc, eff=point.eff,
                          volume_ratio=point.volume_ratio)

        new_point.phi = point.phi
        new_point.psi = point.psi
        new_point.speed = self._speed_from_psi(new_point)
        new_point.flow_v = self._flow_from_phi(new_point)
        new_point.flow_m = new_point.flow_v * self.suc.rho()
        new_point.power = new_point._power_calc()

        return new_point

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
