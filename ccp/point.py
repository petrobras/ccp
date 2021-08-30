from copy import copy

import numpy as np
import toml
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import newton

import ccp.config
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
    suc, disch_p, eff : ccp.State, float, float
        Suction state, discharge pressure and polytropic efficiency.
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
    polytropic_method : str, optional
        Polytropic method used for head and efficiency calculation.
        Options are: "mallen_saveille", "sandberg_colby", "schultz" and "huntington".
        The default is "schultz".
        The default value can be changed in a global level with:
        ccp.config.POLYTROPIC_METHOD = "<desired value>"
    """

    @check_units
    def __init__(
        self,
        suc=None,
        disch=None,
        disch_p=None,
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
        polytropic_method=None,
    ):
        if b is None or D is None:
            raise ValueError("Arguments b and D must be provided.")
        if polytropic_method is None:
            polytropic_method = ccp.config.POLYTROPIC_METHOD

        self.head_calc_func = globals()[f"head_pol_{polytropic_method}"]
        self.eff_calc_func = globals()[f"eff_pol_{polytropic_method}"]

        self.suc = suc
        self.disch = disch
        self.disch_p = disch_p
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
            "disch_p",
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
        self.head = self.head_calc_func(self.suc, self.disch)
        self.eff = self.eff_calc_func(self.suc, self.disch)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.flow_m = self.suc.rho() * self.flow_v
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)

    def _calc_from_disch_flow_m_speed_suc(self):
        self.head = self.head_calc_func(self.suc, self.disch)
        self.eff = self.eff_calc_func(self.suc, self.disch)
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
            new_eff = self.eff_calc_func(self.suc, disch)
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
        self.head = self.head_calc_func(suc, disch)
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

    def _calc_from_disch_p_eff_flow_v_speed_suc(self):
        eff = self.eff
        suc = self.suc
        disch = disch_from_suc_disch_p_eff(suc, self.disch_p, eff)
        self.disch = disch
        self.head = self.head_calc_func(suc, disch)
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()

    def _calc_from_disch_p_eff_flow_m_speed_suc(self):
        eff = self.eff
        suc = self.suc
        disch = disch_from_suc_disch_p_eff(suc, self.disch_p, eff)
        self.disch = disch
        self.head = self.head_calc_func(suc, disch)
        self.flow_v = self.flow_m / self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()

    @classmethod
    @check_units
    def convert_from(cls, original_point, suc=None, find="speed", speed=None):
        """Convert point from an original point.

        The user must provide 3 of the 4 available arguments. The argument which is not
        provided will be calculated.
        """
        if speed is None:
            speed = original_point.speed
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
                speed=speed,
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

    def mach_limits(self, mmsp=None):
        """Calculate Mach lower and upper limits.

        Parameters
        ----------
        mmsp : float, optional
            Mach number specified. Default value is the point Mach number.

        Returns
        -------
        limits : dict
            Dict with keys: 'lower', 'upper' and 'within_limits'.
        """
        if mmsp is None:
            mmsp = self.mach.m
        if 0 <= mmsp < 0.214:
            lower_limit = -mmsp
            upper_limit = -0.25 * mmsp + 0.286
        elif 0.214 <= mmsp < 0.86:
            lower_limit = 0.266 * mmsp - 0.271
            upper_limit = -0.25 * mmsp + 0.286
        elif mmsp >= 0.86:
            lower_limit = -0.042
            upper_limit = 0.07
        else:
            raise ValueError("Mach number out of specified range.")

        if lower_limit < self.mach_diff < upper_limit:
            within_limits = True
        else:
            within_limits = False

        return {
            "lower": lower_limit,
            "upper": upper_limit,
            "within_limits": within_limits,
        }

    def plot_mach(self, fig=None, **kwargs):
        """Plot allowable Mach range and point.

        This will plot the allowable Mach range and the point according to the
        PTC criteria.

        Parameters
        ----------
        fig : plotly.Figure
            Plotly figure.

        Returns
        -------
        fig : plotly.Figure
            Plotly figure.
        """
        if fig is None:
            fig = go.Figure()

        # build acceptable region
        upper_limit = []
        lower_limit = []
        mmsp_range = np.linspace(0, 1.6, 300)
        for mmsp in mmsp_range:
            mach_limits = self.mach_limits(mmsp)
            lower_limit.append(mach_limits["lower"])
            upper_limit.append(mach_limits["upper"])

        fig.add_trace(
            go.Scatter(x=mmsp_range, y=lower_limit, marker=dict(color="black"))
        )
        fig.add_trace(
            go.Scatter(x=mmsp_range, y=upper_limit, marker=dict(color="black"))
        )

        # add point
        fig.add_trace(
            go.Scatter(x=[self.mach.m], y=[self.mach_diff], marker=dict(color="red"))
        )

        fig.update_xaxes(
            title=r"$\text{Machine Mach No. Specified} - Mm_{sp}$",
        )
        fig.update_yaxes(
            title=r"$Mm_t - Mm_{sp}$",
        )
        fig.update_layout(showlegend=False)

        return fig

    def reynolds_limits(self, remsp=None):
        """Calculate Reynolds lower and upper limits.

        Parameters
        ----------
        remsp : float, optional
            Reynolds number specified. Default value is the point reynolds number.

        Returns
        -------
        limits : dict
            Dict with keys: 'lower', 'upper' and 'within_range'.
        """
        if remsp is None:
            remsp = self.reynolds

        x = (remsp / 1e7) ** 0.3
        if 9e4 <= remsp < 1e7:
            upper_limit = 100 ** x
        elif 1e7 <= remsp:
            upper_limit = 100
        else:
            raise ValueError("Reynolds number out of specified range.")

        if 9e4 <= remsp < 1e6:
            lower_limit = 0.01 ** x
        elif 1e6 <= remsp:
            lower_limit = 0.1
        else:
            raise ValueError("Reynolds number out of specified range.")

        if lower_limit < self.reynolds_ratio < upper_limit:
            within_limits = True
        else:
            within_limits = False

        return {
            "lower": lower_limit,
            "upper": upper_limit,
            "within_limits": within_limits,
        }

    def plot_reynolds(self, fig=None, **kwargs):
        """Plot allowable Reynolds range and point.

        This will plot the allowable Mach range and the point according to the
        PTC criteria.

        Parameters
        ----------
        fig : plotly.Figure
            Plotly figure.

        Returns
        -------
        fig : plotly.Figure
            Plotly figure.
        """
        # build acceptable region
        upper_limit = []
        lower_limit = []
        remsp_range = np.geomspace(9e4, 1e9, 300)
        for remsp in remsp_range:
            reynolds_limits = self.reynolds_limits(remsp)
            lower_limit.append(reynolds_limits["lower"])
            upper_limit.append(reynolds_limits["upper"])

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=remsp_range, y=lower_limit, marker=dict(color="black"))
        )
        fig.add_trace(
            go.Scatter(x=remsp_range, y=upper_limit, marker=dict(color="black"))
        )

        # add point
        fig.add_trace(
            go.Scatter(
                x=[self.reynolds.m], y=[self.reynolds_ratio], marker=dict(color="red")
            )
        )

        fig.update_xaxes(
            type="log",
            tickformat=".1e",
            tickmode="array",
            tickvals=[10 ** i for i in range(4, 9)],
            title=r"$\text{Machine Reynolds No. Specified} - Rem_{sp}$",
        )
        fig.update_yaxes(
            type="log",
            tickformat=".1e",
            tickmode="array",
            tickvals=[10 ** i for i in range(-3, 3)],
            title=r"$Rem_t / Rem_{sp}$",
        )
        fig.update_layout(showlegend=False)

        return fig

    def similarity_table(self, fig=None, **kwargs):
        """Plot similarity table.

        This table show the values for the non dimensional numbers (Mach, Reynolds
        and Volume ratio) and their calculated relations with respect to the
        original points used in the conversion (in the formulas, 'c' means converted
        points and 'o' means original point).

        If values are within limits, relation cells are colored in green, otherwise
        they are colored in red.

        """
        if fig is None:
            fig = go.Figure()

        quantity = ["Ratio of Specific Volume", "Mach Number", "Reynolds Number"]
        abbrev = ["$v_i / v_d$", "Mm", "Rem"]
        point_value = [
            f"{self.volume_ratio.m:.3f}",
            f"{self.mach.m:.3f}",
            f"{self.reynolds.m:.3e}",
        ]
        formula = [
            "$(v_i / v_d)_c / (v_i / v_d)_o = $",
            "$Mm_c - Mm_o = $",
            "$Rem_c / Rem_o = $",
        ]
        relation = [
            f"{self.volume_ratio_ratio.m:.3f}",
            f"{self.mach_diff.m:.3f}",
            f"{self.reynolds_ratio.m:.3e}",
        ]
        mach_limits = self.mach_limits()
        reynolds_limits = self.reynolds_limits()
        lower_limit = [
            0.95,
            f'{mach_limits["lower"]:.3f}',
            f'{reynolds_limits["lower"]:.3e}',
        ]
        upper_limit = [
            1.05,
            f'{mach_limits["upper"]:.3f}',
            f'{reynolds_limits["upper"]:.3e}',
        ]

        if 0.95 < self.volume_ratio_ratio < 1.05:
            volume_ratio_within_limits = True
        else:
            volume_ratio_within_limits = False

        light_green = "#D8F3DC"
        dark_green = "#2D6A4F"
        light_red = "#FFB3C1"
        dark_red = "#A4133C"

        rel_fill_color = []
        rel_font_color = []
        for status in [
            volume_ratio_within_limits,
            mach_limits["within_limits"],
            reynolds_limits["within_limits"],
        ]:
            if status is True:
                rel_fill_color.append(light_green)
                rel_font_color.append(dark_green)
            else:
                rel_fill_color.append(light_red)
                rel_font_color.append(dark_red)

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(
                        values=[
                            "<b>Quantity</b>",
                            "<b></b>",
                            "<b>Point Value</b>",
                            "<b></b>",
                            "<b>Relation</b>",
                            "<b>Lower Limit</b>",
                            "<b>Upper Limit</b>",
                        ],
                        line_color="white",
                        fill_color="white",
                        align="center",
                        font=dict(color="black", size=12),
                    ),
                    cells=dict(
                        values=[
                            quantity,
                            abbrev,
                            point_value,
                            formula,
                            relation,
                            lower_limit,
                            upper_limit,
                        ],
                        line_color=[
                            "white",
                            "white",
                            "white",
                            "white",
                            "white",
                            "white",
                            "white",
                        ],
                        fill_color=[
                            "white",
                            "white",
                            "white",
                            "white",
                            rel_fill_color,
                            "white",
                            "white",
                        ],
                        align="center",
                        font=dict(
                            color=[
                                "black",
                                "black",
                                "black",
                                "black",
                                rel_font_color,
                                "black",
                                "black",
                            ],
                            size=[12],
                        ),
                    ),
                )
            ]
        )

        return fig

    def plot_similarity(self, fig=None, **kwargs):
        """Plot similarity results.

        Plots the similarity results showing the Mach and Reynolds plots with
        their respective limits and also a table summarizing the results comparing
        the current (converted) point to the original point.

        Parameters
        ----------
        fig : plotly.Figure
            Plotly figure.

        Returns
        -------
        fig : plotly.Figure
            Plotly figure.
        """
        if fig is None:
            fig = make_subplots(
                rows=2,
                cols=2,
                specs=[
                    [{"type": "xy"}, {"type": "xy"}],
                    [{"type": "table", "colspan": 2}, None],
                ],
            )

        stable = self.similarity_table()
        mach = self.plot_mach()
        reynolds = self.plot_reynolds()

        for data in mach.data:
            data.showlegend = False
            fig.append_trace(data, row=1, col=1)

        for data in reynolds.data:
            data.showlegend = False
            fig.append_trace(data, row=1, col=2)

        for data in stable.data:
            fig.append_trace(data, row=2, col=1)

        fig.update_xaxes(mach.layout.xaxis, row=1, col=1)
        fig.update_xaxes(reynolds.layout.xaxis, row=1, col=2)
        fig.update_yaxes(mach.layout.yaxis, row=1, col=1)
        fig.update_yaxes(reynolds.layout.yaxis, row=1, col=2)

        return fig


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
    r"""Polytropic exponent.

    The polytropic exponent :math:`n` is calculated as per :cite:`schultz1962` eq. 27:

    .. math::

        \begin{equation}
            n = \frac{\log{\frac{p_d}{p_s}}}{\log{\frac{v_s}{v_d}}}
        \end{equation}

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


