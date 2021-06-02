from copy import copy

import numpy as np
import toml
import plotly.graph_objects as go
from scipy.optimize import newton

from .state import State
from ccp.config.units import check_units, Q_
from ccp.config.utilities import r_getattr


class Point:
    """A performance point.
    A point in the compressor map that can be defined in different ways.

    Parameters
    ----------
    speed : pint.Quantity, float
        Speed in rad/s.
    flow_v or flow_m : pint.Quantity, float
        Volumetric (m³/s) or mass (kg/s) flow.
    suc, disch : ccp.State, ccp.State
        Suction and discharge states for the point.
    suc, head, eff : ccp.State, float, float
        Suction state, polytropic head and polytropic efficiency.
    suc, head, power : ccp.State, pint.Quantity or float, pint.Quantity or float
        Suction state, polytropic head (J/kg) and gas power (Watt).
    suc, eff, volume_ratio : ccp.State, float, float
        Suction state, polytropic efficiency and volume ratio.
    b, D : pint.Quantity, float
        Impeller width and diameter.

    Returns
    -------
    Point : ccp.Point
        A point in the compressor map.

    Attributes
    ----------
    suc : ccp.State
        A ccp.State object.
        For more information on attributes and methods available see:
        :py:class:`ccp.State`
    disch : ccp.State
        A ccp.State object.
        For more information on attributes and methods available see:
        :py:class:`ccp.State`
    flow_v : pint.Quantity
        Volumetric flow (m³/s).
    flow_m : pint.Quantity
        Mass flow (kg/s)
    speed : pint.Quantity
        Speed (rad/s).
    head : pint.Quantity
        Polytropic head (J/kg).
    eff : pint.Quantity
        Polytropic efficiency (dimensionless).
    power : pint.Quantity
        Power (Watt).
    phi : pint.Quantity
        Volume flow coefficient (dimensionless).
    psi : pint.Quantity
        Polytropic head coefficient (dimensionless).
    volume_ratio : pint.Quantity
        Volume ratio - suc.v() / disch.v() (dimensionless).
    b : pint.Quantity
        Impeller width (m).
    D : pint.Quantity
        Impeller diameter (m).
    reynolds : pint.Quantity
        Reynolds number (dimensionless).
    mach : pint.Quantity
        Mach number (dimensionless).
    phi_ratio : float
        Ratio between phi for this point and the original point from which it was converted from.
    psi_ratio : float
        Ratio between psi for this point and the original point from which it was converted from.
    reynolds_ratio : float
        Ratio between Reynolds for this point and the original point from which it was converted from.
    mach_diff : float
        Difference between Mach for this point and the original point from which it was converted from.
    volume_ratio_ratio = 1.0
        Ratio between volume_ratio for this point and the original point from which it was converted from.

    """

    @check_units
    def __init__(
        self,
        suc=None,
        disch=None,
        flow_v=None,
        flow_m=None,
        speed=None,
        head=None,
        eff=None,
        power=None,
        phi=None,
        psi=None,
        volume_ratio=None,
        b=None,
        D=None,
    ):
        if b is None or D is None:
            raise ValueError("Arguments b and D must be provided.")

        self.suc = suc
        self.disch = disch
        self.flow_v = flow_v
        self.flow_m = flow_m
        self.speed = speed
        self.head = head
        self.eff = eff
        self.power = power

        self.phi = phi
        self.psi = psi
        self.volume_ratio = volume_ratio

        self.b = b
        self.D = D

        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        kwargs_list = []

        for k in [
            "suc",
            "disch",
            "flow_v",
            "flow_m",
            "speed",
            "head",
            "eff",
            "power",
            "phi",
            "psi",
            "volume_ratio",
        ]:
            if getattr(self, k):
                kwargs_list.append(k)

        kwargs_str = "_".join(sorted(kwargs_list))

        getattr(self, "_calc_from_" + kwargs_str)()

        self.reynolds = reynolds(self.suc, self.speed, self.b, self.D)
        self.mach = mach(self.suc, self.speed, self.D)

        self.phi_ratio = 1.0
        self.psi_ratio = 1.0
        self.reynolds_ratio = 1.0
        # mach in the ptc 10 is compared with Mmt - Mmsp
        self.mach_diff = 0.0
        # ratio between specific volume ratios in original and converted conditions
        self.volume_ratio_ratio = 1.0

        self._add_point_plot()

    def _add_point_plot(self):
        """Add plot to point after point is fully defined."""
        for state in ["suc", "disch"]:
            for attr in ["p", "T", "h", "s", "rho"]:
                plot = plot_func(self, ".".join([state, attr]))
                setattr(getattr(self, state), attr + "_plot", plot)
        for attr in ["head", "eff", "power"]:
            plot = plot_func(self, attr)
            setattr(self, attr + "_plot", plot)

    def __str__(self):
        return (
            f"\nPoint: "
            f"\nVolume flow: {self.flow_v:.2f~P}"
            f"\nHead: {self.head:.2f~P}"
            f"\nEfficiency: {self.eff:.2f~P}"
            f"\nPower: {self.power:.2f~P}"
        )

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if (
                self.suc == other.suc
                and np.allclose(self.speed, other.speed)
                and np.allclose(self.flow_v, other.flow_v)
                and np.allclose(self.head, other.head)
                and np.allclose(self.eff, other.eff)
            ):
                return True

        return False

    def __repr__(self):

        return (
            f"{self.__class__.__name__}(suc={self.suc},"
            f' speed=Q_("{self.speed:.0f~P}"),'
            f' flow_v=Q_("{self.flow_v:.2f~P}"),'
            f' head=Q_("{self.head:.0f~P}"),'
            f' eff=Q_("{self.eff:.3f~P}"))'
        )

    def _calc_from_disch_flow_v_speed_suc(self):
        self.head = head_pol_schultz(self.suc, self.disch)
        self.eff = eff_pol_schultz(self.suc, self.disch)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.flow_m = self.suc.rho() * self.flow_v
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)

    def _calc_from_disch_flow_m_speed_suc(self):
        self.head = head_pol_schultz(self.suc, self.disch)
        self.eff = eff_pol_schultz(self.suc, self.disch)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.flow_v = self.flow_m / self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)

    def _calc_from_eff_phi_psi_suc_volume_ratio(self):
        eff = self.eff
        suc = self.suc
        volume_ratio = self.volume_ratio

        disch_v = suc.v() / volume_ratio
        disch_rho = 1 / disch_v

        # consider first an isentropic compression
        disch = State.define(rho=disch_rho, s=suc.s(), fluid=suc.fluid)

        def update_state(x, update_type):
            if update_type == "pressure":
                disch.update(rho=disch_rho, p=x)
            elif update_type == "temperature":
                disch.update(rho=disch_rho, T=x)
            new_eff = eff_pol_schultz(self.suc, disch)
            if not 0.0 < new_eff < 1.1:
                raise ValueError

            return (new_eff - eff).magnitude

        try:
            newton(update_state, disch.T().magnitude, args=("temperature",), tol=1e-1)
        except ValueError:
            # re-instantiate disch, since update with temperature not converging
            # might break the state
            disch = State.define(rho=disch_rho, s=suc.s(), fluid=suc.fluid)
            newton(update_state, disch.p().magnitude, args=("pressure",), tol=1e-1)

        self.disch = disch
        self.head = head_pol_schultz(suc, disch)
        self.speed = speed_from_psi(self.D, self.head, self.psi)
        self.flow_v = flow_from_phi(self.D, self.phi, self.speed)
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)

    def _calc_from_eff_flow_v_head_speed_suc(self):
        eff = self.eff
        head = self.head
        suc = self.suc
        disch = disch_from_suc_head_eff(suc, head, eff)
        self.disch = disch
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()

    def _calc_from_eff_flow_m_head_speed_suc(self):
        eff = self.eff
        head = self.head
        suc = self.suc
        disch = disch_from_suc_head_eff(suc, head, eff)
        self.disch = disch
        self.flow_v = self.flow_m / self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()

    def _calc_from_eff_phi_psi_speed_suc(self):
        self.head = head_from_psi(self.D, self.psi, self.speed)
        self.disch = disch_from_suc_head_eff(self.suc, self.head, self.eff)
        self.flow_v = flow_from_phi(self.D, self.phi, self.speed)
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.volume_ratio = self.suc.v() / self.disch.v()

    @classmethod
    def convert_from(cls, original_point, suc=None, find="speed"):
        """Convert point from an original point.

        The user must provide 3 of the 4 available arguments. The argument which is not
        provided will be calculated.
        """
        convert_point_options = {
            "speed": dict(
                suc=suc,
                eff=original_point.eff,
                phi=original_point.phi,
                psi=original_point.psi,
                volume_ratio=original_point.volume_ratio,
                b=original_point.b,
                D=original_point.D,
            ),
            "volume_ratio": dict(
                suc=suc,
                eff=original_point.eff,
                phi=original_point.phi,
                psi=original_point.psi,
                speed=original_point.speed,
                b=original_point.b,
                D=original_point.D,
            ),
        }

        converted_point = cls(**convert_point_options[find])
        converted_point.phi_ratio = converted_point.phi / original_point.phi
        converted_point.psi_ratio = converted_point.psi / original_point.psi
        converted_point.volume_ratio_ratio = (
            converted_point.volume_ratio / original_point.volume_ratio
        )
        converted_point.reynolds_ratio = (
            converted_point.reynolds / original_point.reynolds
        )
        converted_point.mach_diff = converted_point.mach - original_point.mach

        return converted_point

    def __getstate__(self):
        attributes = self.__dict__.copy()
        final_attributes = {k: v for k, v in attributes.items() if "plot" not in k}

        return final_attributes

    def __setstate__(self, state):
        self.__dict__ = state
        self._add_point_plot()

    def _dict_to_save(self):
        """Returns a dict that will be saved to a toml file."""
        return dict(
            p=str(self.suc.p()),
            T=str(self.suc.T()),
            fluid=self.suc.fluid,
            speed=str(self.speed),
            flow_v=str(self.flow_v),
            head=str(self.head),
            eff=str(self.eff),
            b=str(self.b),
            D=str(self.D),
        )

    @staticmethod
    def _dict_from_load(dict_parameters):
        """Change dict to format that can be used by load constructor."""
        suc = State.define(
            p=Q_(dict_parameters.pop("p")),
            T=Q_(dict_parameters.pop("T")),
            fluid=dict_parameters.pop("fluid"),
        )

        return dict(suc=suc, **{k: Q_(v) for k, v in dict_parameters.items()})

    def save(self, file_name):
        """Save point to toml file."""
        with open(file_name, mode="w") as f:
            toml.dump(self._dict_to_save(), f)

    @classmethod
    def load(cls, file_name):
        """Load point from toml file."""
        with open(file_name) as f:
            parameters = toml.load(f)

        return cls(**cls._dict_from_load(parameters))


