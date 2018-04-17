import numpy as np
from copy import copy


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
    def __init__(self, *, speed, **kwargs):
        self.flow_v = kwargs.get('flow_v', None)
        self.flow_m = kwargs.get('flow_m', None)
        if self.flow_v is None and self.flow_m is None:
            raise TypeError("__init__() missing 1 required keyword-only"
                            " argument: 'flow_v' or 'flow_m'.")

        self.suc = kwargs['suc']
        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        if self.flow_m is None:
            self.flow_m = self.flow_v * self.suc.rhomass()
        else:
            self.flow_v = self.flow_m / self.suc.rhomass()

        self.disch = kwargs.get('disch')
        self.head = kwargs.get('head')
        self.eff = kwargs.get('eff')
        self.power = kwargs.get('power')
        self.volume_ratio = kwargs.get('volume_ratio')

        kwargs_keys = '-'.join(sorted(kwargs))

        options = {
            'disch-flow_v-suc': self._calc_from_suc_disch
        }

        options[kwargs_keys]()

    def _calc_from_suc_disch(self):
        self.head = self._head_pol_schultz()
        self.eff = self._eff_pol_schultz()
        self.power = self._power_calc()

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
        disch_s.update(p=disch.p(), s=suc.smass())

        h2s_h1 = disch_s.hmass() - suc.hmass()
        h_isen = self._head_isen()

        return h2s_h1 / h_isen

    def _head_isen(self):
        """Isentropic head."""

        suc = self.suc
        disch = self.disch

        # define state to isentropic discharge using dummy state
        disch_s = self._dummy_state
        disch_s.update(p=disch.p(), s=suc.smass())

        return self._head_pol

    def _head_pol(self):
        """Polytropic head."""

        suc = self.suc
        disch = self.disch

        n = self._n_exp()

        p2 = disch.p()
        v2 = 1 / disch.rhomass()
        p1 = suc.p()
        v1 = 1 / suc.rhomass()

        return (n/(n-1))*(p2*v2 - p1*v1)

    def _n_exp(self):
        """Polytropic exponent."""

        suc = self.suc
        disch = self.disch

        ps = suc.p()
        vs = 1 / suc.rhomass()
        pd = disch.p()
        vd = 1 / disch.rhomass()

        return np.log(pd/ps)/np.log(vs/vd)

    def eff_pol_schultz(self):
        suc = self.suc
        disch = self.disch

        wp = self.head_pol_schultz(suc, disch)
        dh = disch.hmass() - suc.hmass()

        return wp/dh