def head_pol(suc, disch):
    r"""Polytropic head.

    The polytropic head is calculated as per :cite:`schultz1962` eq. 27:

    .. math::

       \begin{equation}
          H_p = (\frac{n}{n - 1}) (p_d v_d - p_s v_s)
       \end{equation}

    And :math:`n` is calculated by :py:func:`n_exp`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_pol : pint.Quantity
        Polytropic head (J/kg).
    """

    n = n_exp(suc, disch)

    p2 = disch.p()
    v2 = 1 / disch.rho()
    p1 = suc.p()
    v1 = 1 / suc.rho()

    return (n / (n - 1)) * (p2 * v2 - p1 * v1).to("joule/kilogram")


def eff_pol(suc, disch):
    """Polytropic efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    eff_pol : pint.Quantity
        Polytropic efficiency (dimensionless).

    """
    wp = head_pol(suc, disch)

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

    return head_pol(suc, disch_s).to("joule/kilogram")


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
    r"""Correction factor as per :cite:`schultz1962` eq 32:

    .. math::

       \begin{equation}
          f = \frac{H_{ds} - H_s}{(\frac{n_s}{n_s - 1})(p_d v_{ds} - p_s v_s)}
       \end{equation}


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
    r"""Polytropic head corrected by the :cite:`schultz1962` factor.

    .. math::

       \begin{equation}
          H_{p_{schultz}} = f_{schultz} H_p
       \end{equation}

    Where :math:`f_{schultz}` is calculated by :py:func:`f_schultz` and
    :math:`H_p` is calculated by :py:func:`head_pol`.

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
    head = head_pol(suc, disch)

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
    r"""Polytropic head as per :cite:`mallen1977polytropic` calculated with:

    .. math::

       \begin{equation}
          H_p = (h_d - h_s) - (s_d - s_s) \frac{T_d - Ts}{\ln{(\frac{T_d}{T_s})}}
       \end{equation}

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
    r"""Reference head.

    The reference head consists of the integration of :math:`v dp` along the
    polytropic path as described by :cite:`huntington1985` and :cite:`sandberg2013limitations`.
    To achieve this we break the polytropic path into a series of subpaths.
    The compression ratio :math:`R_{c_i}` for each segment, as described by
    :cite:`sandberg2013limitations` is calculated with:

    .. math::

       \begin{equation}
          R_{c_i} = \sqrt[n_{steps}]{\frac{p_d}{p_s}}
       \end{equation}


    The calculation consists of two loops.
    One converges the :math:`T_1` temperature at each step by evaluating the
    difference between :math:`H = v_{avg} \Delta_p` and :math:`H = e \Delta_h`.
    The other evaluates the efficiency by checking the difference between
    the last :math:`T_1` to the discharge temperature :math:`T_d`.

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

        # TODO implement p_intervals considering pressure ratio
        for p0, p1 in zip(p_intervals[:-1], p_intervals[1:]):
            s0 = State.define(p=p0, T=T0, fluid=suc.fluid)
            T1 = newton(
                calc_step_discharge_temp, (T0 + 1e-3), args=(p1, p0, s0.h(), s0.v(), e)
            )
            s1 = State.define(p=p1, T=T1, fluid=suc.fluid)
            _ref_H += head_pol(s0, s1)

            T0 = T1

        return disch.T().magnitude - T1

    _ref_eff = newton(calc_eff, 0.8, args=(suc, disch))

    return _ref_H, _ref_eff