def plot_func(self, attr):
    def inner(*args, plot_kws=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments flow_v_units='...' and
        attr_units='...'.
        """
        fig = kwargs.pop("fig", None)

        if fig is None:
            fig = go.Figure()

        if plot_kws is None:
            plot_kws = {}

        point_attr = r_getattr(self, attr)
        if callable(point_attr):
            point_attr = point_attr()

        flow_v_units = kwargs.get("flow_v_units", self.flow_v.units)
        # Split in '.' for cases such as disch.rho.
        # In this case the user gives rho_units instead of disch.rho_units
        attr_units = kwargs.get(f"{attr.split('.')[-1]}_units", point_attr.units)

        if attr_units is not None:
            point_attr = point_attr.to(attr_units)

        value = getattr(point_attr, "magnitude")
        units = getattr(point_attr, "units")

        flow_v = self.flow_v

        name = kwargs.get(
            "name", f"Flow: {flow_v.to(flow_v_units).m:.2f}, {attr}: {value:.2f}"
        )

        if flow_v_units is not None:
            flow_v = flow_v.to(flow_v_units)

        fig.add_trace(go.Scatter(x=[flow_v], y=[value], name=name, **plot_kws))

        return fig

    return inner


def n_exp(suc, disch):
    """Polytropic exponent.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    n_exp : float
        Polytropic exponent.
    """
    ps = suc.p()
    vs = 1 / suc.rho()
    pd = disch.p()
    vd = 1 / disch.rho()

    return np.log(pd / ps) / np.log(vs / vd)


def head_polytropic(suc, disch):
    """Polytropic head.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_polytropic : pint.Quantity
        Polytropic head (J/kg).
    """

    n = n_exp(suc, disch)

    p2 = disch.p()
    v2 = 1 / disch.rho()
    p1 = suc.p()
    v1 = 1 / suc.rho()

    return (n / (n - 1)) * (p2 * v2 - p1 * v1).to("joule/kilogram")


def eff_polytropic(suc, disch):
    """Polytropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_polytropic : pint.Quantity
        Polytropic head (J/kg).

    """
    wp = head_polytropic(suc, disch)

    dh = disch.h() - suc.h()

    return wp / dh


def head_isentropic(suc, disch):
    """Isentropic head.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_isentropic : pint.Quantity
        Isentropic head.
    """
    # define state to isentropic discharge using dummy state
    disch_s = copy(disch)
    disch_s.update(p=disch.p(), s=suc.s())

    return head_polytropic(suc, disch_s).to("joule/kilogram")


def eff_isentropic(suc, disch):
    """Isentropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_isentropic : pint.Quantity
        Isentropic efficiency.
    """
    ws = head_isentropic(suc, disch)
    dh = disch.h() - suc.h()

    return ws / dh


def f_schultz(suc, disch):
    """Correction factor as per :cite:`schultz1962`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    f_schultz : float
        Schultz polytropic factor.
    """

    # define state to isentropic discharge using dummy state
    disch_s = copy(disch)
    disch_s.update(p=disch.p(), s=suc.s())

    h2s_h1 = disch_s.h() - suc.h()
    h_isen = head_isentropic(suc, disch)

    return h2s_h1 / h_isen


def head_pol_schultz(suc, disch):
    """Polytropic head corrected by the :cite:`schultz1962` factor.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_schultz : pint.Quantity
        Schultz polytropic head (J/kg).
    """

    f = f_schultz(suc, disch)
    head = head_polytropic(suc, disch)

    return f * head


def eff_pol_schultz(suc, disch):
    """Polytropic efficiency as per :cite:`schultz1962`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_schultz : pint.Quantity
        Schultz polytropic efficiency (dimensionless).
    """
    wp = head_pol_schultz(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_mallen_saville(suc, disch):
    """Polytropic head as per :cite:`mallen1977polytropic`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_mallen_saville : pint.Quantity
        Mallen-Saville polytropic polytropic head (J/kg).
    """

    head = (disch.h() - suc.h()) - (disch.s() - suc.s()) * (
        disch.T() - suc.T()
    ) / np.log(disch.T() / suc.T())

    return head


def eff_pol_mallen_saville(suc, disch):
    """Polytropic efficiency as per :cite:`mallen1977polytropic`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_mallen_saville : pint.Quantity
        Mallen-Saville polytropic efficiency (dimensionless).
    """
    wp = head_pol_mallen_saville(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


_ref_H = 0


def head_reference(suc, disch, num_steps=100):
    """Reference head as described by :cite:`huntington1985`.

    It consists of two loops.
    One converges the T1 temperature at each step by evaluating the
    difference between H = vm * delta_p and H = eff * delta_h.
    The other evaluates the efficiency by checking the difference between
    the last T1 to the discharge temperature Td.

    Results are stored at _ref_eff, _ref_H and _ref_n.
    self._ref_n is a list with n_exp at each step for the final converged
    efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_reference : pint.Quantity
       Reference head as described by :cite:`huntington1985`. (J/kg).
    eff_reference : float
        Reference efficiency as described by :cite:`huntington1985` (dimensionless).
    """

    def calc_step_discharge_temp(T1, p1, p0, h0, v0, e):
        s1 = State.define(p=p1, T=T1, fluid=suc.fluid)
        h1 = s1.h()

        vm = (v0 + s1.v()) / 2
        delta_p = Q_(p1 - p0, "Pa")
        H0 = vm * delta_p
        H1 = e * (h1 - h0)

        return (H1 - H0).magnitude

    def calc_eff(e, suc, disch):
        rc = (disch.p().m / suc.p().m) ** (1 / num_steps)
        p_intervals = [suc.p().m]
        p = suc.p().m
        for i in range(num_steps):
            next_p = p * rc
            p = next_p
            p_intervals.append(p)

        T0 = suc.T().magnitude

        global _ref_H

        _ref_H = 0

        for p0, p1 in zip(p_intervals[:-1], p_intervals[1:]):
            s0 = State.define(p=p0, T=T0, fluid=suc.fluid)
            T1 = newton(
                calc_step_discharge_temp, (T0 + 1e-3), args=(p1, p0, s0.h(), s0.v(), e)
            )
            s1 = State.define(p=p1, T=T1, fluid=suc.fluid)
            _ref_H += head_polytropic(s0, s1)

            T0 = T1

        return disch.T().magnitude - T1

    _ref_eff = newton(calc_eff, 0.8, args=(suc, disch))

    return _ref_H, _ref_eff


def f_sandberg_colby(suc, disch):
    """Correction factor as proposed by Sandberg-Colby.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    f_sandberg_colby : pint.Quantity
       Polytropic head correction factor as described by :cite:`sandberg2013limitations` (dimensionless).
    """
    Tm = (suc.T() + disch.T()) / 2
    hd = disch.h()
    hs = suc.h()
    sd = disch.s()
    ss = suc.s()
    n = n_exp(suc, disch)
    pd = disch.p()
    ps = suc.p()
    vd = disch.v()
    vs = suc.v()

    f_sandberg_colby = ((hd - hs) - Tm * (sd - ss)) / (
        (n / (n - 1)) * (pd * vd - ps * vs)
    )

    return f_sandberg_colby.to("dimensionless")


def head_pol_sandberg_colby(suc, disch):
    """Polytropic head corrected by the Sandberg-Colby factor.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_sandberg_colby : pint.Quantity
       Reference head as described by :cite:`sandberg2013limitations` (J/kg).
    """
    f = f_sandberg_colby(suc, disch)
    h = f * head_polytropic(suc, disch)
    return h


def eff_pol_sandberg_colby(suc, disch):
    """Sandberg-Colby polytropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_sandberg_colby: pint.Quantity
        Sandberg-Colby polytropic efficiency (dimensionless).
    """
    wp = head_pol_sandberg_colby(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_huntington(suc, disch):
    """Polytropic head calculated by the 3 point method described by :cite:`huntington1985`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol_huntington : pint.Quantity
       Polytropic head as described by :cite:`huntington1985` (J/kg).
    """
    eff = eff_pol_huntington(suc, disch)
    head = (disch.h() - suc.h()) * eff

    return head


def eff_pol_huntington(suc, disch):
    """Polytropic efficiency calculated by the 3 point method described by :cite:`huntington1985`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol_huntington : pint.Quantity
       Polytropic efficiency as described by :cite:`huntington1985` (dimensionless).
    """
    p1 = suc.p()
    p2 = disch.p()
    s1 = suc.s()
    s2 = disch.s()
    z1 = suc.z()
    z2 = disch.z()
    T1 = suc.T()
    T2 = disch.T()
    p3 = np.sqrt(p1 * p2)

    T3 = np.sqrt(T1 * T2)
    error = 1
    n = 0
    while error > 1e-10:
        state3 = State.define(p=p3, T=T3, fluid=suc.fluid)
        s3 = state3.s()
        z3 = state3.z()
        cp3 = state3.cp()
        b = (z1 + z2 - 2 * z3) / (np.sqrt(p2 / p1) - 1) ** 2
        a = z1 - b
        c = (z2 - a - b * (p2 / p1)) / np.log(p2 / p1)
        s3_ = s1 + (s2 - s1) * (
            (
                ((a / 2) * np.log(p2 / p1))
                + b * (np.sqrt(p2 / p1) - 1)
                + (c / 8) * np.log(p2 / p1) ** 2
            )
            / (
                a * np.log(p2 / p1)
                + b * ((p2 / p1) - 1)
                + (c / 2) * np.log(p2 / p1) ** 2
            )
        )
        T3_new = T3 * np.exp((s3_ - s3) / cp3)
        error = abs(T3_new - T3).m
        T3 = T3_new

        n += 1
        if n == 100:
            raise RecursionError("Maximum number of iterations exceeded.")

    R = suc.gas_constant() / suc.molar_mass()
    inv_e = 1 + (
        ((s2 - s1) / R)
        / (a * np.log(p2 / p1) + b * ((p2 / p1) - 1) + (c / 2) * np.log(p2 / p1) ** 2)
    )
    eff = 1 / inv_e

    return eff


@check_units
def power_calc(flow_m, head, eff):
    """Calculate power.

    Parameters
    ----------
    flow_m : pint.Quantity, float
        Mass flow (kg/s).
    head : pint.Quantity, float
        Head (J/kg).
    eff : pint.Quantity, float
        Efficiency (dimensionless).

    Returns
    -------
    power : pint.Quantity
        Power (watt).
    """
    power = flow_m * head / eff

    return power.to("watt")


@check_units
def u_calc(D, speed):
    """Calculate the impeller tip speed.

    Parameters
    ----------
    D : pint.Quantity, float
        Impeller diameter (m).
    speed : pint.Quantity, float
        Impeller speed (rad/s).

    Returns
    -------
    u_calc : pint.Quantity
        Impeller tip speed (m/s).
    """
    u = speed * D / 2
    return u.to("m/s")


@check_units
def psi(head, speed, D):
    """Polytropic head coefficient.

    Parameters
    ----------
    head : pint.Quantity, float
        Polytropic head (J/kg).
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    D : pint.Quantity, float
        Impeller diameter.

    Returns
    -------
    psi : pint.Quantity
        Polytropic head coefficient (dimensionless).
    """
    u = u_calc(D, speed)
    psi = head / (u ** 2 / 2)
    return psi.to("dimensionless")


@check_units
def u_from_psi(head, psi):
    """Calculate u_calc from non dimensional psi.

    Parameters
    ----------
    head : pint.Quantity, float
        Polytropic head.
    psi : pint.Quantity, float
        Head coefficient.

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = np.sqrt(2 * head / psi)

    return u.to("m/s")


@check_units
def speed_from_psi(D, head, psi):
    """Calculate speed from non dimensional psi.

    Parameters
    ----------
    D : pint.Quantity, float
        Impeller diameter.
    head : pint.Quantity, float
        Polytropic head.
    psi : pint.Quantity, float
        Head coefficient.

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = u_from_psi(head, psi)

    speed = 2 * u / D

    return speed.to("rad/s")


@check_units
def phi(flow_v, speed, D):
    """Flow coefficient."""
    u = u_calc(D, speed)

    phi = flow_v * 4 / (np.pi * D ** 2 * u)

    return phi.to("dimensionless")


@check_units
def flow_from_phi(D, phi, speed):
    """Calculate flow from non dimensional phi.

    Parameters
    ----------
    D : pint.Quantity, float
        Impeller diameter (m).
    phi : pint.Quantity, float
        Flow coefficient (m³/s).
    speed : pint.Quantity, float
        Speed (rad/s).

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = speed * D / 2

    flow_v = phi * (np.pi * D ** 2 * u) / 4

    return flow_v.to("m**3/s")


def head_from_psi(D, psi, speed):
    """Calculate head from non dimensional psi.

    Parameters
    ----------
    D : pint.Quantity, float
        Impeller diameter (m).
    psi : pint.Quantity, float
        Head coefficient.
    speed : pint.Quantity, float
        Speed (rad/s).

    Returns
    -------
    u_calc : pint.Quantity, float
        Impeller tip speed.
    """
    u = speed * D / 2
    head = psi * (u ** 2 / 2)

    return head.to("J/kg")


def disch_from_suc_head_eff(suc, head, eff):
    """Calculate discharge state from suction, head and efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    head : pint.Quantity, float
        Polytropic head (J/kg).
    eff : pint.Quantity, float
        Polytropic efficiency (dimensionless).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    h_disch = head / eff + suc.h()

    #  consider first an isentropic compression
    disch = State.define(h=h_disch, s=suc.s(), fluid=suc.fluid)

    def update_pressure(p):
        disch.update(h=h_disch, p=p)
        new_head = head_pol_schultz(suc, disch)

        return (new_head - head).magnitude

    newton(update_pressure, disch.p().magnitude, tol=1e-1)

    return disch


@check_units
def reynolds(suc, speed, b, D):
    """Calculate the Reynolds number.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    b : pint.Quantity, float
        Impeller width (m).
    D : pint.Quantity, float
        Impeller diameter (m).

    Returns
    -------
    reynolds : pint.Quantity
        Reynolds number (dimensionless).
    """
    u = u_calc(D, speed)
    re = u * b * suc.rho() / suc.viscosity()

    return re.to("dimensionless")


@check_units
def mach(suc, speed, D):
    """Calculate the Mach number.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    D : pint.Quantity, float
        Impeller diameter (m).

    Returns
    -------
    mach : pint.Quantity
        Mach number (dimensionless).
    """
    u = u_calc(D, speed)
    a = suc.speed_sound()
    ma = u / a

    return ma.to("dimensionless")
