from copy import copy
from warnings import warn

import matplotlib.pyplot as plt
import numpy as np
import toml
import plotly.graph_objects as go
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool
from scipy.optimize import newton

from ccp import check_units, State, Q_
from ccp.config.units import change_data_units
from ccp.config.utilities import r_getattr


def plot_func(self, attr):
    def inner(*args, plot_kws=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments x_units='...' and
        y_units='...'.
        """
        fig = kwargs.pop("fig", None)

        if fig is None:
            fig = go.Figure()

        if plot_kws is None:
            plot_kws = {}

        x_units = kwargs.get("flow_v_units", None)
        y_units = kwargs.get(f"{attr}_units", None)
        name = kwargs.get("name", None)

        point_attr = r_getattr(self, attr)
        if callable(point_attr):
            point_attr = point_attr()

        if y_units is not None:
            point_attr = point_attr.to(y_units)

        value = getattr(point_attr, "magnitude")
        units = getattr(point_attr, "units")

        flow_v = self.flow_v

        if x_units is not None:
            flow_v = flow_v.to(x_units)

        fig.add_trace(go.Scatter(x=[flow_v], y=[value], name=name, **plot_kws))

        return fig

    return inner


def _bokeh_source_func(point, attr):
    def inner(*args, **kwargs):
        """Return source data for bokeh plots."""
        x_units = kwargs.get("x_units", None)
        y_units = kwargs.get("y_units", None)
        x_data = point.flow_v
        y_data = r_getattr(point, attr)

        flow_m = point.flow_v * point.suc.rho()

        if callable(y_data):
            y_data = y_data()

        x_data, y_data = change_data_units(x_data, y_data, x_units, y_units)

        source = ColumnDataSource(
            data=dict(
                x=[x_data.magnitude],
                y=[y_data.magnitude],
                flow_m=[flow_m.magnitude],
                x_units=[f"{x_data.units:~P}"],
                y_units=[f"{y_data.units:~P}"],
                flow_m_units=[f"{flow_m.units:~P}"],
            )
        )

        return source

    return inner


def _bokeh_plot_func(point, attr):
    def inner(*args, fig=None, source=None, plot_kws=None, **kwargs):
        if plot_kws is None:
            plot_kws = {}

        plot_kws.setdefault("color", "navy")
        plot_kws.setdefault("size", 8)
        plot_kws.setdefault("alpha", 0.5)
        plot_kws.setdefault("name", "point")

        if source is None:
            source = r_getattr(point, attr + "_bokeh_source")(*args, **kwargs)

        fig.circle("x", "y", source=source, **plot_kws)
        x_units_str = source.data["x_units"][0]
        y_units_str = source.data["y_units"][0]
        flow_m_units_str = source.data["flow_m_units"][0]
        fig.xaxis.axis_label = f"Flow ({x_units_str})"
        fig.yaxis.axis_label = f"{attr} ({y_units_str})"

        fig.add_tools(
            HoverTool(
                names=["point"],
                tooltips=[
                    ("Flow", f"@x ({x_units_str})"),
                    ("Mass Flow", f"@flow_m ({flow_m_units_str})"),
                    (f"{attr}", f"@y ({y_units_str})"),
                ],
            )
        )

        return fig

    return inner


class Point:
    """Point.
    A point in the compressor map that can be defined in different ways.

    Parameters
    ----------
    speed : float
        Speed in 1/s.
    flow_v or flow_m : float
        Volumetric or mass flow.
    suc, disch : ccp.State, ccp.State
        Suction and discharge states for the point.
    suc, head, eff : ccp.State, float, float
        Suction state, polytropic head and polytropic efficiency.
    suc, head, power : ccp.State, float, float
        Suction state, polytropic head and gas power.
    suc, eff, vol_ratio : ccp.State, float, float
        Suction state, polytropic efficiency and volume ratio.

    Returns
    -------
    Point : ccp.Point
        A point in the compressor map.
    """

    @check_units
    def __init__(self, *args, **kwargs):
        self.flow_v = kwargs.get("flow_v", None)
        self.flow_m = kwargs.get("flow_m", None)
        self.volume_ratio = kwargs.get("volume_ratio")
        if not (self.flow_m or self.flow_v or self.volume_ratio):
            raise ValueError("flow_v, flow_m or volume_ratio must be provided.")

        self.suc = kwargs["suc"]
        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        if self.flow_v is not None:
            self.flow_m = self.flow_v * self.suc.rho()
        elif self.flow_m is not None:
            self.flow_v = self.flow_m / self.suc.rho()

        self.disch = kwargs.get("disch")
        self.head = kwargs.get("head")
        self.eff = kwargs.get("eff")
        self.power = kwargs.get("power")
        self.speed = kwargs.get("speed")

        # check if some values are within a reasonable range
        try:
            if self.speed.m > 5000:
                warn(f'Speed seems to high: {self.speed} - {self.speed.to("RPM")}')
        except AttributeError:
            pass

        # non dimensional parameters will be added when the point is associated
        # to an impeller (when the impeller object is instantiated)
        self.phi = None
        self.psi = None
        self.mach = None
        self.reynolds = None

        kwargs_keys = [
            k for k in kwargs.keys() if k not in ["flow_v", "flow_m", "speed"]
        ]
        kwargs_keys = "-".join(sorted(kwargs_keys))

        calc_options = {
            "disch-suc": self._calc_from_disch_suc,
            "eff-suc-volume_ratio": self._calc_from_eff_suc_volume_ratio,
            "eff-head-suc": self._calc_from_eff_head_suc,
        }

        calc_options[kwargs_keys]()
        self._add_point_plot()

    def _add_point_plot(self):
        """Add plot to point after point is fully defined."""
        for state in ["suc", "disch"]:
            for attr in ["p", "T"]:
                plot = plot_func(self, ".".join([state, attr]))
                setattr(getattr(self, state), attr + "_plot", plot)
                bokeh_source = _bokeh_source_func(self, ".".join([state, attr]))
                setattr(getattr(self, state), attr + "_bokeh_source", bokeh_source)
                bokeh_plot = _bokeh_plot_func(self, ".".join([state, attr]))
                setattr(getattr(self, state), attr + "_bokeh_plot", bokeh_plot)
        for attr in ["head", "eff", "power"]:
            plot = plot_func(self, attr)
            setattr(self, attr + "_plot", plot)
            bokeh_source = _bokeh_source_func(self, attr)
            setattr(self, attr + "_bokeh_source", bokeh_source)
            bokeh_plot = _bokeh_plot_func(self, attr)
            setattr(self, attr + "_bokeh_plot", bokeh_plot)

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

    def _calc_from_disch_suc(self):
        self.head = self._head_pol_schultz()
        self.eff = self._eff_pol_schultz()
        self.volume_ratio = self._volume_ratio()
        self.power = self._power_calc()

    def _calc_from_eff_suc_volume_ratio(self):
        eff = self.eff
        suc = self.suc
        volume_ratio = self.volume_ratio

        disch_rho = suc.rho() / volume_ratio

        #  consider first an isentropic compression
        disch = State.define(rho=disch_rho, s=suc.s(), fluid=suc.fluid)

        def update_state(x, update_type):
            if update_type == "pressure":
                disch.update(rho=disch_rho, p=x)
            elif update_type == "temperature":
                disch.update(rho=disch_rho, T=x)
            new_eff = self._eff_pol_schultz(disch=disch)
            if not 0. < new_eff < 1.1:
                raise ValueError

            return (new_eff - eff).magnitude

        try:
            newton(update_state, disch.T().magnitude, args=("temperature",),
                   tol=1e-1)
        except ValueError:
            # re-instantiate disch, since update with temperature not converging
            # might break the state
            disch = State.define(rho=disch_rho, s=suc.s(), fluid=suc.fluid)
            newton(update_state, disch.p().magnitude, args=("pressure",),
                   tol=1e-1)

        self.disch = disch
        self.head = self._head_pol_schultz()

    def _calc_from_eff_head_suc(self):
        eff = self.eff
        head = self.head
        suc = self.suc

        h_disch = head / eff + suc.h()

        #  consider first an isentropic compression
        disch = State.define(h=h_disch, s=suc.s(), fluid=suc.fluid)

        def update_pressure(p):
            disch.update(h=h_disch, p=p)
            new_head = self._head_pol_schultz(disch)

            return (new_head - head).magnitude

        newton(update_pressure, disch.p().magnitude, tol=1e-1)

        self.disch = disch
        self.volume_ratio = self._volume_ratio()
        self.power = self._power_calc()

    def _head_pol_schultz(self, disch=None):
        """Polytropic head corrected by the Schultz factor."""
        if disch is None:
            disch = self.disch

        f = self._schultz_f(disch=disch)
        head = self._head_pol(disch=disch)

        return f * head

    def _head_pol_mallen_saville(self, disch=None):
        """Polytropic head as per Mallen-Saville"""
        if disch is None:
            disch = self.disch

        suc = self.suc

        head = (disch.h() - suc.h()) - (disch.s() - suc.s()) * (
            disch.T() - suc.T()
        ) / np.log(disch.T() / suc.T())

        return head

    def _head_reference(self, disch=None):
        """Reference head as described by Huntington (1985).

        It consists of two loops.
        One converges the T1 temperature at each step by evaluating the
        diffence between H = vm * delta_p and H = eff * delta_h.
        The other evaluates the efficiency by checking the difference between
        the last T1 to the discharge temperature Td.

        Results are stored at self._ref_eff, self._ref_H and self._ref_n.
        self._ref_n is a list with n_exp at each step for the final converged
        efficiency.

        """
        if disch is None:
            disch = self.disch

        suc = self.suc

        def calc_step_discharge_temp(T1, T0, self, p1, e):
            s0 = State.define(p=self, T=T0, fluid=suc.fluid)
            s1 = State.define(p=p1, T=T1, fluid=suc.fluid)
            h0 = s0.h()
            h1 = s1.h()

            vm = ((1 / s0.rho()) + (1 / s1.rho())) / 2
            delta_p = Q_(p1 - self, "Pa")
            H0 = vm * delta_p
            H1 = e * (h1 - h0)

            return (H1 - H0).magnitude

        def calc_eff(e, suc, disch):
            p_intervals = np.linspace(suc.p(), disch.p(), 1000)

            T0 = suc.T().magnitude

            self._ref_H = 0
            self._ref_n = []

            for self, p1 in zip(p_intervals[:-1], p_intervals[1:]):
                T1 = newton(
                    calc_step_discharge_temp, (T0 + 1e-3), args=(T0, self, p1, e)
                )

                s0 = State.define(p=self, T=T0, fluid=suc.fluid)
                s1 = State.define(p=p1, T=T1, fluid=suc.fluid)
                step_point = Point(flow_m=1, speed=1, suc=s0, disch=s1)

                self._ref_H += step_point._head_pol()
                self._ref_n.append(step_point._n_exp())
                T0 = T1

            return disch.T().magnitude - T1

        self._ref_eff = newton(calc_eff, 0.8, args=(suc, disch))

    def _schultz_f(self, disch=None):
        """Schultz factor."""
        suc = self.suc
        if disch is None:
            disch = self.disch

        # define state to isentropic discharge using dummy state
        disch_s = self._dummy_state
        disch_s.update(p=disch.p(), s=suc.s())

        h2s_h1 = disch_s.h() - suc.h()
        h_isen = self._head_isen(disch=disch)

        return h2s_h1 / h_isen

    def _head_isen(self, disch=None):
        """Isentropic head."""
        suc = self.suc
        if disch is None:
            disch = self.disch

        # define state to isentropic discharge using dummy state
        disch_s = self._dummy_state
        disch_s.update(p=disch.p(), s=suc.s())

        return self._head_pol(disch=disch_s).to("joule/kilogram")

    def _eff_isen(self):
        """Isentropic efficiency."""
        suc = self.suc
        disch = self.disch

        ws = self._head_isen()
        dh = disch.h() - suc.h()
        return ws / dh

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

        return (n / (n - 1)) * (p2 * v2 - p1 * v1).to("joule/kilogram")

    def _eff_pol(self):
        """Polytropic efficiency."""
        suc = self.suc
        disch = self.disch

        wp = self._head_pol()

        dh = disch.h() - suc.h()

        return wp / dh

    def _n_exp(self, disch=None):
        """Polytropic exponent."""
        suc = self.suc

        if disch is None:
            disch = self.disch

        ps = suc.p()
        vs = 1 / suc.rho()
        pd = disch.p()
        vd = 1 / disch.rho()

        return np.log(pd / ps) / np.log(vs / vd)

    def _eff_pol_schultz(self, disch=None):
        """Schultz polytropic efficiency."""
        suc = self.suc
        if disch is None:
            disch = self.disch

        wp = self._head_pol_schultz(disch=disch)
        dh = disch.h() - suc.h()

        return wp / dh

    def _power_calc(self):
        """Power."""
        flow_m = self.flow_m
        head = self.head
        eff = self.eff

        return (flow_m * head / eff).to("watt")

    def _volume_ratio(self):
        suc = self.suc
        disch = self.disch

        vs = 1 / suc.rho()
        vd = 1 / disch.rho()

        return vd / vs

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