_ref_H_2017 = 0


def head_reference_2017(suc, disch, num_steps=100):
    r"""Reference head.

    The reference head consists of the integration along the
    polytropic path as described by :cite:`huntington2017`.
    Contrary to the method presented by :cite:`huntington1985`, this method does
    not use a specific volume linearized over each step of the integration, instead,
    it is based on the assumption that the compressibility factor varies linearly
    with the pressure within each step.

    In this case the inner loop of the method is calculated by:

    .. math::

       \begin{equation}
          a = \frac{z_i (\frac{p_{i+1}}{p_i}) - z_{i+1}}
          {(\frac{p_{i+1}}{p_i} - 1)} \\
          b = \frac{z_{i+1} - z_i}
          {(\frac{p_{i+1}}{p_i} - 1)} \\
          (s_{i+1} - s_i) = R \frac{(1-e)}{e}(a \ln{(\frac{p_{i+1}}{p_i})} + b(\frac{p_{i+1}}{p_i} - 1))
      \end{equation}


    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.

    Returns
    -------
    head_reference : pint.Quantity
       Reference head as described by :cite:`huntington2017`. (J/kg).
    eff_reference : float
        Reference efficiency as described by :cite:`huntington2017` (dimensionless).
    """
    R = suc.gas_constant() / suc.molar_mass()
    rc = (disch.p().m / suc.p().m) ** (1 / num_steps)
    p_intervals = [suc.p().m]
    p = suc.p().m
    for i in range(num_steps):
        next_p = p * rc
        p = next_p
        p_intervals.append(p)

    def calc_step_discharge_z(s1, s0, p1, p0, z0, R, e):
        state1 = ccp.State.define(p=p1, s=s1, fluid=suc.fluid)
        z1 = state1.z()
        a = (z0 * (p1 / p0) - z1) / ((p1 / p0) - 1)
        b = (z1 - z0) / ((p1 / p0) - 1)

        return (
            (R * ((1 - e) / e)) * (a * np.log(p1 / p0) + b * ((p1 / p0) - 1))
            - (state1.s() - Q_(s0, state1.s().units))
        ).magnitude

    def calc_eff(e, suc, disch, p_intervals):
        global _ref_H_2017
        _ref_H_2017 = 0
        s0 = suc.s().magnitude

        for p0, p1 in zip(p_intervals[:-1], p_intervals[1:]):
            state0 = ccp.State.define(p=p0, s=s0, fluid=suc.fluid)
            z0 = state0.z()

            s1 = newton(calc_step_discharge_z, (s0 + 1e-8), args=(s0, p1, p0, z0, R, e))
            state1 = ccp.State.define(p=p1, s=s1, fluid=suc.fluid)
            _ref_H_2017 += ccp.point.head_pol(state0, state1)

            s0 = s1
            T1 = state1.T().magnitude

        return disch.T().magnitude - T1

    eff0 = ccp.point.eff_pol_huntington(suc, disch)
    _ref_eff = newton(calc_eff, eff0, args=(suc, disch, p_intervals))

    return _ref_H_2017, _ref_eff


