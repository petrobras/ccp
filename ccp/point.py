import numpy as np
import matplotlib.pyplot as plt
from copy import copy
from scipy.optimize import newton
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool
from ccp.config.utilities import r_getattr
from ccp.config.units import change_data_units
from ccp import check_units, State


def plot_func(self, attr):
    def inner(*args, plot_kws=None, **kwargs):
        """Plot parameter versus volumetric flow.

        You can choose units with the arguments x_units='...' and
        y_units='...'.
        """
        ax = kwargs.pop('ax', None)

        if ax is None:
            ax = plt.gca()

        if plot_kws is None:
            plot_kws = {}

        x_units = kwargs.get('x_units', None)
        y_units = kwargs.get('y_units', None)

        point_attr = r_getattr(self, attr)
        if callable(point_attr):
            point_attr = point_attr()

        if y_units is not None:
            point_attr = point_attr.to(y_units)

        value = (getattr(point_attr, 'magnitude'))
        units = getattr(point_attr, 'units')

        flow_v = self.flow_v

        if x_units is not None:
            flow_v = flow_v.to(x_units)

        ax.scatter(flow_v, value, **plot_kws)
        #  vertical and horizontal lines
        ax.plot([flow_v.magnitude, flow_v.magnitude],
                [0, value], ls='--', color='k', alpha=0.2)
        ax.plot([0, flow_v.magnitude],
                [value, value], ls='--', color='k', alpha=0.2)

        ax.set_xlabel(f'Volumetric flow ({flow_v.units:P~})')
        ax.set_ylabel(f'{attr} ({units:P~})')

        return ax

    return inner


def bokeh_source_func(point, attr):
    def inner(*args, **kwargs):
        """Return source data for bokeh plots."""
        x_units = kwargs.get('x_units', None)
        y_units = kwargs.get('y_units', None)
        x_data = point.flow_v
        y_data = r_getattr(point, attr)
        if callable(y_data):
            y_data = y_data()

        x_data, y_data = change_data_units(x_data, y_data, x_units, y_units)

        source = ColumnDataSource(data=dict(x=[x_data.magnitude],
                                            y=[y_data.magnitude],
                                            x_units=[f'{x_data.units:~P}'],
                                            y_units=[f'{y_data.units:~P}']))

        return source
    return inner


def bokeh_plot_func(point, attr):
    def inner(*args, fig=None, source=None, plot_kws=None, **kwargs):
        if plot_kws is None:
            plot_kws = {}

        plot_kws.setdefault('color', 'navy')
        plot_kws.setdefault('size', 8)
        plot_kws.setdefault('alpha', 0.5)
        plot_kws.setdefault('name', 'point')

        if source is None:
            source = r_getattr(point, attr + '_bokeh_source')(*args, **kwargs)

        fig.circle('x', 'y', source=source, **plot_kws)
        x_units_str = source.data["x_units"][0]
        y_units_str = source.data["y_units"][0]
        fig.xaxis.axis_label = f'Flow ({x_units_str})'
        fig.yaxis.axis_label = f'{attr} ({y_units_str})'

        fig.add_tools(HoverTool(
            names=['point'],
            tooltips=[
                ('Flow', f'@x ({x_units_str})'),
                ('Efficiency', f'@y ({y_units_str})')
            ]))

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

        self.suc = kwargs['suc']
        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        if self.flow_v is not None:
            self.flow_m = self.flow_v * self.suc.rho()
        elif self.flow_m is not None:
            self.flow_v = self.flow_m / self.suc.rho()

        self.disch = kwargs.get('disch')
        self.head = kwargs.get('head')
        self.eff = kwargs.get('eff')
        self.power = kwargs.get('power')
        self.volume_ratio = kwargs.get('volume_ratio')
        self.speed = kwargs.get('speed')

        # non dimensional parameters will be added when the point is associated
        # to an impeller (when the impeller object is instantiated)
        self.phi = None
        self.psi = None

        kwargs_keys = [k for k in kwargs.keys()
                       if k not in ['flow_v', 'flow_m', 'speed']]
        kwargs_keys = '-'.join(sorted(kwargs_keys))

        calc_options = {
            'disch-suc': self._calc_from_disch_suc,
            'eff-suc-volume_ratio': self._calc_from_eff_suc_volume_ratio,
            'eff-head-suc': self._calc_from_eff_head_suc
        }

        calc_options[kwargs_keys]()
        self._add_point_plot()

    def _add_point_plot(self):
        """Add plot to point after point is fully defined."""
        for state in ['suc', 'disch']:
            for attr in ['p', 'T']:
                plot = plot_func(self, '.'.join([state, attr]))
                setattr(getattr(self, state), attr + '_plot', plot)
                bokeh_source = bokeh_source_func(self, '.'.join([state, attr]))
                setattr(getattr(self, state), attr + '_bokeh_source', bokeh_source)
                bokeh_plot = bokeh_plot_func(self, '.'.join([state, attr]))
                setattr(getattr(self, state), attr + '_bokeh_plot', bokeh_plot)
        for attr in ['head', 'eff', 'power']:
                plot = plot_func(self, attr)
                setattr(self, attr + '_plot', plot)
                bokeh_source = bokeh_source_func(self, attr)
                setattr(self, attr + '_bokeh_plot', bokeh_source)
                bokeh_plot = bokeh_plot_func(self, attr)
                setattr(self, attr + '_bokeh_plot', bokeh_plot)

    def __repr__(self):
        return (
                '\nPoint: '
                + '\n Volume flow: {:10.5}'.format(self.flow_v)
                + '\n Head       : {:10.5}'.format(self.head)
                + '\n Efficiency : {:10.5}'.format(self.eff)
                + '\n Power      : {:10.5}'.format(self.power)
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

        def update_pressure(p):
            disch.update(rho=disch_rho, p=p)
            new_eff = self._eff_pol_schultz(disch=disch)

            return (new_eff - eff).magnitude

        newton(update_pressure, disch.p().magnitude, tol=1e-1)

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

    def _eff_pol_schultz(self, disch=None):
        """Schultz polytropic efficiency."""
        suc = self.suc
        if disch is None:
            disch = self.disch

        wp = self._head_pol_schultz(disch=disch)
        dh = disch.h() - suc.h()

        return wp/dh

    def _power_calc(self):
        """Power."""
        flow_m = self.flow_m
        head = self.head
        eff = self.eff

        return (flow_m * head / eff).to('watt')

    def _volume_ratio(self):
        suc = self.suc
        disch = self.disch

        vs = 1 / suc.rho()
        vd = 1 / disch.rho()

        return vd / vs



