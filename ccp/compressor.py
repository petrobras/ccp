"""Module to define compressors with 1 or 2 sections."""
from ccp.impeller import Impeller
from ccp.point import Point


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
        buffer_gas_flow=None,
        buffer_temperature=None,
        oil_flow_journal_bearing_de=None,
        oil_flow_journal_bearing_nde=None,
        oil_flow_thrust_bearing_nde=None,
        oil_inlet_temperature=None,
        oil_outlet_temperature_de=None,
        oil_outlet_temperature_nde=None,
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
            polytropic_method=polytropic_method,
        )
        self.balance_line_flow = balance_line_flow
        self.buffer_gas_flow = buffer_gas_flow
        self.buffer_temperature = buffer_temperature
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