def f_sandberg_colby(suc, disch):
    r"""Correction factor as proposed by :cite:`sandberg2013limitations`.

    .. math::

       \begin{equation}
          f_p =
           \frac{(h_d - h_s) - T_{avg} (s_d - s_s)}
          {(\frac{n}{n-1})(p_d v_d - p_s v_s)}
       \end{equation}

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
    r"""Polytropic head corrected by the :cite:`sandberg2013limitations` factor.

    .. math::

       \begin{equation}
          H_{p_{s-c}} = f_{s-c} H_p
       \end{equation}

    Where :math:`f_{s-c}` is calculated by :py:func:`f_sandberg_colby` and
    :math:`H_p` is calculated by :py:func:`head_pol`.

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
    h = f * head_pol(suc, disch)
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
    r"""Polytropic head calculated by the 3 point method described by :cite:`huntington1985`.

    The polytropic head in this case is calculated from the polytropic efficiency with:

    .. math::

       \begin{equation}
          \frac{1}{e} =
          1 +
          \frac{\frac{(s_d - s_s)}{R}}
          {a \ln(\frac{p_d}{p_s})
          + b((\frac{p_d}{p_s}) - 1)
          + \frac{c}{2}(\ln{(\frac{p_d}{p_s})})^2}
       \end{equation}

    The constants :math:`a`, :math:`b` and :math:`c` are calculated with:

    .. math::

       \begin{equation}
          a = z_s - b \\
          b = \frac{(z_s + z_d - 2z_{int})}{((\frac{p_s}{p_s})^{0.5} - 1)^2} \\
          c = \frac{(z_d - a - b(\frac{p_d}{p_s}))}{\ln{(\frac{p_d}{p_s})}}
       \end{equation}

    The intermediate values are calculated interactively:

    .. math::

       \begin{equation}
          p_{int} = \sqrt{p_s p_d} \\
          T_{int}' = T_{int} \exp{(\frac{(s_{int}' - s_{int})}{c_p})}
       \end{equation}

    And :math:`s_{int}` is calculated by:

    .. math::

       \begin{equation}
            s_{int}' = s_s + (s_d - s_s)
            \frac{\frac{a}{2}\ln{(\frac{p_d}{p_s})} + b((\frac{p_s}{p_s})^{0.5} - 1)) + \frac{c}{8}(\ln{(\frac{p_d}{p_s})})^2}
            {a\ln(\frac{p_d}{p_s}) + b((\frac{p_d}{p_s})-1) + \frac{c}{2}(\ln(\frac{p_d}{p_s}))^2}
       \end{equation}

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


def disch_from_suc_head_eff(suc, head, eff, polytropic_method=None):
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
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD

    head_calc_func = globals()[f"head_pol_{polytropic_method}"]
    h_disch = head / eff + suc.h()

    #  consider first an isentropic compression
    disch = State.define(h=h_disch, s=suc.s(), fluid=suc.fluid)

    def update_pressure(p):
        disch.update(h=h_disch, p=p)
        new_head = head_calc_func(suc, disch)

        return (new_head - head).magnitude

    newton(update_pressure, disch.p().magnitude, tol=1e-1)

    return disch


def disch_from_suc_disch_p_eff(suc, disch_p, eff, polytropic_method=None):
    """Calculate discharge state from suction, discharge pressure and efficiency.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch_p : pint.Quantity, float
        Discharge pressure (Pa).
    eff : pint.Quantity, float
        Polytropic efficiency (dimensionless).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    # consider first an isentropic compression
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD

    disch = ccp.State.define(p=disch_p, s=suc.s(), fluid=suc.fluid)
    eff_calc_func = globals()[f"eff_pol_{polytropic_method}"]

    def update_state(x):
        disch.update(p=disch_p, T=x)
        new_eff = eff_calc_func(suc, disch)

        return (new_eff - eff).magnitude

    newton(update_state, disch.T().magnitude)

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
