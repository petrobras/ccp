"""Module to define compressors with 1 or 2 sections."""
from copy import copy

import ccp
from ccp.impeller import Impeller
from ccp.point import Point, flow_from_phi
from ccp.state import State
from ccp.config.units import check_units
from ccp import Q_
import numpy as np


class Point1Sec(Point):
    """Point class for a compressor with 1 section.

    Parameters
    ----------
    balance_line_flow_m : float, pint.Quantity
        Balance line mass flow (kg/s).
    seal_gas_flow_m : float, pint.Quantity
        Seal gas mass flow (kg/s).
    seal_gas_temperature : float, pint.Quantity
        Seal gas injection temperature (degK).
    oil_flow_journal_bearing_de : float, pint.Quantity
        Oil flow journal bearing drive end side (m³/s).
    oil_flow_journal_bearing_nde : float, pint.Quantity
        Oil flow journal bearing non-drive end side (m³/s).
    oil_flow_thrust_bearing_nde : float, pint.Quantity
         Oil flow journal bearing thrust bearing (m³/s).
    oil_inlet_temperature : float, pint.Quantity
        Oil inlet temperature (degK).
    oil_outlet_temperature_de : float, pint.Quantity
        Oil outlet temperature journal bearing drive end side (degK).
    oil_outlet_temperature_nde : float, pint.Quantity
        Oil outlet temperature bearing non-drive end side (degK).

    Returns
    -------
    point1sec : ccp.Point1Sec
        A point for a straight through compressor (inherited from ccp.Point).

    Examples
    --------
    >>> import ccp
    >>> p = Point1Sec(
    ...     flow_m=Q_(7.737, "kg/s"),
    ...     speed=Q_(7894, "RPM"),
    ...     b=Q_(28.5, "mm"),
    ...     D=Q_(365, "mm"),
    ...     suc=State.define(
    ...         p=Q_(1.826, "bar"),
    ...         T=Q_(296.7, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 0.80218,
    ...             "R134a": 0.18842,
    ...             "nitrogen": 0.0091,
    ...             "oxygen": 0.0003,
    ...         },
    ...     ),
    ...     disch=State.define(
    ...         p=Q_(6.142, "bar"),
    ...         T=Q_(392.1, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 0.80218,
    ...             "R134a": 0.18842,
    ...             "nitrogen": 0.0091,
    ...             "oxygen": 0.0003,
    ...         },
    ...     ),
    ...     balance_line_flow_m=Q_(0.1076, "kg/s"),
    ...     seal_gas_flow_m=Q_(0.04982, "kg/s"),
    ...     seal_gas_temperature=Q_(297.7, "degK"),
    ...     oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
    ...     oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
    ...     oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
    ...     oil_inlet_temperature=Q_(42.184, "degC"),
    ...     oil_outlet_temperature_de=Q_(48.111, "degC"),
    ...     oil_outlet_temperature_nde=Q_(46.879, "degC"),
    ...     casing_area=7.5,
    ...     casing_temperature=Q_(31.309, "degC"),
    ...     ambient_temperature=Q_(0, "degC"),
    ...     )

    """

    @check_units
    def __init__(
        self,
        *args,
        balance_line_flow_m=None,
        seal_gas_flow_m=None,
        seal_gas_temperature=None,
        oil_flow_journal_bearing_de=None,
        oil_flow_journal_bearing_nde=None,
        oil_flow_thrust_bearing_nde=None,
        oil_inlet_temperature=None,
        oil_outlet_temperature_de=None,
        oil_outlet_temperature_nde=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        self.balance_line_flow_m = balance_line_flow_m
        self.seal_gas_flow_m = seal_gas_flow_m
        self.seal_gas_temperature = seal_gas_temperature
        self.oil_flow_journal_bearing_de = oil_flow_journal_bearing_de
        self.oil_flow_journal_bearing_nde = oil_flow_journal_bearing_nde
        self.oil_flow_thrust_bearing_nde = oil_flow_thrust_bearing_nde
        self.oil_inlet_temperature = oil_inlet_temperature
        self.oil_outlet_temperature_de = oil_outlet_temperature_de
        self.oil_outlet_temperature_nde = oil_outlet_temperature_nde


class StraightThrough(Impeller):
    """Straight Through compressor"""

    @check_units
    def __init__(self, guarantee_point, test_points, speed=None):
        self.guarantee_point = guarantee_point
        self.test_points = test_points
        if speed is None:
            speed = guarantee_point.speed
        self.speed = speed

        # points for test flange conditions
        self.points_flange_t = test_points

        # calculate rotor condition
        test_points_rotor = []
        self.k_end_seal = []  # list with seal constants
        for point in test_points:
            ms1f = point.flow_m
            mbal = point.balance_line_flow_m
            mseal = point.seal_gas_flow_m

            mend = mbal - (0.95 * mseal) / 2
            ms1r = ms1f + mend

            Ts1f = point.suc.T()
            # dummy state to calculate Tend
            dummy_state = copy(point.disch)
            dummy_state.update(p=point.suc.p(), h=dummy_state.h())
            Tend = dummy_state.T()
            Tseal = point.seal_gas_temperature
            Ts1r = (ms1f * Ts1f + mend * Tend + 0.95 * mseal * Tseal) / (
                ms1f + mend + 0.95 * mseal
            )
            point.Ts1r = Ts1r
            k_end = k_seal(flow_m=mend, state_up=point.disch, state_down=point.suc)
            self.k_end_seal.append(k_end)
            suc_rotor = State.define(
                p=point.suc.p(), T=point.Ts1r, fluid=point.suc.fluid
            )
            test_points_rotor.append(
                Point(
                    suc=suc_rotor,
                    disch=point.disch,
                    flow_m=ms1r,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                    casing_area=point.casing_area,
                    casing_temperature=point.casing_temperature,
                    ambient_temperature=point.ambient_temperature,
                )
            )

        self.points_rotor_t = test_points_rotor

        # convert points_rotor_t to points_rotor_sp
        self.points_rotor_sp = []
        self.points_flange_sp = []
        # calculate ms1r for the guarantee point
        for point, k in zip(self.points_rotor_t, self.k_end_seal):
            error = 1
            # initial estimate of Ts1r_sp with Ts1f_sp
            Ts1r_sp = guarantee_point.suc.T()
            initial_suc = copy(guarantee_point.suc)
            i = 0
            while error > 1e-5 and i < 5:
                initial_suc.update(p=initial_suc.p(), T=Ts1r_sp)
                initial_point_rotor_sp = Point.convert_from(
                    original_point=point,
                    suc=initial_suc,
                    speed=self.speed,
                    find="volume_ratio",
                )
                ms1r_sp = initial_point_rotor_sp.flow_m
                mend_sp = flow_m_seal(
                    k,
                    state_up=initial_point_rotor_sp.disch,
                    state_down=initial_point_rotor_sp.suc,
                )
                ms1f_sp = ms1r_sp - mend_sp
                Ts1f_sp = guarantee_point.suc.T()
                # dummy state to calculate Tend
                dummy_state = copy(initial_point_rotor_sp.disch)
                dummy_state.update(p=initial_point_rotor_sp.suc.p(), h=dummy_state.h())
                Tend_sp = dummy_state.T()
                Ts1r_sp_new = (ms1f_sp * Ts1f_sp + mend_sp * Tend_sp) / (
                    ms1f_sp + mend_sp
                )
                i += 1
                error = abs(Ts1r_sp_new.m - Ts1r_sp.m)
                Ts1r_sp = Ts1r_sp_new
            self.points_rotor_sp.append(initial_point_rotor_sp)
            self.points_flange_sp.append(
                Point(
                    suc=guarantee_point.suc,
                    disch=initial_point_rotor_sp.disch,
                    flow_m=ms1f_sp,
                    speed=speed,
                    b=guarantee_point.b,
                    D=guarantee_point.D,
                )
            )

        super().__init__(self.points_flange_sp)


class Point2Sec(Point):
    """Point class for a compressor with 2 sections in a back-to-back configuration.

    Parameters
    ----------
    balance_line_flow_m : float, pint.Quantity
        Balance line mass flow (kg/s).
    seal_gas_flow_m : float, pint.Quantity
        Seal gas mass flow (kg/s).
    seal_gas_temperature : float, pint.Quantity
        Seal gas injection temperature (degK).
    first_section_discharge_flow_m : float, pint.Quantity
        First section discharge mass flow (kg/s).
    div_wall_flow_m : float, pint.Quantity
        Division wall mass flow (kg/s).
    end_seal_upstream_temperature : float, pint.Quantity
        Temperature upstream the end seal (degK).
    end_seal_upstream_pressure : float, pint.Quantity
        Pressure upstream the end seal (Pa).
    div_wall_upstream_temperature : float, pint.Quantity
        Temperature upstream the division wall (degK).
    div_wall_upstream_pressure : float, pint.Quantity
         Pressure upstream the division wall (Pa).
    oil_flow_journal_bearing_de : float, pint.Quantity
        Oil flow journal bearing drive end side (m³/s).
    oil_flow_journal_bearing_nde : float, pint.Quantity
        Oil flow journal bearing non-drive end side (m³/s).
    oil_flow_thrust_bearing_nde : float, pint.Quantity
         Oil flow journal bearing thrust bearing (m³/s).
    oil_inlet_temperature : float, pint.Quantity
        Oil inlet temperature (degK).
    oil_outlet_temperature_de : float, pint.Quantity
        Oil outlet temperature journal bearing drive end side (degK).
    oil_outlet_temperature_nde : float, pint.Quantity
        Oil outlet temperature bearing non-drive end side (degK).

    Returns
    -------
    point1sec : ccp.Point1Sec
        A point for a straight through compressor (inherited from ccp.Point).

    Examples
    --------
    >>> import ccp
    >>> p = Point2Sec(
    ...     flow_m=Q_(4.325, "kg/s"),
    ...     speed=Q_(9096, "RPM"),
    ...     b=Q_(10.5, "mm"),
    ...     D=Q_(365, "mm"),
    ...     suc=State.define(
    ...         p=Q_(5.182, "bar"),
    ...         T=Q_(299.5, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 1,
    ...         },
    ...     ),
    ...     disch=State.define(
    ...         p=Q_(14.95, "bar"),
    ...         T=Q_(397.6, "degK"),
    ...         fluid={
    ...             "carbon dioxide": 1,
    ...         },
    ...     ),
    ...     balance_line_flow_m=Q_(0.1625, "kg/s"),
    ...     seal_gas_flow_m=Q_(0.0616, "kg/s"),
    ...     seal_gas_temperature=299.7,
    ...     first_section_discharge_flow_m=4.8059,
    ...     div_wall_flow_m=None,
    ...     end_seal_upstream_temperature=304.3,
    ...     end_seal_upstream_pressure=14.59,
    ...     div_wall_upstream_temperature=362.5,
    ...     div_wall_upstream_pressure=26.15,
    ...     oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
    ...     oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
    ...     oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
    ...     oil_inlet_temperature=Q_(41.544, "degC"),
    ...     oil_outlet_temperature_de=Q_(49.727, "degC"),
    ...     oil_outlet_temperature_nde=Q_(50.621, "degC"),
    ...     casing_area=5.5,
    ...     casing_temperature=Q_(23.895, "degC"),
    ...     ambient_temperature=Q_(0, "degC"),
    ... )
    """

    @check_units
    def __init__(
        self,
        *args,
        balance_line_flow_m=None,
        seal_gas_flow_m=None,
        seal_gas_temperature=None,
        first_section_discharge_flow_m=None,
        div_wall_flow_m=None,
        end_seal_upstream_temperature=None,
        end_seal_upstream_pressure=None,
        div_wall_upstream_temperature=None,
        div_wall_upstream_pressure=None,
        oil_flow_journal_bearing_de=None,
        oil_flow_journal_bearing_nde=None,
        oil_flow_thrust_bearing_nde=None,
        oil_inlet_temperature=None,
        oil_outlet_temperature_de=None,
        oil_outlet_temperature_nde=None,
        **kwargs,
    ):
        super().__init__(
            *args,
            **kwargs,
        )
        self.balance_line_flow_m = balance_line_flow_m
        self.seal_gas_flow_m = seal_gas_flow_m
        self.seal_gas_temperature = seal_gas_temperature
        self.first_section_discharge_flow_m = first_section_discharge_flow_m
        self.div_wall_flow_m = div_wall_flow_m
        self.end_seal_upstream_temperature = end_seal_upstream_temperature
        self.end_seal_upstream_pressure = end_seal_upstream_pressure
        self.div_wall_upstream_temperature = div_wall_upstream_temperature
        self.div_wall_upstream_pressure = div_wall_upstream_pressure
        self.oil_flow_journal_bearing_de = oil_flow_journal_bearing_de
        self.oil_flow_journal_bearing_nde = oil_flow_journal_bearing_nde
        self.oil_flow_thrust_bearing_nde = oil_flow_thrust_bearing_nde
        self.oil_inlet_temperature = oil_inlet_temperature
        self.oil_outlet_temperature_de = oil_outlet_temperature_de
        self.oil_outlet_temperature_nde = oil_outlet_temperature_nde

        self.end_seal_upstream_state = State.define(
            p=self.end_seal_upstream_pressure,
            T=self.end_seal_upstream_temperature,
            fluid=self.suc.fluid,
        )
        self.end_seal_downstream_state = copy(self.suc)
        self.end_seal_downstream_state.update(
            p=self.end_seal_downstream_state.p(), h=self.end_seal_upstream_state.h()
        )

        self.div_wall_upstream_state = State.define(
            p=self.div_wall_upstream_pressure,
            T=self.div_wall_upstream_temperature,
            fluid=self.suc.fluid,
        )
        self.div_wall_downstream_state = copy(self.disch)
        self.div_wall_downstream_state.update(
            p=self.div_wall_downstream_state.p(), h=self.div_wall_upstream_state.h()
        )


class BackToBack(Impeller):
    """Back to Back compressor"""

    @check_units
    def __init__(
        self,
        guarantee_point_sec1,
        test_points_sec1,
        guarantee_point_sec2,
        test_points_sec2,
        speed=None,
    ):
        self.guarantee_point_sec1 = guarantee_point_sec1
        self.guarantee_point_sec2 = guarantee_point_sec2
        self.test_points_sec1 = test_points_sec1
        self.test_points_sec2 = test_points_sec2
        if speed is None:
            speed = guarantee_point_sec1.speed
        self.speed = speed

        # points for test flange conditions
        self.points_flange_t_sec1 = test_points_sec1

        # calculate rotor condition
        test_points_sec1_rotor = np.full(len(test_points_sec1), np.nan, dtype=np.object)
        self.k_end_seal = np.zeros(
            len(test_points_sec1), dtype=np.object
        )  # array with seal constants
        self.k_div_wall = np.zeros(
            len(test_points_sec1), dtype=np.object
        )  # array with div wall seal constants
        for i, point in enumerate(test_points_sec1):
            if point.first_section_discharge_flow_m:
                md1f_t = point.first_section_discharge_flow_m
                ms1f_t = point.flow_m
                mbal_t = point.balance_line_flow_m
                mseal_t = point.seal_gas_flow_m
                mend_t = mbal_t - (0.95 * mseal_t) / 2
                point.end_seal_flow_m = mend_t
                mdiv_t = md1f_t - ms1f_t - mend_t - 0.95 * mseal_t
                point.div_wall_flow_m = mdiv_t
                ms1r_t = ms1f_t + mend_t + 0.95 * mseal_t

                ps1f_t = point.suc.p()
                Ts1f_t = point.suc.T()

                pd1f_t = point.disch.p()
                Td1f_t = point.disch.T()
                pd2f_t = point.div_wall_upstream_pressure
                Td2f_t = point.div_wall_upstream_temperature
                Tseal_t = point.seal_gas_temperature

                Tend_t = point.end_seal_downstream_state.T()

                k_end = k_seal(
                    flow_m=mend_t,
                    state_up=point.end_seal_upstream_state,
                    state_down=point.end_seal_downstream_state,
                )
                self.k_end_seal[i] = k_end

                k_div_wall = k_seal(
                    flow_m=mdiv_t,
                    state_up=point.div_wall_upstream_state,
                    state_down=point.div_wall_downstream_state,
                )
                self.k_div_wall[i] = k_div_wall
                Tdiv_t = point.div_wall_downstream_state.T()
                Ts1r_t = (
                    ms1f_t * Ts1f_t + mend_t * Tend_t + 0.95 * mseal_t * Tseal_t
                ) / (ms1f_t + mend_t + 0.95 * mseal_t)
                Td1r_t = (md1f_t * Td1f_t - mdiv_t * Tdiv_t) / (md1f_t - mdiv_t)
                suc_sec1_rotor_t = State.define(
                    p=ps1f_t, T=Ts1r_t, fluid=point.suc.fluid
                )
                disch_sec1_rotor_t = State.define(
                    p=pd1f_t, T=Td1r_t, fluid=point.suc.fluid
                )

                test_points_sec1_rotor[i] = Point(
                    suc=suc_sec1_rotor_t,
                    disch=disch_sec1_rotor_t,
                    flow_m=ms1r_t,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                    casing_area=point.casing_area,
                    casing_temperature=point.casing_temperature,
                    ambient_temperature=point.ambient_temperature,
                )

        for i, point in enumerate(test_points_sec1):
            if not point.first_section_discharge_flow_m:
                # use calculated k_end_seal and k_div_wall to calculate seal mass flow
                # use manual mean, since np.mean removes the units
                k_end_seal_mean = sum(self.k_end_seal[self.k_end_seal != 0]) / len(
                    self.k_end_seal[self.k_end_seal != 0]
                )
                self.k_end_seal[i] = k_end_seal_mean
                end_seal_flow_m = flow_m_seal(
                    k_seal=k_end_seal_mean,
                    state_up=point.end_seal_upstream_state,
                    state_down=point.end_seal_downstream_state,
                )
                k_div_wall_mean = sum(self.k_div_wall[self.k_div_wall != 0]) / len(
                    self.k_div_wall[self.k_div_wall != 0]
                )
                self.k_div_wall[i] = k_div_wall_mean
                div_wall_flow_m = flow_m_seal(
                    k_seal=k_div_wall_mean,
                    state_up=point.div_wall_upstream_state,
                    state_down=point.div_wall_downstream_state,
                )

                # calculate balance line and rotor suction flow
                mseal_t = point.seal_gas_flow_m
                mend_t = end_seal_flow_m
                point.end_seal_flow_m = mend_t

                mbal_t = mend_t + (0.95 * mseal_t) / 2
                point.balance_line_flow_m = mbal_t

                ms1f_t = point.flow_m
                ms1r_t = ms1f_t + mend_t + 0.95 * mseal_t

                # calculate discharge flow
                mdiv_t = div_wall_flow_m
                point.div_wall_flow_m = mdiv_t
                md1f_t = mdiv_t + ms1f_t + mend_t + 0.95 * mseal_t
                point.first_section_discharge_flow_m = md1f_t

                Ts1f_t = point.suc.T()
                Tend_t = point.end_seal_downstream_state.T()
                Tdiv_t = point.div_wall_downstream_state.T()
                Tseal_t = point.seal_gas_temperature
                Td1f_t = point.disch.T()
                ps1f_t = point.suc.p()
                pd1f_t = point.disch.p()

                Ts1r_t = (
                    ms1f_t * Ts1f_t + mend_t * Tend_t + 0.95 * mseal_t * Tseal_t
                ) / (ms1f_t + mend_t + 0.95 * mseal_t)
                Td1r_t = (md1f_t * Td1f_t - mdiv_t * Tdiv_t) / (md1f_t - mdiv_t)

                suc_sec1_rotor_t = State.define(
                    p=ps1f_t, T=Ts1r_t, fluid=point.suc.fluid
                )
                disch_sec1_rotor_t = State.define(
                    p=pd1f_t, T=Td1r_t, fluid=point.suc.fluid
                )

                test_points_sec1_rotor[i] = Point(
                    suc=suc_sec1_rotor_t,
                    disch=disch_sec1_rotor_t,
                    flow_m=ms1r_t,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                    casing_area=point.casing_area,
                    casing_temperature=point.casing_temperature,
                    ambient_temperature=point.ambient_temperature,
                )

        self.points_rotor_t_sec1 = test_points_sec1_rotor

        # convert points_rotor_t to points_rotor_sp
        self.points_rotor_sp_sec1 = []
        self.points_flange_sp_sec1 = []
        # calculate ms1r for the guarantee point
        for point, k_end_seal, k_div_wall in zip(
            self.points_rotor_t_sec1, self.k_end_seal, self.k_div_wall
        ):
            initial_point = Point.convert_from(
                original_point=point,
                suc=guarantee_point_sec1.suc,
                speed=self.speed,
                find="volume_ratio",
            )

            # determine rotor specified suction state
            end_seal_state_upstream_sp = State.define(
                p=initial_point.disch.p(),
                T=guarantee_point_sec2.suc.T(),
                fluid=initial_point.suc.fluid,
            )
            end_seal_state_downstream_sp = copy(initial_point.disch)
            end_seal_state_downstream_sp.update(
                p=guarantee_point_sec1.suc.p(), h=end_seal_state_upstream_sp.h()
            )
            Tend_sp = end_seal_state_downstream_sp.T()

            mend_sp = flow_m_seal(
                k_seal=k_end_seal,
                state_up=end_seal_state_upstream_sp,
                state_down=end_seal_state_downstream_sp,
            )

            Ts1f_sp = guarantee_point_sec1.suc.T()
            qs1r_sp = flow_from_phi(D=point.D, phi=point.phi, speed=self.speed)
            ps1r_sp = guarantee_point_sec1.suc.p()
            vs1f_sp = guarantee_point_sec1.suc.v()
            dummy_suc = copy(guarantee_point_sec1.suc)

            error = 1
            dm = Q_(1, "kg/s")
            ms1f_sp = qs1r_sp / vs1f_sp  # initial guess
            while error > 0.00001:
                ms1r_sp = ms1f_sp + mend_sp
                Ts1r_sp = (mend_sp * Tend_sp + ms1f_sp * Ts1f_sp) / ms1r_sp
                dummy_suc.update(p=ps1r_sp, T=Ts1r_sp)
                vs1r_sp = dummy_suc.v()
                qs1r_sp_1 = ms1r_sp * vs1r_sp

                fx = -qs1r_sp + qs1r_sp_1
                ms1f_sp_new = ms1f_sp + dm
                ms1r_sp_new = ms1f_sp_new + mend_sp
                Ts1r_sp_new = (ms1f_sp_new * Ts1f_sp + mend_sp * Tend_sp) / ms1r_sp_new
                dummy_suc.update(p=ps1r_sp, T=Ts1r_sp_new)
                vs1r_sp_new = dummy_suc.v()
                qs1r_sp_1_new = ms1r_sp_new * vs1r_sp_new
                dfx = (qs1r_sp_1_new - qs1r_sp_1) / dm
                ms1f_sp = ms1f_sp - (fx / dfx)
                error = ((fx**2) ** 0.5).m

            rotor_sp_sec1_suc = ccp.State.define(
                p=guarantee_point_sec1.suc.p(),
                T=Ts1r_sp,
                fluid=guarantee_point_sec1.suc.fluid,
            )
            point_rotor = Point.convert_from(
                original_point=point,
                suc=rotor_sp_sec1_suc,
                speed=self.speed,
                find="volume_ratio",
            )
            self.points_rotor_sp_sec1.append(point_rotor)

            # calculate div wall flow

            # calculate flange disch
            Td1r_sp = point_rotor.disch.T()
            Td1f_sp = ms1r_sp * Td1r_sp
            point_flange = Point(
                suc=guarantee_point_sec1.suc,
            )


@check_units
def k_seal(flow_m, state_up, state_down):
    """Function to calculate the seal constant k.

    This seal constant is used to estimate the seal leakage in different conditions.

    Parameters
    ----------
    flow_m : float, pint.Quantity
        Mass flow through the seal (kg/s).
    state_up : ccp.State
        State upstream of the seal.
    state_down : ccp.State
        State downstream of the seal.

    Returns
    -------
    k_end_seal : pint.Quantity
        Seal constant (kelvin ** 0.5 * kilogram ** 0.5 * mole ** 0.5 / pascal / second).
    """
    p_up = state_up.p()
    z_up = state_up.z()
    T_up = state_up.T()
    MW = state_up.molar_mass()
    p_down = state_down.p()

    k = (flow_m * np.sqrt(z_up * T_up / MW)) / (
        p_up * np.sqrt(1 - (p_down / p_up) ** 2)
    )

    return k


@check_units
def flow_m_seal(k_seal, state_up, state_down):
    """Function to calculate the seal constant k.

    This seal constant is used to estimate the seal leakage in different conditions.

    Parameters
    ----------
    k_seal : pint.Quantity
        Seal constant (kelvin ** 0.5 * kilogram ** 0.5 * mole ** 0.5 / pascal / second).
    state_up : ccp.State
        State upstream of the seal.
    state_down : ccp.State
        State downstream of the seal.

    """
    p_up = state_up.p()
    z_up = state_up.z()
    T_up = state_up.T()
    MW = state_up.molar_mass()
    p_down = state_down.p()

    flow_m_seal = (
        k_seal
        * p_up
        * (np.sqrt(1 - (p_down / p_up) ** 2))
        / (np.sqrt(z_up * T_up / MW))
    )

    return flow_m_seal
