import pytest
from ccp.compressor import StraightThrough, Point1Sec
from ccp.point import Point
from ccp.state import State
from ccp import Q_


@pytest.fixture
def straight_through():
    fluid_sp = {
        "methane": 69.945,
        "ethane": 9.729,
        "propane": 5.570,
        "butane": 1.780,
        "isobutane": 1.020,
        "pentane": 0.390,
        "isopentane": 0.360,
        "hexane": 0.180,
        "nitrogen": 1.490,
        "hydrogen sulfide": 0.017,
        "carbon dioxide": 9.259,
        "water": 0.200,
    }
    suc_sp = State.define(p=Q_(16.99, "bar"), T=Q_(38.4, "degC"), fluid=fluid_sp)
    disch_sp = State.define(p=Q_(80.39, "bar"), T=Q_(164.6, "degC"), fluid=fluid_sp)
    guarantee_point = Point(
        suc=suc_sp, disch=disch_sp, flow_v=Q_(8765, "m³/h"), speed=Q_(12361, "RPM")
    )

    test_points = [
        Point1Sec(
            flow_m=Q_(28638, "kg/h"),
            speed=Q_(7993, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.914, "bar"),
                T=Q_(301, "degK"),
                fluid={
                    "carbon dioxide": 0.77634,
                    "R134a": 0.17626,
                    "nitrogen": 0.373,
                    "oxygen": 0.0101,
                },
            ),
            disch=State.define(
                p=Q_(6.06, "bar"),
                T=Q_(396.5, "degK"),
                fluid={
                    "carbon dioxide": 0.77634,
                    "R134a": 0.17626,
                    "nitrogen": 0.373,
                    "oxygen": 0.0101,
                },
            ),
            balance_line_flow=Q_(0.1484, "kg/s"),
            seal_gas_flow=Q_(0.07932, "kg/s"),
            seal_gas_temperature=Q_(308, "degK"),
            oil_flow_journal_bearing_de=Q_(23.945, "l/min"),
            oil_flow_journal_bearing_nde=Q_(36.102, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(27.872, "l/min"),
            oil_inlet_temperature=Q_(45.885, "degC"),
            oil_outlet_temperature_de=Q_(44.244, "degC"),
            oil_outlet_temperature_nde=Q_(50.512, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(22712.4, "kg/h"),
            speed=Q_(8199, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.572, "bar"),
                T=Q_(300.6, "degK"),
                fluid={
                    "carbon dioxide": 0.77634,
                    "R134a": 0.17626,
                    "nitrogen": 0.373,
                    "oxygen": 0.0101,
                },
            ),
            disch=State.define(
                p=Q_(6.212, "bar"),
                T=Q_(404.1, "degK"),
                fluid={
                    "carbon dioxide": 0.77634,
                    "R134a": 0.17626,
                    "nitrogen": 0.373,
                    "oxygen": 0.0101,
                },
            ),
            balance_line_flow=Q_(0.1545, "kg/s"),
            seal_gas_flow=Q_(0.0813, "kg/s"),
            seal_gas_temperature=Q_(309.5, "degK"),
            oil_flow_journal_bearing_de=Q_(23.945, "l/min"),
            oil_flow_journal_bearing_nde=Q_(36.102, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(27.872, "l/min"),
            oil_inlet_temperature=Q_(45.885, "degC"),
            oil_outlet_temperature_de=Q_(44.244, "degC"),
            oil_outlet_temperature_nde=Q_(50.512, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(18532.8, "kg/h"),
            speed=Q_(8182, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.496, "bar"),
                T=Q_(299.7, "degK"),
                fluid={
                    "carbon dioxide": 0.7859,
                    "R134a": 0.1722,
                    "nitrogen": 0.033,
                    "oxygen": 0.0089,
                },
            ),
            disch=State.define(
                p=Q_(7.17, "bar"),
                T=Q_(414.5, "degK"),
                fluid={
                    "carbon dioxide": 0.7859,
                    "R134a": 0.1722,
                    "nitrogen": 0.033,
                    "oxygen": 0.0089,
                },
            ),
            balance_line_flow=Q_(0.1266, "kg/s"),
            seal_gas_flow=Q_(0.03048, "kg/s"),
            seal_gas_temperature=Q_(304.8, "degK"),
            oil_flow_journal_bearing_de=Q_(23.945, "l/min"),
            oil_flow_journal_bearing_nde=Q_(36.102, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(27.872, "l/min"),
            oil_inlet_temperature=Q_(45.885, "degC"),
            oil_outlet_temperature_de=Q_(44.244, "degC"),
            oil_outlet_temperature_nde=Q_(50.512, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(16329.6, "kg/h"),
            speed=Q_(8135, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.432, "bar"),
                T=Q_(299.9, "degK"),
                fluid={
                    "carbon dioxide": 0.7859,
                    "R134a": 0.1722,
                    "nitrogen": 0.033,
                    "oxygen": 0.0089,
                },
            ),
            disch=State.define(
                p=Q_(7.106, "bar"),
                T=Q_(417.5, "degK"),
                fluid={
                    "carbon dioxide": 0.7859,
                    "R134a": 0.1722,
                    "nitrogen": 0.033,
                    "oxygen": 0.0089,
                },
            ),
            balance_line_flow=Q_(0.124, "kg/s"),
            seal_gas_flow=Q_(0.02966, "kg/s"),
            seal_gas_temperature=Q_(304.6, "degK"),
            oil_flow_journal_bearing_de=Q_(23.945, "l/min"),
            oil_flow_journal_bearing_nde=Q_(36.102, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(27.872, "l/min"),
            oil_inlet_temperature=Q_(45.885, "degC"),
            oil_outlet_temperature_de=Q_(44.244, "degC"),
            oil_outlet_temperature_nde=Q_(50.512, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(14018.4, "kg/h"),
            speed=Q_(8178, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.394, "bar"),
                T=Q_(299.1, "degK"),
                fluid={
                    "carbon dioxide": 0.7859,
                    "R134a": 0.1722,
                    "nitrogen": 0.033,
                    "oxygen": 0.0089,
                },
            ),
            disch=State.define(
                p=Q_(7.422, "bar"),
                T=Q_(424.3, "degK"),
                fluid={
                    "carbon dioxide": 0.7859,
                    "R134a": 0.1722,
                    "nitrogen": 0.033,
                    "oxygen": 0.0089,
                },
            ),
            balance_line_flow=Q_(0.1289, "kg/s"),
            seal_gas_flow=Q_(0.03095, "kg/s"),
            seal_gas_temperature=Q_(303.9, "degK"),
            oil_flow_journal_bearing_de=Q_(23.945, "l/min"),
            oil_flow_journal_bearing_nde=Q_(36.102, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(27.872, "l/min"),
            oil_inlet_temperature=Q_(45.885, "degC"),
            oil_outlet_temperature_de=Q_(44.244, "degC"),
            oil_outlet_temperature_nde=Q_(50.512, "degC"),
        ),
    ]
    compressor = StraightThrough(
        guarantee_point=guarantee_point, test_points=test_points
    )

    return compressor
