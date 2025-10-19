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
    suc, head, power_shaft, power_losses : ccp.State, pint.Quantity or float, pint.Quantity or float, pint.Quantity or float
        Suction state, polytropic head (J/kg), shaft power (Watt) and power losses (Watt).
    suc, eff, volume_ratio : ccp.State, float, float
        Suction state, polytropic efficiency and volume ratio.
    suc, pres_ratio, disch_T : ccp.State, float, pint.Quantity or float
        Suction state, pressure ration and discharge temperature.
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).
    D : float, pint.Quantity
        Impeller outer diameter (m).
    power_shaft : float, pint.Quantity
        Shaft power (Watt), optional.
    power_losses : float, pint.Quant
        Mechanical power losses (Watt), optional.
    torque : float, pint.Quantity
        load torque (N.m), optional.                                                                                                                                                       (N.m), optional.
    surface_roughness : pint.Quantity, optional
        Gas passage mean surface roughness (m).
        Used in the reynolds correction calculation.
        Default value is 3.048e-6 m.
    casing_area : pint.Quantity, optional
        Compressor case area used to calculate case heat loss (m²).
    casing_temperature : pint.Quantity, optional
        Compressor case temperature used to calculate case heat loss (degK).
    ambient_temperature : pint.Quantity, optional
        Ambient temperature used to calculate case heat loss (degK).
    convection_constant : pint.Quantity, optional
        Heat transfer (convection) constant (W / m²degK).
        Default value is 13.6.
    polytropic_method : str, optional
        Polytropic method used for head and efficiency calculation.
        Options are: "mallen_saville", "sandberg_colby", "schultz" and "huntington".
        The default is "schultz".
        The default value can be changed in a global level with:
        ccp.config.POLYTROPIC_METHOD = "<desired value>"

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
    power_shaft : pint.Quantity
        Shaft power (Watt) which includes bearing and seal losses.
    power_losses : pint.Quantity
        Mechanical power losses (Watt) which includes bearing and seal.
    torque : pint.Quantity
        Load torque (N*m) at coupling which includes bearing and seal losses.
    phi : pint.Quantity
        Volume flow coefficient (dimensionless).
    psi : pint.Quantity
        Polytropic head coefficient (dimensionless).
    volume_ratio : pint.Quantity
        Volume ratio - suc.v() / disch.v() (dimensionless).
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).
    D : float, pint.Quantity
        Impeller outer diameter (m).
    casing_area : pint.Quantity
        Compressor case area used to calculate case heat loss (m²).
    casing_temperature : pint.Quantity
        Compressor case temperature used to calculate case heat loss (degK).
    ambient_temperature : pint.Quantity
        Ambient temperature used to calculate case heat loss (degK).
    convection_constant : pint.Quantity
        Heat transfer (convection) constant (W / m²degK).
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
    volume_ratio_ratio : float
        Ratio between volume_ratio for this point and the original point from which it was converted from.
    polytropic_method : str
        Polytropic method used for head and efficiency calculation.
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
        power_shaft=None,
        power_losses=None,
        torque=None,
        phi=None,
        psi=None,
        volume_ratio=None,
        pressure_ratio=None,
        disch_T=None,
        b=Q_(0.005, "m"),
        D=Q_(0.5, "m"),
        surface_roughness=Q_(3.175e-6, "m"),
        casing_area=None,
        casing_temperature=None,
        ambient_temperature=None,
        convection_constant=Q_(13.6, "W/(m²*degK)"),
        polytropic_method=None,
    ):
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
        self.power_shaft = power_shaft
        self.power_losses = power_losses
        self.torque = torque

        self.phi = phi
        self.psi = psi
        self.volume_ratio = volume_ratio
        self.pressure_ratio = pressure_ratio
        self.disch_T = disch_T

        self.b = b
        self.D = D
        self.surface_roughness = surface_roughness

        self.casing_area = casing_area
        self.casing_temperature = casing_temperature
        self.ambient_temperature = ambient_temperature
        self.convection_constant = convection_constant
        self.casing_heat_loss = None

        # dummy state used to avoid copying states
        self._dummy_state = copy(self.suc)

        kwargs_list = []
        kwargs_dict = {}
        reasonable_ranges = {
            "eff": (0.3, 1.0),
            "head": (0, 1e15),
            "disch_p": (0, 1e15),
        }
        out_of_range_dict = {}

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
            "pressure_ratio",
            "disch_T",
            "power_losses",
            "power_shaft",
            "torque",
        ]:
            if getattr(self, k) is not None:
                kwargs_list.append(k)
                kwargs_dict[k] = getattr(self, k)

        kwargs_str = "_".join(sorted(kwargs_list))

        try:
            getattr(self, "_calc_from_" + kwargs_str)()
        except (ValueError, RuntimeError) as e:
            kwargs_repr = (
                str(kwargs_dict)
                .replace(">", "")
                .replace("<", "")
                .replace("Quantity", "Q_")
                .replace("State", "ccp.State")
            )
            # check if some kwargs are out of reasonable range
            for k in kwargs_dict:
                if k in reasonable_ranges:
                    if (
                        not reasonable_ranges[k][0]
                        <= kwargs_dict[k].m
                        <= reasonable_ranges[k][1]
                    ):
                        # add this to the out of range dict
                        out_of_range_dict[k] = kwargs_dict[k]

            raise ValueError(
                f"Could not calculate point with ccp.Point(**{kwargs_repr}).\n"
                f"The following kwargs seems out of reasonable range: {out_of_range_dict}."
            )

        self.reynolds = reynolds(self.suc, self.speed, self.b, self.D)
        self.mach = mach(self.suc, self.speed, self.D)

        self.phi_ratio = Q_(1.0, "dimensionless")
        self.psi_ratio = Q_(1.0, "dimensionless")
        self.reynolds_ratio = Q_(1.0, "dimensionless")
        # mach in the ptc 10 is compared with Mmt - Mmsp
        self.mach_diff = Q_(0.0, "dimensionless")
        # ratio between specific volume ratios in original and converted conditions
        self.volume_ratio_ratio = Q_(1.0, "dimensionless")

        self._add_point_plot()

    def _add_point_plot(self):
        """Add plot to point after point is fully defined."""
        for state in ["suc", "disch"]:
            for attr in ["p", "T", "h", "s", "rho"]:
                plot = plot_func(self, ".".join([state, attr]))
                setattr(getattr(self, state), attr + "_plot", plot)
        for attr in ["head", "eff", "power", "power_shaft", "torque"]:
            plot = plot_func(self, attr)
            setattr(self, attr + "_plot", plot)

    def __str__(self):
        return (
            f"\nPoint: "
            f"\nVolume flow: {self.flow_v:.2f~P}"
            f"\nHead: {self.head:.2f~P}"
            f"\nEfficiency: {self.eff:.2f~P}"
            f"\nPower: {self.power:.2f~P}"
            f"\nShaft Power: {self.power_shaft:.2f~P}"
            f"\nTorque: {self.torque:.2f~P}"
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

    def __hash__(self):
        return hash(
            (
                self.suc,
                round(self.speed.to_base_units().magnitude, 8) if self.speed else None,
                (
                    round(self.flow_v.to_base_units().magnitude, 8)
                    if self.flow_v
                    else None
                ),
                round(self.head.to_base_units().magnitude, 8) if self.head else None,
                round(self.eff.to_base_units().magnitude, 8) if self.eff else None,
            )
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(suc={self.suc},"
            f' speed=Q_("{self.speed:.0f~P}"),'
            f' flow_v=Q_("{self.flow_v:.2f~P}"),'
            f' head=Q_("{self.head:.0f~P}"),'
            f' eff=Q_("{self.eff:.3f~P}"),'
            f' power_losses=Q_("{self.power_losses:.0f~P}"))'
        )

    def _calc_from_disch_flow_v_speed_suc(self):
        self.head = self.head_calc_func(self.suc, self.disch, self._dummy_state)
        self.eff = self.eff_calc_func(self.suc, self.disch, self._dummy_state)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.flow_m = self.suc.rho() * self.flow_v
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        if self.casing_temperature is not None:
            # correct efficiency with casing heat loss
            self.casing_heat_loss = (
                self.convection_constant
                * self.casing_area
                * (self.casing_temperature - self.ambient_temperature)
            )
            self.eff = self.eff / (
                1
                + (
                    self.casing_heat_loss
                    / ((self.disch.h() - self.suc.h()) * self.flow_m)
                )
            )
        self.power = power_calc(self.flow_m, self.head, self.eff)
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_flow_v_speed_suc_torque(self):
        self._calc_from_disch_flow_v_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_disch_flow_v_power_losses_speed_suc(self):
        self._calc_from_disch_flow_v_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_flow_m_speed_suc(self):
        self.head = self.head_calc_func(self.suc, self.disch, self._dummy_state)
        self.eff = self.eff_calc_func(self.suc, self.disch, self._dummy_state)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.flow_v = self.flow_m / self.suc.rho()
        if self.casing_temperature is not None:
            # correct efficiency with casing heat loss
            self.casing_heat_loss = (
                self.convection_constant
                * self.casing_area
                * (self.casing_temperature - self.ambient_temperature)
            )
            self.eff = self.eff / (
                1
                + (
                    self.casing_heat_loss
                    / ((self.disch.h() - self.suc.h()) * self.flow_m)
                )
            )
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_flow_m_speed_suc_torque(self):
        self._calc_from_disch_flow_m_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_disch_flow_m_power_losses_speed_suc(self):
        self._calc_from_disch_flow_m_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_eff_phi_psi_suc_volume_ratio(self):
        eff = self.eff
        suc = self.suc
        volume_ratio = self.volume_ratio

        disch_v = suc.v() / volume_ratio
        disch_rho = 1 / disch_v

        # consider first an isentropic compression
        disch = State(rho=disch_rho, s=suc.s(), fluid=suc.fluid)

        def update_state(x, update_type):
            if update_type == "pressure":
                disch.update(rho=disch_rho, p=x)
            elif update_type == "temperature":
                disch.update(rho=disch_rho, T=x)
            new_eff = self.eff_calc_func(self.suc, disch)
            if not 0.0 < new_eff < 1.5:
                raise ValueError("Efficiency did not converge")

            return (new_eff - eff).magnitude

        try:
            newton(update_state, disch.T().magnitude, args=("temperature",), tol=1e-1)
        except ValueError:
            # re-instantiate disch, since update with temperature not converging
            # might break the state
            disch = State(rho=disch_rho, s=suc.s(), fluid=suc.fluid)
            newton(update_state, disch.p().magnitude, args=("pressure",), tol=1e-1)

        self.disch = disch
        self.head = self.head_calc_func(suc, disch, self._dummy_state)
        self.speed = speed_from_psi(self.D, self.head, self.psi)
        self.flow_v = flow_from_phi(self.D, self.phi, self.speed)
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_eff_phi_psi_suc_torque_volume_ratio(self):
        self._calc_from_eff_phi_psi_suc_volume_ratio()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_eff_phi_power_losses_psi_suc_volume_ratio(self):
        self._calc_from_eff_phi_psi_suc_volume_ratio()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

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
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_eff_flow_v_head_speed_suc_torque(self):
        self._calc_from_eff_flow_v_head_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_eff_flow_v_head_power_losses_speed_suc(self):
        self._calc_from_eff_flow_v_head_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

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
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_eff_flow_m_head_speed_suc_torque(self):
        self._calc_from_eff_flow_m_head_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_eff_flow_m_head_power_losses_speed_suc(self):
        self._calc_from_eff_flow_m_head_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_eff_phi_psi_speed_suc(self):
        self.head = head_from_psi(self.D, self.psi, self.speed)
        self.disch = disch_from_suc_head_eff(self.suc, self.head, self.eff)
        self.flow_v = flow_from_phi(self.D, self.phi, self.speed)
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.volume_ratio = self.suc.v() / self.disch.v()
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_eff_phi_psi_speed_suc_torque(self):
        self._calc_from_eff_phi_psi_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_eff_phi_power_losses_psi_speed_suc(self):
        self._calc_from_eff_phi_psi_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_p_eff_flow_v_speed_suc(self):
        eff = self.eff
        suc = self.suc
        disch = disch_from_suc_disch_p_eff(suc, self.disch_p, eff)
        self.disch = disch
        self.head = self.head_calc_func(suc, disch, self._dummy_state)
        self.flow_m = self.flow_v * self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_p_eff_flow_v_speed_suc_torque(self):
        self._calc_from_disch_p_eff_flow_v_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_disch_p_eff_flow_v_power_losses_speed_suc(self):
        self._calc_from_disch_p_eff_flow_v_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_p_eff_flow_m_speed_suc(self):
        eff = self.eff
        suc = self.suc
        disch = disch_from_suc_disch_p_eff(suc, self.disch_p, eff)
        self.disch = disch
        self.head = self.head_calc_func(suc, disch, self._dummy_state)
        self.flow_v = self.flow_m / self.suc.rho()
        self.power = power_calc(self.flow_m, self.head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_p_eff_flow_m_speed_suc_torque(self):
        self._calc_from_disch_p_eff_flow_m_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_disch_p_eff_flow_m_power_losses_speed_suc(self):
        self._calc_from_disch_p_eff_flow_m_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_v_head_power_speed_suc(self):
        suc = self.suc
        head = self.head
        power = self.power
        self.flow_m = self.flow_v * self.suc.rho()
        self.eff = (self.flow_m * head / power).to("dimensionless")
        self.disch = disch_from_suc_head_eff(suc, head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_v_head_power_speed_suc_torque(self):
        self._calc_from_flow_v_head_power_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_flow_v_head_power_power_losses_speed_suc(self):
        self._calc_from_flow_v_head_power_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_m_head_power_speed_suc(self):
        suc = self.suc
        head = self.head
        power = self.power
        self.flow_v = self.flow_m / self.suc.rho()
        self.eff = (self.flow_m * head / power).to("dimensionless")
        self.disch = disch_from_suc_head_eff(suc, head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_m_head_power_speed_suc_torque(self):
        self._calc_from_flow_m_head_power_speed_suc()
        self.power_shaft = self.torque * self.speed
        self.power_losses = self.power_shaft - self.power

    def _calc_from_flow_m_head_power_power_losses_speed_suc(self):
        self._calc_from_flow_m_head_power_speed_suc()
        self.power_shaft = self.power + self.power_losses
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_v_head_power_shaft_speed_suc(self):
        suc = self.suc
        head = self.head
        power_shaft = self.power_shaft
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power = power_shaft - self.power_losses
        self.flow_m = self.flow_v * self.suc.rho()
        self.eff = (self.flow_m * head / self.power).to("dimensionless")
        self.disch = disch_from_suc_head_eff(suc, head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_m_head_power_shaft_speed_suc(self):
        suc = self.suc
        head = self.head
        power_shaft = self.power_shaft
        if not self.power_losses:
            self.power_losses = Q_(0, "watt")
        self.power = power_shaft - self.power_losses
        self.flow_v = self.flow_m / self.suc.rho()
        self.eff = (self.flow_m * head / self.power).to("dimensionless")
        self.disch = disch_from_suc_head_eff(suc, head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_v_head_power_losses_power_shaft_speed_suc(self):
        suc = self.suc
        head = self.head
        power_shaft = self.power_shaft
        self.power = power_shaft - self.power_losses
        self.flow_m = self.flow_v * self.suc.rho()
        self.eff = (self.flow_m * head / self.power).to("dimensionless")
        self.disch = disch_from_suc_head_eff(suc, head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.torque = self.power_shaft / self.speed

    def _calc_from_flow_m_head_power_losses_power_shaft_speed_suc(self):
        suc = self.suc
        head = self.head
        power_shaft = self.power_shaft
        self.power = power_shaft - self.power_losses
        self.flow_v = self.flow_m / self.suc.rho()
        self.eff = (self.flow_m * head / self.power).to("dimensionless")
        self.disch = disch_from_suc_head_eff(suc, head, self.eff)
        self.phi = phi(self.flow_v, self.speed, self.D)
        self.psi = psi(self.head, self.speed, self.D)
        self.volume_ratio = self.suc.v() / self.disch.v()
        self.torque = self.power_shaft / self.speed

    def _calc_from_disch_T_flow_v_pressure_ratio_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        pressure_ratio = self.pressure_ratio
        disch_p = suc.p() * pressure_ratio
        self.disch = State(p=disch_p, T=disch_T, fluid=suc.fluid)
        self._calc_from_disch_flow_v_speed_suc()

    def _calc_from_disch_T_flow_v_pressure_ratio_speed_suc_torque(self):
        suc = self.suc
        disch_T = self.disch_T
        pressure_ratio = self.pressure_ratio
        disch_p = suc.p() * pressure_ratio
        self.disch = State(p=disch_p, T=disch_T, fluid=suc.fluid)
        self._calc_from_disch_flow_v_speed_suc_torque()

    def _calc_from_disch_T_flow_v_power_losses_pressure_ratio_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        pressure_ratio = self.pressure_ratio
        disch_p = suc.p() * pressure_ratio
        self.disch = State(p=disch_p, T=disch_T, fluid=suc.fluid)
        self._calc_from_disch_flow_v_power_losses_speed_suc()

    def _calc_from_disch_T_flow_m_pressure_ratio_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        pressure_ratio = self.pressure_ratio
        disch_p = suc.p() * pressure_ratio
        self.disch = State(p=disch_p, T=disch_T, fluid=suc.fluid)
        self._calc_from_disch_flow_m_speed_suc()

    def _calc_from_disch_T_flow_m_pressure_ratio_speed_suc_torque(self):
        suc = self.suc
        disch_T = self.disch_T
        pressure_ratio = self.pressure_ratio
        disch_p = suc.p() * pressure_ratio
        self.disch = State(p=disch_p, T=disch_T, fluid=suc.fluid)
        self._calc_from_disch_flow_m_speed_suc_torque()

    def _calc_from_disch_T_flow_m_power_losses_pressure_ratio_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        pressure_ratio = self.pressure_ratio
        disch_p = suc.p() * pressure_ratio
        self.disch = State(p=disch_p, T=disch_T, fluid=suc.fluid)
        self._calc_from_disch_flow_m_power_losses_speed_suc()

    def _calc_from_disch_T_flow_v_head_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        head = self.head

        self.disch = disch_from_suc_disch_T_head(suc, disch_T, head)
        self._calc_from_disch_flow_v_speed_suc()

    def _calc_from_disch_T_flow_v_head_speed_suc_torque(self):
        suc = self.suc
        disch_T = self.disch_T
        head = self.head

        self.disch = disch_from_suc_disch_T_head(suc, disch_T, head)
        self._calc_from_disch_flow_v_speed_suc_torque()

    def _calc_from_disch_T_flow_v_head_power_losses_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        head = self.head

        self.disch = disch_from_suc_disch_T_head(suc, disch_T, head)
        self._calc_from_disch_flow_v_power_losses_speed_suc()

    def _calc_from_disch_T_flow_m_head_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        head = self.head

        self.disch = disch_from_suc_disch_T_head(suc, disch_T, head)
        self._calc_from_disch_flow_m_speed_suc()

    def _calc_from_disch_T_flow_m_head_speed_suc_torque(self):
        suc = self.suc
        disch_T = self.disch_T
        head = self.head

        self.disch = disch_from_suc_disch_T_head(suc, disch_T, head)
        self._calc_from_disch_flow_m_speed_suc_torque()

    def _calc_from_disch_T_flow_m_head_power_losses_speed_suc(self):
        suc = self.suc
        disch_T = self.disch_T
        head = self.head

        self.disch = disch_from_suc_disch_T_head(suc, disch_T, head)
        self._calc_from_disch_flow_m_power_losses_speed_suc()

    @classmethod
    @check_units
    def convert_from(
        cls,
        original_point,
        suc=None,
        find="speed",
        speed=None,
        reynolds_correction=False,
        **kwargs,
    ):
        """Convert point from an original point.

        The procedure to convert a point considering that the volume ratio will be the same,
        follows the following steps:
        1. Assume that eff_converted = eff_original and psi_converted = psi_original
        2. Assume that volume ratio will be the same to keep similarity
        3. Calculate discharge volume based on suction state and volume ratio
        4. Calculate discharge state using newton method to find the discharge pressure.
        Criterion for convergence is the polytropic efficiency.
        5. Calculate head based on the new discharge state
        6. Calculate speed based on head and psi

        This procedure is followed whe we have find="speed".

        Parameters
        ----------
        original_point : ccp.Point
            Original point from which the desired point will be converted.
        suc : ccp.State
            New suction state.
        find : str, optional
            If the calculation will find a new speed keeping constant volume ratio,
            or a new volume ratio for the desired speed.
            Options are "speed" or "volume_ratio", default is "speed".
        speed : float, pint.Quantity, optional
            Desired speed. If find="speed", this should be None.
        reynolds_correction : bool, optional
            If reynolds correction should be applied during the conversion.
            If True the ASME PTC 10 reynolds correction is applied

        The user must provide 3 of the 4 available arguments. The argument which is not
        provided will be calculated.
        """
        if speed is None:
            speed = original_point.speed

        power_losses = (
            original_point.power_losses * (speed / original_point.speed) ** 2.5
        )

        eff_converted = original_point.eff
        psi_converted = original_point.psi
        phi_converted = original_point.phi

        if reynolds_correction == "ptc1997":
            rem_corr_eff, rem_corr_psi, rem_corr_phi = correct_reynolds_1997(
                suc,
                speed,
                original_point,
            )
            eff_converted = rem_corr_eff * original_point.eff
            psi_converted = rem_corr_psi * original_point.psi
            phi_converted = rem_corr_phi * original_point.phi
        elif reynolds_correction == "ptc2022" or reynolds_correction is True:
            rem_corr_eff, rem_corr_psi, rem_corr_phi = correct_reynolds_2022(
                suc,
                speed,
                original_point,
            )
            eff_converted = rem_corr_eff * original_point.eff
            psi_converted = rem_corr_psi * original_point.psi
            phi_converted = rem_corr_phi * original_point.phi

        convert_point_options = {
            "speed": dict(
                suc=suc,
                eff=eff_converted,
                power_losses=power_losses,
                phi=phi_converted,
                psi=psi_converted,
                volume_ratio=original_point.volume_ratio,
                b=original_point.b,
                D=original_point.D,
                **kwargs,
            ),
            "volume_ratio": dict(
                suc=suc,
                eff=eff_converted,
                power_losses=power_losses,
                phi=phi_converted,
                psi=psi_converted,
                speed=speed,
                b=original_point.b,
                D=original_point.D,
                **kwargs,
            ),
        }

        converted_point = cls(**convert_point_options[find])
        converted_point.phi_ratio = original_point.phi / converted_point.phi
        converted_point.psi_ratio = original_point.psi / converted_point.psi
        converted_point.volume_ratio_ratio = (
            original_point.volume_ratio / converted_point.volume_ratio
        )
        converted_point.reynolds_ratio = (
            original_point.reynolds / converted_point.reynolds
        )
        converted_point.mach_diff = original_point.mach - converted_point.mach

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
            power_losses=str(self.power_losses),
            b=str(self.b),
            D=str(self.D),
        )

    @staticmethod
    def _dict_from_load(dict_parameters):
        """Change dict to format that can be used by load constructor."""
        suc = State(
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
        if 0 <= mmsp < 0.215:
            lower_limit = 0
            upper_limit = 0.286 + 0.75 * mmsp
        elif 0.215 <= mmsp <= 0.86:
            lower_limit = 1.266 * mmsp - 0.271
            upper_limit = 0.286 + 0.75 * mmsp
        elif mmsp > 0.86:
            lower_limit = mmsp - 0.042
            upper_limit = mmsp + 0.07
        else:
            raise ValueError("Mach number out of specified range.")

        if lower_limit < self.mach_diff + self.mach < upper_limit:
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

        The x-axis represents the Specified Machine Mach Number for the point.
        The y-axis represents the Test Machine Mach Number from the original point.

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
        mmsp_range = np.linspace(0, 1.2, 300)
        for mmsp in mmsp_range:
            mach_limits = self.mach_limits(mmsp)
            lower_limit.append(mach_limits["lower"])
            upper_limit.append(mach_limits["upper"])

        fig.add_trace(
            go.Scatter(
                x=mmsp_range, y=lower_limit, line=dict(color="blue", dash="dash")
            )
        )
        fig.add_trace(
            go.Scatter(x=mmsp_range, y=upper_limit, line=dict(color="red", dash="dash"))
        )

        # add point
        fig.add_trace(
            go.Scatter(
                x=[self.mach],
                y=[self.mach_diff + self.mach],
                marker=dict(color="black"),
                mode="markers",
                hovertemplate=(
                    "Specified Mach (Mm<sub>sp</sub>): %{x:.3f}<br>"
                    "Test Mach (Mm<sub>t</sub>): %{y:.3f}<extra></extra>"
                ),
            )
        )
        # subscripts for t and sp
        _t = "\u209c"
        _sp = "\u209b\u209a"
        space_str = "&nbsp;"
        fig.update_xaxes(
            title=f"Specified Machine Mach Number - Mm{_sp}",
        )
        fig.update_yaxes(
            title=f"Test Machine Mach Number - Mm{_t}",
        )
        fig.update_xaxes(
            range=[0, 1.2],
            tickformat=".1f",
            dtick=0.1,
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
        )
        fig.update_yaxes(
            range=[0, 1.2],
            tickformat=".1f",
            dtick=0.1,
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
        )
        # Upper Limit text
        upper_text = (
            "<b>Upper Limit</b><br>"
            f"Mm{_t} = (0.286 + 0.75·Mm{_sp}) {2 * space_str}for Mm{_sp} ≤ 0.86<br>"
            f"Mm{_t} = (Mm{_sp} + 0.07) {8 * space_str}for Mm{_sp} > 0.86"
        )

        # Lower Limit text
        lower_text = (
            "<b>Lower Limit</b><br>"
            f"Mm{_t} = 0 {20 * space_str}for Mm{_sp} < 0.215<br>"
            f"Mm{_t} = (1.266·Mm{_sp} - 0.271) {space_str}for 0.215 ≤ Mm{_sp} ≤ 0.86<br>"
            f"Mm{_t} = (Mm{_sp} - 0.042) {7 * space_str}for Mm{_sp} > 0.86"
        )

        # Annotation: Upper Limit (top-left corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            align="left",
            showarrow=False,
            text=upper_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
        )

        # Annotation: Lower Limit (bottom-right corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.08,
            xanchor="right",
            yanchor="bottom",
            align="left",
            showarrow=False,
            text=lower_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
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

        ul = 68.205 + 16.13 * np.log10(remsp) - 64.008 * np.sqrt(np.log10(remsp))
        if 9e4 <= remsp < 8e5:
            upper_limit = 10**ul
        elif remsp >= 8e5:
            upper_limit = remsp * 100
        else:
            raise ValueError("Reynolds number out of specified range.")

        ll = -22.733 - 4.247 * np.log10(remsp) + 21.63 * np.sqrt(np.log10(remsp))
        if 9e4 <= remsp < 5e5:
            lower_limit = 10**ll
        elif remsp >= 5e5:
            lower_limit = remsp * 0.1
        else:
            raise ValueError("Reynolds number out of specified range.")

        if lower_limit < self.reynolds_ratio * self.reynolds < upper_limit:
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

        The x-axis represents the Specified Machine Reynolds Number for the point.
        The y-axis represents the Test Machine Reynolds Number from the original point.

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
        remsp_range = np.geomspace(9e4, 1e10, 300)
        for remsp in remsp_range:
            reynolds_limits = self.reynolds_limits(remsp)
            lower_limit.append(reynolds_limits["lower"])
            upper_limit.append(reynolds_limits["upper"])

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=remsp_range, y=lower_limit, line=dict(color="blue", dash="dash")
            )
        )
        fig.add_trace(
            go.Scatter(
                x=remsp_range, y=upper_limit, line=dict(color="red", dash="dash")
            )
        )

        # add point
        fig.add_trace(
            go.Scatter(
                x=[self.reynolds.m],
                y=[self.reynolds_ratio * self.reynolds.m],
                marker=dict(color="black"),
                mode="markers",
                hovertemplate=(
                    "Specified Reynolds (Rem<sub>sp</sub>): %{x:.3e}<br>"
                    "Test Reynolds (Rem<sub>t</sub>): %{y:.3e}<extra></extra>"
                ),
            )
        )

        # subscripts for t and sp
        _t = "\u209c"
        _sp = "\u209b\u209a"
        space_str = "&nbsp;"
        fig.update_xaxes(
            type="log",
            tickformat=".1e",
            tickmode="array",
            tickvals=[10**i for i in range(4, 11)],  # Show tick labels only at 1eX
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
            minor=dict(
                tickvals=[j * 10**i for i in range(4, 11) for j in range(2, 10)],
                showgrid=True,
                gridcolor="rgba(200,200,200,0.4)",
                gridwidth=0.5,
            ),
            title=f"Specified Machine Reynolds Number- Rem{_sp}",
            range=[4, 10],
        )
        fig.update_yaxes(
            type="log",
            tickformat=".1e",
            tickmode="array",
            tickvals=[10**i for i in range(4, 13)],
            showgrid=True,
            gridcolor="lightgray",
            gridwidth=1,
            minor=dict(
                tickvals=[j * 10**i for i in range(4, 12) for j in range(2, 10)],
                showgrid=True,
                gridcolor="rgba(200,200,200,0.4)",
                gridwidth=0.5,
            ),
            title=f"Test Machine Reynolds Number - Rem{_t}",
            range=[4, 12],
        )

        # upper limit text
        upper_text = (
            "<b>Upper Limit</b><br>"
            f"Rem{_t} = 10<sup>ul</sup> {9 * space_str} for 9e4 ≤ Rem{_sp} < 8e5<br>"
            f"Rem{_t} = Rem{_sp} * 100 {space_str} for Rem{_sp} ≥ 8e5<br>"
            "where<br>"
            f"ul = 68.205 + 16.13 * log10(Rem{_sp})<br>"
            f"- 64.008 * \u221alog10(Rem{_sp})"
        )

        # lower limit text
        lower_text = (
            "<b>Lower Limit</b><br>"
            f"Rem{_t} = 10<sup>ll</sup> {10 * space_str}for 9e4 ≤ Rem{_sp} < 5e5<br>"
            f"Rem{_t} = Rem{_sp} * 0.1 {2 * space_str}for Rem{_sp} ≥ 5e5<br>"
            "where<br>"
            f"ll = -22.733 - 4.247 * log10(Rem{_sp})<br>"
            f"+ 21.63 * \u221alog10(Rem{_sp})"
        )

        # Annotation: Upper Limit (top-left corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.96,
            xanchor="left",
            yanchor="top",
            align="left",
            showarrow=False,
            text=upper_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
        )

        # Annotation: Lower Limit (bottom-right corner)
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.99,
            y=0.02,
            xanchor="right",
            yanchor="bottom",
            align="left",
            showarrow=False,
            text=lower_text,
            font=dict(size=10, family="monospace"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(0,0,0,0.45)",
            borderwidth=1,
            borderpad=6,
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
        abbrev = ["v<sub>i</sub> / v<sub>d</sub>", "Mm", "Rem"]
        point_value = [
            f"{self.volume_ratio.m:.3f}",
            f"{self.mach.m:.3f}",
            f"{self.reynolds.m:.3e}",
        ]
        formula = [
            "(v<sub>i</sub> / v<sub>d</sub>)<sub>c</sub> / (v<sub>i</sub> / v<sub>d</sub>)<sub>o</sub>",
            "Mm<sub>c</sub>",
            "Rem<sub>c</sub>",
        ]
        relation = [
            f"{self.volume_ratio_ratio.m:.3f}",
            f"{self.mach_diff.m + self.mach.m:.3f}",
            f"{self.reynolds_ratio.m * self.reynolds.m:.3e}",
        ]
        mach_limits = self.mach_limits()
        reynolds_limits = self.reynolds_limits()
        lower_limit = [
            0.95,
            f"{mach_limits['lower']:.3f}",
            f"{reynolds_limits['lower']:.3e}",
        ]
        upper_limit = [
            1.05,
            f"{mach_limits['upper']:.3f}",
            f"{reynolds_limits['upper']:.3e}",
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
                            "<b>Original Point Value</b>",
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
        color = kwargs.pop("color", None)

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

        fig.add_trace(
            go.Scatter(x=[flow_v], y=[value], name=name, marker_color=color, **plot_kws)
        )

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


def head_isentropic(suc, disch, disch_s=None):
    """Isentropic head.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be updated and used for calculations. If None, a copy of
        disch will be created.

    Returns
    -------
    head_isentropic : pint.Quantity
        Isentropic head.
    """
    # define state to isentropic discharge using dummy state
    if disch_s is None:
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


def f_schultz(suc, disch, disch_s=None):
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
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be updated and used for calculations. If None, a copy of
        disch will be created.

    Returns
    -------
    f_schultz : float
        Schultz polytropic factor.
    """

    # define state to isentropic discharge using dummy state
    if disch_s is None:
        disch_s = copy(disch)

    disch_s.update(p=disch.p(), s=suc.s())

    h2s_h1 = disch_s.h() - suc.h()
    h_isen = head_isentropic(suc, disch, disch_s)

    return h2s_h1 / h_isen


def head_pol_schultz(suc, disch, disch_s=None):
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
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be passed to f_schultz for reuse.

    Returns
    -------
    head_pol_schultz : pint.Quantity
        Schultz polytropic head (J/kg).
    """
    f = f_schultz(suc, disch, disch_s)
    head = head_pol(suc, disch)

    return f * head


def eff_pol_schultz(suc, disch, disch_s=None):
    """Polytropic efficiency as per :cite:`schultz1962`.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch : ccp.State
        Discharge state.
    disch_s : ccp.State, optional
        Reusable state object to avoid copying. If provided, this state
        will be passed to head_pol_schultz for reuse.

    Returns
    -------
    eff_pol_schultz : pint.Quantity
        Schultz polytropic efficiency (dimensionless).
    """
    wp = head_pol_schultz(suc, disch, disch_s)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_mallen_saville(suc, disch, disch_s=None):
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


def eff_pol_mallen_saville(suc, disch, disch_s=None):
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
        s1 = State(p=p1, T=T1, fluid=suc.fluid)
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
            s0 = State(p=p0, T=T0, fluid=suc.fluid)
            T1 = newton(
                calc_step_discharge_temp, (T0 + 1e-3), args=(p1, p0, s0.h(), s0.v(), e)
            )
            s1 = State(p=p1, T=T1, fluid=suc.fluid)
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

    state1 = ccp.State(p=suc.p(), s=suc.s(), fluid=suc.fluid)

    def calc_step_discharge_z(s1, s0, p1, p0, z0, R, e):
        state1.update(p=p1, s=s1)
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
            state0 = ccp.State(p=p0, s=s0, fluid=suc.fluid)
            z0 = state0.z()

            s1 = newton(calc_step_discharge_z, (s0 + 1e-8), args=(s0, p1, p0, z0, R, e))
            state1 = ccp.State(p=p1, s=s1, fluid=suc.fluid)
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


def head_pol_sandberg_colby(suc, disch, disch_s=None):
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
    Tm = (suc.T() + disch.T()) / 2
    h = (disch.h() - suc.h()) - Tm * (disch.s() - suc.s())
    return h


def head_pol_sandberg_colby_f(suc, disch, disch_s=None):
    r"""Polytropic head corrected by the :cite:`sandberg2013limitations` factor (original implementation).

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
    head_pol_sandberg_colby_f : pint.Quantity
       Reference head as described by :cite:`sandberg2013limitations` (J/kg).
    """
    f = f_sandberg_colby(suc, disch)
    h = f * head_pol(suc, disch)
    return h


def eff_pol_sandberg_colby(suc, disch, disch_s=None):
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


def eff_pol_sandberg_colby_f(suc, disch, disch_s=None):
    """Sandberg-Colby polytropic efficiency with correction factor."""
    wp = head_pol_sandberg_colby_f(suc, disch)
    dh = disch.h() - suc.h()

    return (wp / dh).to("dimensionless")


def head_pol_huntington(suc, disch, disch_s=None):
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


def eff_pol_huntington(suc, disch, disch_s=None):
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
        state3 = State(p=p3, T=T3, fluid=suc.fluid)
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
    D : float, pint.Quantity
        Impeller outer diameter (m).
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
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    psi : pint.Quantity
        Polytropic head coefficient (dimensionless).
    """
    u = u_calc(D, speed)
    psi = head / (u**2 / 2)
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
    D : float, pint.Quantity
        Impeller outer diameter (m).
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
    """Flow coefficient.

    Parameters
    ----------
    flow_v : float, pint.Quantity
        Impeller flow (m³/s).
    speed : float, pint.Quantity
        Impeller speed (rad/s).
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    phi : pint.Quantity
        Flow coefficient (dimensionless).
    """
    u = u_calc(D, speed)

    phi = flow_v * 4 / (np.pi * D**2 * u)

    return phi.to("dimensionless")


@check_units
def phi3(flow_v, speed, D, b):
    """Discharge flow coefficient.

    Eq. 5.13 from :cite:`ludtke2004process`

    Parameters
    ----------
    flow_v : float, pint.Quantity
        Impeller exit flow (m³/s).
    speed : float, pint.Quantity
        Impeller speed (rad/s).
    D : float, pint.Quantity
        Impeller outer diameter (m).
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).

    Returns
    -------
    phi : pint.Quantity
        Discharge flow coefficient (dimensionless).
    """
    u = u_calc(D, speed)

    phi = flow_v / (np.pi * D * b * u)

    return phi.to("dimensionless")


@check_units
def flow_from_phi(D, phi, speed):
    """Calculate flow from non dimensional phi.

    Parameters
    ----------
    D : float, pint.Quantity
        Impeller outer diameter (m).
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

    flow_v = phi * (np.pi * D**2 * u) / 4

    return flow_v.to("m**3/s")


def head_from_psi(D, psi, speed):
    """Calculate head from non dimensional psi.

    Parameters
    ----------
    D : float, pint.Quantity
        Impeller outer diameter (m).
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
    head = psi * (u**2 / 2)

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
    disch = State(h=h_disch, s=suc.s(), fluid=suc.fluid)

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

    disch = ccp.State(p=disch_p, s=suc.s(), fluid=suc.fluid)
    eff_calc_func = globals()[f"eff_pol_{polytropic_method}"]

    def update_state(x):
        disch.update(p=disch_p, T=x)
        new_eff = eff_calc_func(suc, disch)

        return (new_eff - eff).magnitude

    newton(update_state, disch.T().magnitude)

    return disch


def disch_from_suc_disch_T_head(suc, disch_T, head, polytropic_method=None):
    """Calculate discharge state from suction, discharge temperature and head.

    Parameters
    ----------
    suc : ccp.State
        Suction state.
    disch_T : pint.Quantity, float
        Discharge temperature (degK).
    head : pint.Quantity, float
        Polytropic head (J/kg).

    Returns
    -------
    disch : ccp.State
        Discharge state.
    """
    # consider first an isentropic compression
    if polytropic_method is None:
        polytropic_method = ccp.config.POLYTROPIC_METHOD

    disch = ccp.State(T=disch_T, s=suc.s(), fluid=suc.fluid)
    head_calc_func = globals()[f"head_pol_{polytropic_method}"]

    def update_state(x):
        disch.update(T=disch_T, p=x)
        new_head = head_calc_func(suc, disch)

        return (new_head - head).magnitude

    newton(update_state, disch.p().magnitude, tol=1e-7)

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
    b : float, pint.Quantity
        Impeller width at the outer blade diameter (m).
    D : float, pint.Quantity
        Impeller outer diameter (m).

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
    D : float, pint.Quantity
        Impeller outer diameter (m).

    Returns
    -------
    mach : pint.Quantity
        Mach number (dimensionless).
    """
    u = u_calc(D, speed)
    a = suc.speed_sound()
    ma = u / a

    return ma.to("dimensionless")


def correct_reynolds_1997(suc, speed, original_point):
    """Correct the efficiency based on ASME PTC 10 1997.

    Parameters
    ----------
    suc : ccp.State
        New suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    original_point : ccp.Point
        Original operating point.

    Returns
    -------
    rem_corr_eff, rem_corr_psi, rem_corr_phi
        Correction factors for eff, psi and phi.
    """
    rc_original = 0.988 / original_point.reynolds**0.243
    rb_original = np.log(0.000125 + 13.67 / original_point.reynolds) / np.log(
        original_point.surface_roughness.to("in").m + (13.67 / original_point.reynolds)
    )
    ra_original = (
        0.066
        + 0.934
        * ((4.8e6 * original_point.b.to("ft").m) / original_point.reynolds)
        ** rc_original
    )
    reynolds_converted = reynolds(
        suc=suc, speed=speed, b=original_point.b, D=original_point.D
    )
    rc_converted = 0.988 / reynolds_converted**0.243
    rb_converted = np.log(0.000125 + 13.67 / reynolds_converted) / np.log(
        original_point.surface_roughness.to("in").m + (13.67 / reynolds_converted)
    )
    ra_converted = (
        0.066
        + 0.934
        * ((4.8e6 * original_point.b.to("ft").m) / reynolds_converted) ** rc_converted
    )

    eff_converted = 1 - (1 - original_point.eff) * (ra_converted / ra_original) * (
        rb_converted / rb_original
    )

    rem_corr_eff = rem_corr_psi = eff_converted / original_point.eff
    rem_corr_phi = 1

    return rem_corr_eff, rem_corr_psi, rem_corr_phi


def correct_reynolds_2022(suc, speed, original_point):
    """Correct efficiency, head coefficient and flow coefficient based on ASME PTC 10 2022.

    Parameters
    ----------
    suc : ccp.State
        New suction state.
    speed : pint.Quantity, float
        Impeller speed (rad/s).
    original_point : ccp.Point
        Original operating point.

    Returns
    -------
    rem_corr_eff, rem_corr_psi, rem_corr_phi
        Correction factors for eff, psi and phi.

    """
    ra = original_point.surface_roughness
    reynolds_converted = reynolds(
        suc=suc, speed=speed, b=original_point.b, D=original_point.D
    )

    lambda_inf = (
        1.74 - 2 * np.log10(2 * original_point.surface_roughness / original_point.b)
    ) ** (-2)

    def colebrook(lamda, reynolds):
        return (
            1 / np.sqrt(lamda)
            + 2
            * np.log10(
                1 + (18.7 * original_point.b) / (reynolds * 2 * ra * np.sqrt(lamda))
            )
            - 1 / np.sqrt(lambda_inf)
        )

    lambda_t = newton(colebrook, x0=lambda_inf, args=(original_point.reynolds,))
    lambda_sp = newton(colebrook, x0=lambda_inf, args=(reynolds_converted,))

    rem_corr_eff = 1 / original_point.eff + (1 - 1 / original_point.eff) * (
        (0.3 + 0.7 * lambda_sp / lambda_inf) / (0.3 + 0.7 * lambda_t / lambda_inf)
    )
    rem_corr_psi = 0.5 + 0.5 * rem_corr_eff
    rem_corr_phi = np.sqrt(rem_corr_psi)

    return rem_corr_eff, rem_corr_psi, rem_corr_phi
