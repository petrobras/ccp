import pytest
import numpy as np
from numpy.testing import assert_allclose
from ccp.compressor import StraightThrough, Point1Sec
from ccp.point import Point
from ccp.state import State
from ccp import Q_


def test_point1sec():
    """P76 MAIN B - CASE A - point 0"""
    p = Point1Sec(
        flow_m=Q_(7.737, "kg/s"),
        speed=Q_(7894, "RPM"),
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
        suc=State.define(
            p=Q_(1.826, "bar"),
            T=Q_(296.7, "degK"),
            fluid={
                "carbon dioxide": 0.80218,
                "R134a": 0.18842,
                "nitrogen": 0.0091,
                "oxygen": 0.0003,
            },
        ),
        disch=State.define(
            p=Q_(6.142, "bar"),
            T=Q_(392.1, "degK"),
            fluid={
                "carbon dioxide": 0.80218,
                "R134a": 0.18842,
                "nitrogen": 0.0091,
                "oxygen": 0.0003,
            },
        ),
        balance_line_flow_m=Q_(0.1076, "kg/s"),
        seal_gas_flow_m=Q_(0.04982, "kg/s"),
        seal_gas_temperature=Q_(297.7, "degK"),
        oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
        oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
        oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
        oil_inlet_temperature=Q_(42.184, "degC"),
        oil_outlet_temperature_de=Q_(48.111, "degC"),
        oil_outlet_temperature_nde=Q_(46.879, "degC"),
        casing_area=7.5,
        casing_temperature=Q_(31.309, "degC"),
        ambient_temperature=Q_(0, "degC"),
    )

    assert_allclose(p.eff, 0.735723, rtol=1e-6)
    assert_allclose(p.suc.fluid["CO2"], 0.80218)


