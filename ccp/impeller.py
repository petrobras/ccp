"""Module to define impeller class."""
import csv
import toml
from copy import deepcopy
from itertools import groupby
from pathlib import Path
from warnings import warn

import numpy as np
import plotly.graph_objects as go
from openpyxl import Workbook
from scipy.interpolate import interp1d

from ccp import Q_, check_units, State, Point, Curve
from ccp.config.utilities import r_getattr, r_setattr
from ccp.data_io.read_csv import read_data_from_engauge_csv


class ImpellerState:
    def __init__(self, curves_state):
        self.curves_state = curves_state

        for attr in ["p", "T"]:
            func = self.state_parameter(attr)
            setattr(self, attr, func)

    def state_parameter(self, attr):
        def inner(*args, **kwargs):
            values = []

            for curve_state in self:
                values.append(getattr(getattr(curve_state, attr)(), "magnitude"))

            units = getattr(getattr(curve_state, attr)(), "units")

            return Q_(values, units)

        return inner

    def __getitem__(self, item):
        return self.curves_state.__getitem__(item)


class Impeller:
    @check_units
    def __init__(self, points):
        """Impeller class.

        Impeller instance is initialized with the list of points.
        The created instance will hold the dimensional points used in instantiation.
        Curves will be generated from points close in similarity.

        Parameters
        ----------
        points : list
            List with ccp.Point objects.
        """
        self.points = deepcopy(points)

        curves = []
        for speed, grouped_points in groupby(
            sorted(self.points, key=lambda point: point.speed),
            key=lambda point: point.speed,
        ):
            points = [point for point in grouped_points]
            curve = Curve(points)
            curves.append(curve)
            setattr(self, f"curve_{int(curve.speed.magnitude)}", curve)
        self.curves = curves
        self.disch = ImpellerState([c.disch for c in self.curves])

        for attr in ["disch.p", "disch.T", "head", "eff", "power"]:
            values = []
            # for disch.p etc values are defined in _Impeller_State
            if "." not in attr:
                for c in self.curves:
                    param = r_getattr(c, attr)
                    values.append(param.magnitude)
                units = param.units
                r_setattr(self, attr, Q_(values, units))

            r_setattr(self, attr + "_plot", self.plot_func(attr))

    def __getitem__(self, item):
        return self.points.__getitem__(item)

    def plot_func(self, attr):
        def inner(*args, plot_kws=None, **kwargs):
            fig = kwargs.pop("fig", None)

            if fig is None:
                fig = go.Figure()

            if plot_kws is None:
                plot_kws = {}

            for curve in self.curves:
                fig = r_getattr(curve, attr + "_plot")(
                    fig=fig, plot_kws=plot_kws, **kwargs
                )

            try:
                fig = r_getattr(self.current_curve, attr + "_plot")(
                    fig=fig, name=f"Current Curve {str(self.current_curve.speed.to('RPM'))}", plot_kws=plot_kws, **kwargs
                )
                fig = r_getattr(self.current_point, attr + "_plot")(
                    fig=fig, name="Current Point", plot_kws=plot_kws, **kwargs
                )
            except AttributeError:
                warn("Point not set for this impeller")

            return fig

        inner.__doc__ = r_getattr(self.curves[0], attr + "_plot").__doc__

        return inner

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
        try:
            speeds = np.array([curve.speed.magnitude for curve in self.curves])
        except AttributeError:
            return

        closest_curves_idxs = self._find_closest_speeds(speeds, self.speed.magnitude)
        curves = list(np.array(self.curves)[closest_curves_idxs])

        # calculate factor
        speed_range = curves[1].speed.magnitude - curves[0].speed.magnitude
        factor = (self.speed.magnitude - curves[0].speed.magnitude) / speed_range

        def get_interpolated_value(fac, val_0, val_1):
            return (1 - fac) * val_0 + fac * val_1

        min_flow = get_interpolated_value(
            factor, curves[0].flow_v.magnitude[0], curves[1].flow_v.magnitude[0]
        )
        max_flow = get_interpolated_value(
            factor, curves[0].flow_v.magnitude[-1], curves[1].flow_v.magnitude[-1]
        )

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
                Point(flow_v=f, speed=self.speed, suc=self.suc, disch=disch)
            )

        self.current_curve = Curve(points_current)

        disch_T_0 = curves[0].disch.T_interpolated(self.flow_v).magnitude
        disch_T_1 = curves[1].disch.T_interpolated(self.flow_v).magnitude
        disch_p_0 = curves[0].disch.p_interpolated(self.flow_v).magnitude
        disch_p_1 = curves[1].disch.p_interpolated(self.flow_v).magnitude

        disch_T = get_interpolated_value(factor, disch_T_0, disch_T_1)
        disch_p = get_interpolated_value(factor, disch_p_0, disch_p_1)
        current_disch = State.define(p=disch_p, T=disch_T, fluid=self.suc.fluid)
        self.current_point = Point(
            flow_v=self.flow_v, speed=self.speed, suc=self.suc, disch=current_disch
        )

    def _calc_new_points(self):
        """Calculate new dimensional points based on the suction condition."""
        #  keep volume ratio constant
        all_points = []
        for curve in self.curves:
            new_points = []
            for point in curve:
                new_points.append(self._calc_from_non_dimensional(point))

            speed_mean = np.mean([p.speed.magnitude for p in new_points])

            new_points = [
                self._calc_from_speed(p, Q_(speed_mean, p.speed.units))
                for p in new_points
            ]

            all_points += new_points

        self.new = self.__class__(
            all_points,
            b=self.b,
            D=self.D,
            _suc=self.new_suc,
            _flow_v=self.flow_v,
            _speed=self.speed,
        )

    def export_to_excel(self, path_name=None):
        """Export curves to excel file."""
        wb = Workbook()
        for curve in self.curves:
            sheet_name = f'{curve.speed.to("RPM"):.0f~P}'
            ws = wb.create_sheet(sheet_name)
            for i, p in enumerate(curve):
                i += 1  # openpyxl index
                if i == 1:
                    ws.cell(row=i, column=1, value="Flow (m**3/s)")
                    ws.cell(row=i, column=2, value="Head (kJ/kg)")
                    ws.cell(row=i, column=3, value="Efficiency (%)")
                else:
                    ws.cell(row=i, column=1, value=p.flow_v.magnitude)
                    ws.cell(row=i, column=2, value=p.head.to("kJ/kg").magnitude)
                    ws.cell(row=i, column=3, value=p.eff.magnitude * 100)

        if path_name is None:
            file_name = f'{self.suc.p().to("bar"):.0f~P}.xlsx'
            file_name = file_name.replace(" ", "-")
            path_name = Path.cwd() / file_name

        wb.save(str(path_name))

    @classmethod
    def from_engauge_csv(
        cls,
        suc,
        curve_name,
        curve_path,
        speeds,
        b=None,
        D=None,
        number_of_points=10,
        flow_units="m**3/s",
        head_units="J/kg",
    ):
        """Convert points from csv generated by engauge to csv with 6 points at same flow for use on hysys.

        The csv files should be generated with engauge with the following procedure:
        Inside engauge digitizer:
            - Edit -> Paste as new
            - On Axis Point -> add 3 reference points
            - Settings -> Curves -> With 'New', add how many curves will be collected
            - Segment fill
            - Select the curve (e.g. Curve1)
            - Select the points
            - Select the next curve and points...
            - Settings -> Export Setup -> Select:
            - Raws X's and Y's ; One curve on each line
        Files should be saved with the following convention:
            - <curve-name>-head.csv
            - <curve-name>-eff.csv

        suc : ccp.State
            Suction state.
        curve_path : pathlib.Path
            Path to the curves.
        curve_name : str
            Name for head and efficiency curve.
            Curves should have names <curve_name>-head.csv and <curve-name>-eff.csv.
        speeds : list
            List with speed value for each curve in rad/s.
        b : float, pint.Quantity
            Impeller width (m).
        D : float, pint.Quantity
            Impeller diameter (m).
        number_of_points : int
            Number of points that will be interpolated.
        flow_units : str
            Flow units used when extracting data with engauge.
        head_units : str
            Head units used when extracting data with engauge.
        """
        head_path = curve_path / (curve_name + "-head.csv")
        eff_path = curve_path / (curve_name + "-eff.csv")

        head_curves = read_data_from_engauge_csv(head_path)
        eff_curves = read_data_from_engauge_csv(eff_path)

        # define if we have volume or mass flow
        flow_type = "volumetric"
        if list(Q_(1, flow_units).dimensionality.keys())[0] == "[mass]":
            flow_type = "mass"

        points = []

        for speed, curve in zip(speeds, head_curves.keys()):
            head_interpolated = interp1d(
                head_curves[curve]["x"],
                head_curves[curve]["y"],
                kind=3,
                fill_value="extrapolate",
            )
            # check eff scale
            if max(eff_curves[curve]["y"]) > 1:
                eff_curves[curve]["y"] = [i / 100 for i in eff_curves[curve]["y"]]
            eff_interpolated = interp1d(
                eff_curves[curve]["x"],
                eff_curves[curve]["y"],
                kind=3,
                fill_value="extrapolate",
            )

            min_x = min(head_curves[curve]["x"] + eff_curves[curve]["x"])
            max_x = max(head_curves[curve]["x"] + eff_curves[curve]["x"])

            points_x = np.linspace(min_x, max_x, number_of_points)
            points_head = head_interpolated(points_x)
            points_eff = eff_interpolated(points_x)

            if flow_type == "volumetric":
                points += [
                    Point(
                        suc=suc,
                        speed=speed,
                        flow_v=Q_(flow, flow_units).to("m**3/s"),
                        head=Q_(head, head_units).to("J/kg"),
                        eff=eff,
                    )
                    for flow, head, eff in zip(points_x, points_head, points_eff)
                ]
            else:
                points += [
                    Point(
                        suc=suc,
                        speed=speed,
                        flow_m=Q_(flow, flow_units).to("kg/s"),
                        head=Q_(head, head_units).to("J/kg"),
                        eff=eff,
                    )
                    for flow, head, eff in zip(points_x, points_head, points_eff)
                ]

        return cls(points, b=b, D=D)

    def save(self, file):
        """Save impeller to a toml file.

        Parameters
        ==========
        file : str or pathlib.Path
            Filename to which the data is saved.
        """

        with open(file, mode="w") as f:
            # add impeller geometry to file
            dict_to_save = {"b": self.b.m, "D": self.D.m}
            toml.dump(dict_to_save, f)
            # add points to file
            dict_to_save = {f"Point{i}": point._dict_to_save() for i, point in enumerate(self.points)}
            toml.dump(dict_to_save, f)

    @classmethod
    def load(cls, file):
        """Load impeller from toml file.

        Parameters
        ==========
        file : str or pathlib.Path
            Filename to which the data is saved.

        Returns
        =======
        impeller : ccp.Impeller
            Impeller object.
        """
        parameters = toml.load(file)
        b = parameters.pop("b")
        D = parameters.pop("D")
        points = [Point(**Point._dict_from_load(kwargs)) for kwargs in parameters.values()]

        return cls(points, b=b, D=D)

    def save_hysys_csv(self, curve_dir):
        """Save curve to a csv with hysys format.

        curve_path: pathlib.Path
            Path for directory where the files will be saved.
        """
        curve_dir.mkdir(parents=True, exist_ok=True)
        surge = {"Speed (RPM)": [], "Volume Flow (m3/h)": []}
        stonewall = {"Speed (RPM)": [], "Volume Flow (m3/h)": []}

        for curve in self.curves:
            curve.save_hysys_csv(
                curve_dir / f'speed-{curve.speed.to("RPM").m:.0f}-RPM.csv'
            )
            surge["Speed (RPM)"].append(curve.speed.to("RPM").m)
            stonewall["Speed (RPM)"].append(curve.speed.to("RPM").m)
            surge["Volume Flow (m3/h)"].append(
                min(p.flow_v.to("m**3/h").m for p in curve)
            )
            stonewall["Volume Flow (m3/h)"].append(
                max(p.flow_v.to("m**3/h").m for p in curve)
            )

        for name, limit in zip(["surge", "stonewall"], [surge, stonewall]):
            with open(str(curve_dir / (name + ".csv")), mode="w") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=list(limit.keys()))
                writer.writeheader()
                for speed, flow in zip(
                    limit["Speed (RPM)"], limit["Volume Flow (m3/h)"]
                ):
                    writer.writerow({"Speed (RPM)": speed, "Volume Flow (m3/h)": flow})
