"""Module to define compressors with 1 or 2 sections."""
from copy import copy
from ccp.impeller import Impeller
from ccp.point import Point
from ccp.state import State
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
            *args,
            **kwargs,
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


class StraightThrough:
    """Straight Through compressor"""

    def __init__(self, guarantee_point, test_points):
        self.guarantee_point = guarantee_point
        self.test_points = test_points

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
            zd1f = point.disch.z()
            Td1f = point.disch.T()
            MW1f = point.disch.molar_mass()
            ps1f = point.suc.p()
            pd1f = point.disch.p()
            k_end = (
                mend
                * np.sqrt(zd1f * Td1f / MW1f)
                / (pd1f * np.sqrt(1 - (ps1f / pd1f) ** 2))
            )
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
        self.points_rotor_sp = [
            Point.convert_from(
                point,
                suc=guarantee_point.suc,
                speed=guarantee_point.speed,
                find="volume_ratio",
            )
            for point in self.points_rotor_t
        ]