@pytest.fixture
def straight_through():
    """P77 main b - spare"""
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
    disch_sp = State.define(p=Q_(80.38, "bar"), T=Q_(164.6, "degC"), fluid=fluid_sp)
    guarantee_point = Point(
        suc=suc_sp,
        disch=disch_sp,
        flow_v=Q_(8765, "m³/h"),
        speed=Q_(12361, "RPM"),
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )

    test_points = [
        Point1Sec(
            flow_m=Q_(7.737, "kg/s"),
            speed=Q_(7894, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.826, "bar"),
                T=Q_(296.7, "degK"),
                fluid={
                    "carbon dioxide": 0.80218,
                    "R134a": 0.18842,
                    "nitrogen": 0.0091,
                    "oxygen": 0.0003,
                },
            ),
            disch=State.define(
                p=Q_(6.142, "bar"),
                T=Q_(392.1, "degK"),
                fluid={
                    "carbon dioxide": 0.80218,
                    "R134a": 0.18842,
                    "nitrogen": 0.0091,
                    "oxygen": 0.0003,
                },
            ),
            balance_line_flow_m=Q_(0.1076, "kg/s"),
            seal_gas_flow_m=Q_(0.04982, "kg/s"),
            seal_gas_temperature=Q_(297.7, "degK"),
            oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
            oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
            oil_inlet_temperature=Q_(42.184, "degC"),
            oil_outlet_temperature_de=Q_(48.111, "degC"),
            oil_outlet_temperature_nde=Q_(46.879, "degC"),
            casing_area=7.5,
            casing_temperature=Q_(31.309, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(5.966, "kg/s"),
            speed=Q_(7981, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.51, "bar"),
                T=Q_(297, "degK"),
                fluid={
                    "carbon dioxide": 0.80218,
                    "R134a": 0.18842,
                    "nitrogen": 0.0091,
                    "oxygen": 0.0003,
                },
            ),
            disch=State.define(
                p=Q_(6.306, "bar"),
                T=Q_(399.9, "degK"),
                fluid={
                    "carbon dioxide": 0.80218,
                    "R134a": 0.18842,
                    "nitrogen": 0.0091,
                    "oxygen": 0.0003,
                },
            ),
            balance_line_flow_m=Q_(0.1119, "kg/s"),
            seal_gas_flow_m=Q_(0.0509, "kg/s"),
            seal_gas_temperature=Q_(297.9, "degK"),
            oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
            oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
            oil_inlet_temperature=Q_(42.184, "degC"),
            oil_outlet_temperature_de=Q_(48.111, "degC"),
            oil_outlet_temperature_nde=Q_(46.879, "degC"),
            casing_area=7.5,
            casing_temperature=Q_(31.309, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(18532.8, "kg/s"),
            speed=Q_(7984, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.553, "bar"),
                T=Q_(296.3, "degK"),
                fluid={
                    "carbon dioxide": 0.80522,
                    "R134a": 0.18636,
                    "nitrogen": 0.00812,
                    "oxygen": 0.0003,
                },
            ),
            disch=State.define(
                p=Q_(7.526, "bar"),
                T=Q_(409.9, "degK"),
                fluid={
                    "carbon dioxide": 0.80522,
                    "R134a": 0.18636,
                    "nitrogen": 0.00812,
                    "oxygen": 0.0003,
                },
            ),
            balance_line_flow_m=Q_(0.1343, "kg/s"),
            seal_gas_flow_m=Q_(0.05994, "kg/s"),
            seal_gas_temperature=Q_(297.2, "degK"),
            oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
            oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
            oil_inlet_temperature=Q_(42.184, "degC"),
            oil_outlet_temperature_de=Q_(48.111, "degC"),
            oil_outlet_temperature_nde=Q_(46.879, "degC"),
            casing_area=7.5,
            casing_temperature=Q_(31.309, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(4.538, "kg/s"),
            speed=Q_(7981, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.432, "bar"),
                T=Q_(296.3, "degK"),
                fluid={
                    "carbon dioxide": 0.80522,
                    "R134a": 0.18636,
                    "nitrogen": 0.00812,
                    "oxygen": 0.0003,
                },
            ),
            disch=State.define(
                p=Q_(7.505, "bar"),
                T=Q_(415.3, "degK"),
                fluid={
                    "carbon dioxide": 0.80522,
                    "R134a": 0.18636,
                    "nitrogen": 0.00812,
                    "oxygen": 0.0003,
                },
            ),
            balance_line_flow_m=Q_(0.1338, "kg/s"),
            seal_gas_flow_m=Q_(0.05935, "kg/s"),
            seal_gas_temperature=Q_(296.9, "degK"),
            oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
            oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
            oil_inlet_temperature=Q_(42.184, "degC"),
            oil_outlet_temperature_de=Q_(48.111, "degC"),
            oil_outlet_temperature_nde=Q_(46.879, "degC"),
            casing_area=7.5,
            casing_temperature=Q_(31.309, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        Point1Sec(
            flow_m=Q_(3.971, "kg/s"),
            speed=Q_(7963, "RPM"),
            b=Q_(28.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(1.375, "bar"),
                T=Q_(296, "degK"),
                fluid={
                    "carbon dioxide": 0.80522,
                    "R134a": 0.18636,
                    "nitrogen": 0.00812,
                    "oxygen": 0.0003,
                },
            ),
            disch=State.define(
                p=Q_(7.473, "bar"),
                T=Q_(419.1, "degK"),
                fluid={
                    "carbon dioxide": 0.80522,
                    "R134a": 0.18636,
                    "nitrogen": 0.00812,
                    "oxygen": 0.0003,
                },
            ),
            balance_line_flow_m=Q_(0.1334, "kg/s"),
            seal_gas_flow_m=Q_(0.05874, "kg/s"),
            seal_gas_temperature=Q_(296.6, "degK"),
            oil_flow_journal_bearing_de=Q_(27.084, "l/min"),
            oil_flow_journal_bearing_nde=Q_(47.984, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(33.52, "l/min"),
            oil_inlet_temperature=Q_(42.184, "degC"),
            oil_outlet_temperature_de=Q_(48.111, "degC"),
            oil_outlet_temperature_nde=Q_(46.879, "degC"),
            casing_area=7.5,
            casing_temperature=Q_(31.309, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
    ]
    compressor = StraightThrough(
        guarantee_point=guarantee_point,
        test_points=test_points,
        speed=Q_(12193.63898, "RPM"),
    )

    return compressor


def test_straight_through(straight_through):

    # flange test
    p0f = straight_through.points_flange_t[0]
    assert_allclose(p0f.suc.fluid["CO2"], 0.80218)
    assert_allclose(p0f.volume_ratio, 2.554283752)
    assert_allclose(p0f.mach, 0.648614697, rtol=1e-6)
    assert_allclose(p0f.reynolds, 1225053.326175, rtol=1e-6)
    assert_allclose(p0f.head, 62207.67737, rtol=1e-6)
    assert_allclose(p0f.casing_heat_loss, 3193.518)
    assert_allclose(p0f.eff, 0.735723, rtol=1e-6)
    assert_allclose(p0f.power, 654187.626)
    k_seal = straight_through.k_seal[0]
    assert_allclose(k_seal, 1.201149e-05)
    assert_allclose(p0f.mend, Q_(302.1678, "kg/h").to("kg/s"))

    # rotor test
    p0r = straight_through.points_rotor_t[0]
    assert_allclose(p0r.flow_m, Q_(28155.3678, "kg/h").to("kg/s"))
    assert_allclose(p0r.suc.T(), 297.696929680625)
    assert_allclose(p0r.suc.p(), 182600)
    assert_allclose(p0r.head, 62311.048952, rtol=1e-6)
    assert_allclose(p0r.casing_heat_loss, 3193.518)
    assert_allclose(p0r.eff, 0.744487, rtol=1e-6)
    assert_allclose(p0r.power, 654586.0882)

    # rotor specified
    p0r_sp = straight_through.points_rotor_sp[0]
    assert_allclose(p0r_sp.flow_m, Q_(171207.7077, "kg/h").to("kg/s"), rtol=1e-3)
    assert_allclose(p0r_sp.suc.T(), 312.646427, rtol=1e-3)
    assert_allclose(p0r_sp.suc.p(), 1699000)
    assert_allclose(p0r_sp.head, 148674.8794, rtol=1e-6)
    assert_allclose(p0r_sp.eff, 0.7444869804, rtol=1e-6)
    assert_allclose(p0r_sp.power, 9501324.55769, rtol=1e-4)

    # flange specified
    p0f_sp = straight_through.points_flange_sp[0]
    assert_allclose(p0f_sp.flow_m, Q_(169296.4746, "kg/h").to("kg/s"), rtol=1e-2)
    assert_allclose(p0f_sp.suc.T(), 311.55, rtol=1e-3)
    assert_allclose(p0f_sp.suc.p(), 1699000)
    assert_allclose(p0f_sp.head, 148399.758541, rtol=1e-6)
    assert_allclose(p0f_sp.eff, 0.7357389512832868, rtol=1e-6)
    assert_allclose(p0f_sp.power, 9501324.55769, rtol=1e-3)

    # imp specified
    assert_allclose(
        straight_through.head,
        np.array(
            [
                [
                    211610.343979,
                    205136.724749,
                    173289.555545,
                    148399.758034,
                    193804.346837,
                ]
            ]
        ),
    )
    point_sp = straight_through.point(
        speed=straight_through.speed, flow_m=Q_(142000, "kg/h")
    )
    assert_allclose(point_sp.eff, 0.820459, rtol=1e-5)