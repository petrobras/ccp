"""Module to define impeller class."""
import numpy as np
import matplotlib.pyplot as plt
import csv
from scipy.interpolate import interp1d
from copy import deepcopy
from itertools import groupby
from warnings import warn
from pathlib import Path
from openpyxl import Workbook
from bokeh.models import ColumnDataSource
from ccp.config.utilities import r_getattr, r_setattr
from ccp.data_io.read_csv import read_data_from_engauge_csv
from ccp import Q_, check_units, State, Point, Curve


class ImpellerState:
    def __init__(self, curves_state):
        self.curves_state = curves_state

        for attr in ['p', 'T']:
            func = self.state_parameter(attr)
            setattr(self, attr, func)

    def state_parameter(self, attr):
        def inner(*args, **kwargs):
            values = []

            for curve_state in self:
                values.append(getattr(getattr(curve_state, attr)(), 'magnitude'))

            units = getattr(getattr(curve_state, attr)(), 'units')

            return Q_(values, units)

        return inner

    def __getitem__(self, item):
        return self.curves_state.__getitem__(item)


class Impeller:
    """Impeller class.

    Impeller instance is initialized with the list of points.
    The created instance will hold the dimensional points used in instantiation
    non dimensional points generated from the given dimensional points and
    another list of dimensional points based on current suction condition.
    Curves will be generated from points close in similarity.

    """
    @check_units
    def __init__(self, points, b=None, D=None,
                 _suc=None, _flow_v=None, _speed=None):
        self.b = b
        self.D = D
        if not (self.b and self.D):
            raise ValueError('Width(b) and diameter(D) must be provided.')

        self.points = deepcopy(points)
        # TODO group points with the same speed in curves

        for p in self.points:
            self._add_non_dimensional_attributes(p)
            p._add_point_plot()

        curves = []
        for speed, grouped_points in groupby(
                sorted(self.points, key=lambda point: point.speed),
                key=lambda point: point.speed):
            points = [point for point in grouped_points]
            curve = Curve(points)
            curves.append(curve)
            setattr(self, f'curve_{int(curve.speed.magnitude)}', curve)
        self.curves = curves
        self.disch = ImpellerState([c.disch for c in self.curves])

        for attr in ['disch.p', 'disch.T', 'head', 'eff', 'power']:
            values = []
            # for disch.p etc values are defined in _Impeller_State
            if '.' not in attr:
                for c in self.curves:
                    param = r_getattr(c, attr)
                    values.append(param.magnitude)
                units = param.units
                r_setattr(self, attr, Q_(values, units))

            r_setattr(self, attr + '_plot', self.plot_func(attr))
            r_setattr(self, attr + '_bokeh_source',
                      self._bokeh_source_func(attr))
            r_setattr(self, attr + '_bokeh_plot', self._bokeh_plot_func(attr))

        self._suc = _suc
        self._speed = _speed
        self._flow_v = _flow_v

        self.current_curve = None
        self.current_point = None

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def _add_non_dimensional_attributes(self, point):
        additional_point_attributes = ['phi', 'psi', 'mach', 'reynolds']
        for attr in additional_point_attributes:
            setattr(point, attr, getattr(self, '_' + attr)(point))

    def plot_func(self, attr):
        def inner(*args, plot_kws=None, **kwargs):
            ax = kwargs.pop('ax', None)

            if ax is None:
                ax = plt.gca()

            if plot_kws is None:
                plot_kws = {}

            x_units = kwargs.get('x_units', None)
            y_units = kwargs.get('y_units', None)

            flow_values = [p.flow_v for p in self.points]
            min_flow = min(flow_values)
            max_flow = max(flow_values)
            if callable(r_getattr(self.points[0], attr)):
                values = [r_getattr(p, attr)() for p in self.points]
            else:
                values = [r_getattr(p, attr) for p in self.points]
            min_value = min(values)
            max_value = max(values)

            if x_units is not None:
                min_flow = min_flow.to(x_units)
                max_flow = max_flow.to(x_units)
            if y_units is not None:
                min_value = min_value.to(y_units)
                max_value = max_value.to(y_units)

            ax.set_xlim(0.8 * min_flow.magnitude, 1.1 * max_flow.magnitude)
            ax.set_ylim(0.5 * min_value.magnitude, 1.1 * max_value.magnitude)

            for curve in self.curves:
                ax = r_getattr(curve, attr + '_plot')(
                    ax=ax, plot_kws=plot_kws, **kwargs)

            try:
                ax = r_getattr(self.current_curve, attr + '_plot')(
                    ax=ax, plot_kws=plot_kws, **kwargs)
                ax = r_getattr(self.current_point, attr + '_plot')(
                    ax=ax, plot_kws=plot_kws, **kwargs)
            except AttributeError:
                warn('Point not set for this impeller')

            return ax

        inner.__doc__ = r_getattr(self.curves[0], attr + '_plot').__doc__

        return inner

    def _bokeh_source_func(self, attr):
        def inner(*args, fig=None, plot_kws=None, **kwargs):
            sources = []

            for curve in self.curves:
                source = r_getattr(curve, attr + '_bokeh_source')(*args, **kwargs)
                sources.append(source)

            return sources
        return inner

    def _bokeh_plot_func(self, attr):
        def inner(*args, fig=None, source=None, plot_kws=None, **kwargs):
            if source is None:
                for curve in self.curves:
                        fig = r_getattr(curve, attr + '_bokeh_plot')(
                                        fig=fig, plot_kws=plot_kws, **kwargs)
            else:
                for s, curve in zip(source, self.curves):
                    fig = r_getattr(curve, attr + '_bokeh_plot')(
                        fig=fig, source=s, plot_kws=plot_kws, **kwargs)
            return fig
        return inner

    @property
    def suc(self):
        return self._suc

    @suc.setter
    def suc(self, new_suc):
        self._suc = new_suc
        self._calc_new_points()
        try:
            self._calc_current_point()
        except (AttributeError, TypeError):
            warn('Current point not set (flow and speed)')

    @property
    def speed(self):
        return self._speed

    @speed.setter
    @check_units
    def speed(self, speed):
        if speed.magnitude > 5000:
            warn(f'Speed seems to high: {self.speed} - {self.speed.to("RPM")}')
        self._speed = speed
        if self.flow_v is None:
            return

        if len(self.curves) < 2:
            raise NotImplementedError(
                'Not implemented for less them two curves.')

        self._calc_current_point()

    @property
    def flow_v(self):
        #  TODO check if flow_v is within reasonable range
        return self._flow_v

    @flow_v.setter
    @check_units
    def flow_v(self, flow_v):
        min_flow = min([p.flow_v.m for p in self.points])
        max_flow = max([p.flow_v.m for p in self.points])
        if not min_flow < flow_v.m < max_flow:
            warn(f'Flow outside the flow range '
                 f'min: {min_flow} max: {max_flow}')
        self._flow_v = flow_v
        if self.speed is None:
            return

        self._calc_current_point()

    @staticmethod
    def _find_closest_speeds(array, value):
        diff = array - value
        idx = np.abs(diff).argmin()

        if idx == 0:
            return [0, 1]
        elif idx == len(array) - 1:
            return [len(array) - 2, len(array) - 1]

        if diff[idx] > 0:
            idx = [idx - 1, idx]
        else:
            idx = [idx, idx + 1]

        return np.array(idx)

    def _calc_current_point(self):
        #  TODO refactor this function
        try:
            speeds = np.array([curve.speed.magnitude for curve in self.curves])
        except AttributeError:
            return

        closest_curves_idxs = self._find_closest_speeds(
                speeds, self.speed.magnitude)
        curves = list(np.array(self.curves)[closest_curves_idxs])

        # calculate factor
        speed_range = curves[1].speed.magnitude - curves[0].speed.magnitude
        factor = (self.speed.magnitude - curves[0].speed.magnitude) / speed_range

        def get_interpolated_value(fac, val_0, val_1):
            return (1 - fac) * val_0 + fac * val_1

        min_flow = get_interpolated_value(
            factor, curves[0].flow_v.magnitude[0], curves[1].flow_v.magnitude[0])
        max_flow = get_interpolated_value(
            factor, curves[0].flow_v.magnitude[-1], curves[1].flow_v.magnitude[-1])

        flow_v = np.linspace(min_flow, max_flow, 6)

        disch_T_0 = curves[0].disch.T_interpolated(flow_v).magnitude
        disch_T_1 = curves[1].disch.T_interpolated(flow_v).magnitude
        disch_p_0 = curves[0].disch.p_interpolated(flow_v).magnitude
        disch_p_1 = curves[1].disch.p_interpolated(flow_v).magnitude

        disch_T = get_interpolated_value(factor, disch_T_0, disch_T_1)
        disch_p = get_interpolated_value(factor, disch_p_0, disch_p_1)
        points_current = []

        for f, p, T in zip(flow_v, disch_p, disch_T):
            disch = State.define(p=p, T=T, fluid=self.suc.fluid)
            points_current.append(
                Point(flow_v=f, speed=self.speed, suc=self.suc, disch=disch))

        self.current_curve = Curve(points_current)

        disch_T_0 = curves[0].disch.T_interpolated(self.flow_v).magnitude
        disch_T_1 = curves[1].disch.T_interpolated(self.flow_v).magnitude
        disch_p_0 = curves[0].disch.p_interpolated(self.flow_v).magnitude
        disch_p_1 = curves[1].disch.p_interpolated(self.flow_v).magnitude

        disch_T = get_interpolated_value(factor, disch_T_0, disch_T_1)
        disch_p = get_interpolated_value(factor, disch_p_0, disch_p_1)
        current_disch = State.define(p=disch_p, T=disch_T, fluid=self.suc.fluid)
        self.current_point = Point(flow_v=self.flow_v, speed=self.speed,
                                   suc=self.suc, disch=current_disch)

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

            if speed_std < 10:
                for p in new_points:
                    p.speed = Q_(speed_mean, p.speed.units)
            else:
                raise NotImplementedError('Coerce to same speed'
                                          ' not implemented')

            all_points += new_points

        self.new = self.__class__(all_points, b=self.b, D=self.D,
                                  _suc=self.suc, _flow_v=self.flow_v,
                                  _speed=self.speed)

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

        Point will be calculated considering new impeller suction condition.
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

    def export_to_excel(self, path_name=None):
        """Export curves to excel file."""
        wb = Workbook()
        for curve in self.curves:
            sheet_name = f'{curve.speed.to("RPM"):.0f~P}'
            ws = wb.create_sheet(sheet_name)
            for i, p in enumerate(curve):
                i += 1  # openpyxl index
                if i == 1:
                    ws.cell(row=i, column=1, value='Flow (m**3/s)')
                    ws.cell(row=i, column=2, value='Head (kJ/kg)')
                    ws.cell(row=i, column=3, value='Efficiency (%)')
                else:
                    ws.cell(row=i, column=1, value=p.flow_v.magnitude)
                    ws.cell(row=i, column=2,
                            value=p.head.to('kJ/kg').magnitude)
                    ws.cell(row=i, column=3, value=p.eff.magnitude * 100)

        if path_name is None:
            file_name = f'{self.suc.p().to("bar"):.0f~P}.xlsx'
            file_name = file_name.replace(' ', '-')
            path_name = Path.cwd() / file_name

        wb.save(str(path_name))

    def export_to_bokeh_source(self, sources, **kwargs):
        """Export curves to bokeh source for download."""
        speed_units = kwargs.get('speed_units')

        sources_dict = {k: [] for k in sources}
        sources_dict['flow_v'] = []
        sources_dict['speed'] = []

        for curve in self.curves:
            for p in curve:
                sources_dict['flow_v'].append(p.flow_v.magnitude)
                if speed_units is None:
                    sources_dict['speed'].append(p.speed.magnitude)
                else:
                    sources_dict['speed'].append(
                        p.speed.to(speed_units).magnitude)
                for s in sources:
                    if callable(r_getattr(p, s)):
                        sources_dict[s].append(r_getattr(p, s)().magnitude)
                    else:
                        sources_dict[s].append(r_getattr(p, s).magnitude)

        return ColumnDataSource(sources_dict)

    @classmethod
    def from_engauge_csv(cls, suc, curve_name, curve_path, speeds,
                         b=None, D=None, number_of_points=10,
                         flow_units='m**3/s', head_units='J/kg'):
        """Convert points from csv generated by engauge to csv with 6 points at same flow for use on hysys.

        suc: ccp.State
            Suction state.
        curve_path: pathlib.Path
            Path to the curves.
        curve_name: str
            Name for head and efficiency curve.
            Curves should have names <curve_name>-head.csv and <curve-name>-eff.csv.
        speeds: list
            List with speed value for each curve.
        number_of_points: int
            Number of points that will be interpolated.
        """
        # create dir
        curves_dir = curve_path / curve_name
        curves_dir.mkdir(exist_ok=True)

        head_path = curve_path / (curve_name + '-head.csv')
        eff_path = curve_path / (curve_name + '-eff.csv')

        head_curves = read_data_from_engauge_csv(head_path)
        eff_curves = read_data_from_engauge_csv(eff_path)

        points = []

        for speed, curve in zip(speeds, head_curves.keys()):
            head_interpolated = interp1d(head_curves[curve]['x'],
                                         head_curves[curve]['y'], kind=3,
                                         fill_value='extrapolate')
            eff_interpolated = interp1d(eff_curves[curve]['x'],
                                        eff_curves[curve]['y'], kind=3,
                                        fill_value='extrapolate')

            min_x = min(head_curves[curve]['x'] + eff_curves[curve]['x'])
            max_x = max(head_curves[curve]['x'] + eff_curves[curve]['x'])

            points_x = np.linspace(min_x, max_x, number_of_points)
            points_head = head_interpolated(points_x)
            points_eff = eff_interpolated(points_x)

            points += [
                Point(
                    suc=suc,
                    speed=speed,
                    flow_v=Q_(flow, flow_units).to('m**3/s'),
                    head=Q_(head, head_units).to('J/kg'),
                    eff=eff
                )
                for flow, head, eff in zip(points_x, points_head, points_eff)
            ]

        return cls(points, b=b, D=D)

    def save_hysys_csv(self, curve_dir):
        """Save curve to a csv with hysys format.

        curve_path: pathlib.Path
            Path for directory where the files will be saved.
        """
        curve_dir.mkdir(parents=True, exist_ok=True)
        surge = {'Volume Flow (m3/h'}
        for curve in self.curves:
            curve.save_hysys_csv(
                curve_dir / f'speed-{curve.speed.to("RPM").m:.0f}-RPM.csv'
            )



