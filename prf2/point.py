import numpy as np
from copy import copy
from prf2 import check_units


class Point:
    """Point.
    A point in the compressor map that can be defined in different ways.

    Parameters
    ----------
    speed : float
        Speed in 1/s.
    flow_v or flow_m : float
        Volumetric or mass flow.
    suc, disch : prf.State, prf.State
        Suction and discharge states for the point.
    suc, head, eff : prf.State, float, float
        Suction state, polytropic head and polytropic efficiency.
    suc, head, power : prf.State, float, float
        Suction state, polytropic head and gas power.
    suc, eff, vol_ratio : prf.State, float, float
        Suction state, polytropic efficiency and volume ratio.

    Returns
    -------
    Point : prf.Point
        A point in the compressor map.
    """
    @check_units
    def __init__(self, *args, **kwargs):
        self.flow_v = kwargs.get('flow_v', None)
        self.flow_m = kwargs.get('flow_m', None)
        if self.flow_v is None and self.flow_m is None:
            raise TypeError("__init__() missing 1 required keyword-only"
                            " argument: 'flow_v' or 'flow_m'.")

        self.suc = kwargs['suc']
        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        if self.flow_m is None:
            self.flow_m = self.flow_v * self.suc.rho()
        else:
            self.flow_v = self.flow_m / self.suc.rho()

        self.disch = kwargs.get('disch')
        self.head = kwargs.get('head')
        self.eff = kwargs.get('eff')
        self.power = kwargs.get('power')
        self.volume_ratio = kwargs.get('volume_ratio')
        self.speed = kwargs.get('speed')

        kwargs_keys = [k for k in kwargs.keys()
                       if k not in ['flow_v', 'flow_m']]
        kwargs_keys = '-'.join(sorted(kwargs_keys))

        options = {
            'disch-speed-suc': self._calc_from_disch_suc,
            'eff-suc-volume_ratio': self._calc_from_eff_suc_volume_ratio,
        }

        options[kwargs_keys]()

        #  non_dimensional point will be set on impeller instantiation
        self.non_dimensional_point = None

    def _calc_from_disch_suc(self):
        self.head = self._head_pol_schultz()
        self.eff = self._eff_pol_schultz()
        self.volume_ratio = self._volume_ratio()
        self.power = self._power_calc()

    def _calc_from_eff_suc_volume_ratio(self):
        pass

    def _head_pol_schultz(self):
        """Polytropic head corrected by the Schultz factor."""
        f = self._schultz_f()
        head = self._head_pol()

        return f * head

    def _schultz_f(self):
        """Schultz factor."""
        suc = self.suc
        disch = self.disch

        # define state to isentropic discharge using dummy state
        disch_s = self._dummy_state
        disch_s.update(p=disch.p(), s=suc.s())

        h2s_h1 = disch_s.h() - suc.h()
        h_isen = self._head_isen()

        return h2s_h1 / h_isen

    def _head_isen(self):
        """Isentropic head."""
        suc = self.suc
        disch = self.disch

        # define state to isentropic discharge using dummy state
        disch_s = self._dummy_state
        disch_s.update(p=disch.p(), s=suc.s())

        return self._head_pol(disch=disch_s).to('joule/kilogram')

    def _eff_isen(self):
        """Isentropic efficiency."""
        suc = self.suc
        disch = self.disch

        ws = self._head_isen()
        dh = disch.h() - suc.h()
        return ws/dh

    def _head_pol(self, disch=None):
        """Polytropic head."""
        suc = self.suc

        if disch is None:
            disch = self.disch

        n = self._n_exp(disch=disch)

        p2 = disch.p()
        v2 = 1 / disch.rho()
        p1 = suc.p()
        v1 = 1 / suc.rho()

        return (n/(n-1))*(p2*v2 - p1*v1).to('joule/kilogram')

    def _eff_pol(self):
        """Polytropic efficiency."""
        suc = self.suc
        disch = self.disch

        wp = self._head_pol()

        dh = disch.h() - suc.h()

        return wp/dh

    def _n_exp(self, disch=None):
        """Polytropic exponent."""
        suc = self.suc

        if disch is None:
            disch = self.disch

        ps = suc.p()
        vs = 1 / suc.rho()
        pd = disch.p()
        vd = 1 / disch.rho()

        return np.log(pd/ps)/np.log(vs/vd)

    def _eff_pol_schultz(self):
        """Schultz polytropic efficiency."""
        suc = self.suc
        disch = self.disch

        wp = self._head_pol_schultz()
        dh = disch.h() - suc.h()

        return wp/dh

    def _power_calc(self):
        """Power."""
        flow_m = self.flow_m
        head = self.head
        eff = self.eff

        return (flow_m * head / eff).to('kilowatt')

    def _volume_ratio(self):
        suc = self.suc
        disch = self.disch

        vs = 1 / suc.rho()
        vd = 1 / disch.rho()

        return vd / vs


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
    def __init__(self, phi, psi, eff, volume_ratio, mach, reynolds):

        self.phi = phi
        self.psi = psi
        self.eff = eff
        self.volume_ratio = volume_ratio
        self.mach = mach
        self.reynolds = reynolds
