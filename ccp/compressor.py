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
    """Point class for a compressor with 1 section."""

    def __init__(
        self,
        *args,
        balance_line_flow=None,
        seal_gas_flow=None,
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
            *args, **kwargs,
        )
        self.balance_line_flow = balance_line_flow
        self.seal_gas_flow = seal_gas_flow
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
        self.k_seal = []  # list with seal constants
        for point in test_points:
            ms1f = point.flow_m
            mbal = point.balance_line_flow
            mseal = point.seal_gas_flow

            mend = mbal - (0.95 * mseal) / 2
            point.mend = mend
            point.ms1r = ms1f + mend

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
            self.k_seal.append(k_end)
            suc_rotor = State.define(
                p=point.suc.p(), T=point.Ts1r, fluid=point.suc.fluid
            )
            test_points_rotor.append(
                Point(
                    suc=suc_rotor,
                    disch=point.disch,
                    flow_m=point.ms1r,
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
        for point, k in zip(self.points_rotor_t, self.k_seal):
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
    k_seal : pint.Quantity
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
