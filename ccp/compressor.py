"""Module to define compressors with 1 or 2 sections."""
from copy import copy
from ccp.impeller import Impeller
from ccp.point import Point
from ccp.state import State
from ccp import Q_


class Point1Sec(Point):
    """Point class for a compressor with 1 section."""

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
        pressure_ratio=None,
        disch_T=None,
        b=None,
        D=None,
        polytropic_method=None,
        balance_line_flow=None,
        seal_gas_flow=None,
        seal_gas_temperature=None,
        oil_flow_journal_bearing_de=None,
        oil_flow_journal_bearing_nde=None,
        oil_flow_thrust_bearing_nde=None,
        oil_inlet_temperature=None,
        oil_outlet_temperature_de=None,
        oil_outlet_temperature_nde=None,
        casing_area=None,
        casing_temperature=None,
        ambient_temperature=None,
        convection_constant=Q_(13.6, "W/(m²*degK)"),
    ):
        super().__init__(
            suc=suc,
            disch=disch,
            disch_p=disch_p,
            flow_v=flow_v,
            flow_m=flow_m,
            speed=speed,
            head=head,
            eff=eff,
            power=power,
            phi=phi,
            psi=psi,
            volume_ratio=volume_ratio,
            pressure_ratio=pressure_ratio,
            disch_T=disch_T,
            b=b,
            D=D,
            casing_area=casing_area,
            casing_temperature=casing_temperature,
            ambient_temperature=ambient_temperature,
            convection_constant=convection_constant,
            polytropic_method=polytropic_method,
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

        for point in test_points:
            ms1f = point.flow_m
            mbal = point.balance_line_flow
            mseal = point.seal_gas_flow

            mend = mbal - (0.95 * mseal) / 2
            ms1r = ms1f + mbal + (0.95 * mseal) / 2

            Ts1f = point.suc.T()
            # dummy state to calculate Tend
            dummy_state = copy(point.disch)
            dummy_state.update(p=point.suc.p(), h=dummy_state.h())
            Tend = dummy_state.T()
            Tseal = point.seal_gas_temperature
            Ts1r = (ms1f * Ts1f + mend * Tend + 0.95 * mseal * Tseal) / (
                ms1f + mend + 0.95 * mseal
            )

            suc_rotor = State.define(p=point.suc.p(), T=Ts1r, fluid=point.suc.fluid)
            test_points_rotor.append(
                Point(
                    suc=suc_rotor,
                    disch=point.disch,
                    flow_m=ms1r,
                    speed=point.speed,
                    b=point.b,
                    D=point.D,
                )
            )

        self.points_rotor_t = test_points_rotor
