import pytest
import numpy as np
from numpy.testing import assert_allclose
from ccp.compressor import (
    StraightThrough,
    Point1Sec,
    PointFirstSection,
    PointSecondSection,
    BackToBack,
)
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
    k_seal = straight_through.k_end_seal[0]
    assert_allclose(k_seal, 1.201149e-05)

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
        rtol=1e-6,
    )
    point_sp = straight_through.point(
        speed=straight_through.speed, flow_m=Q_(142000, "kg/h")
    )
    assert_allclose(point_sp.eff, 0.820459, rtol=1e-5)


def test_straight_through_calculate_speed(straight_through):
    straight_through.calculate_speed_to_match_discharge_pressure()
    point_sp = straight_through.point(
        speed=straight_through.speed,
        flow_m=straight_through.guarantee_point.flow_m,
    )
    assert_allclose(point_sp.disch.p(), straight_through.guarantee_point.disch.p())


def test_point2sec():
    p = PointFirstSection(
        flow_m=Q_(4.325, "kg/s"),
        speed=Q_(9096, "RPM"),
        b=Q_(10.5, "mm"),
        D=Q_(365, "mm"),
        suc=State.define(
            p=Q_(5.182, "bar"),
            T=Q_(299.5, "degK"),
            fluid={
                "carbon dioxide": 1,
            },
        ),
        disch=State.define(
            p=Q_(14.95, "bar"),
            T=Q_(397.6, "degK"),
            fluid={
                "carbon dioxide": 1,
            },
        ),
        balance_line_flow_m=Q_(0.1625, "kg/s"),
        seal_gas_flow_m=Q_(0.0616, "kg/s"),
        seal_gas_temperature=299.7,
        first_section_discharge_flow_m=4.8059,
        div_wall_flow_m=None,
        end_seal_upstream_temperature=304.3,
        end_seal_upstream_pressure=Q_(14.59, "bar"),
        div_wall_upstream_temperature=362.5,
        div_wall_upstream_pressure=Q_(26.15, "bar"),
        oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
        oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
        oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
        oil_inlet_temperature=Q_(41.544, "degC"),
        oil_outlet_temperature_de=Q_(49.727, "degC"),
        oil_outlet_temperature_nde=Q_(50.621, "degC"),
        casing_area=5.5,
        casing_temperature=Q_(23.895, "degC"),
        ambient_temperature=Q_(0, "degC"),
    )

    assert_allclose(p.eff, 0.793154028573233, rtol=1e-6)
    assert_allclose(p.suc.fluid["CO2"], 1.0)


@pytest.fixture
def back_to_back():
    fluid_sp = {
        "methane": 73.66,
        "ethane": 11.53,
        "propane": 7.38,
        "butane": 1.87,
        "isobutane": 1.1,
        "pentane": 0.33,
        "isopentane": 0.3,
        "hexane": 0.06,
        "nitrogen": 0.76,
        "hydrogen sulfide": 0.02,
        "carbon dioxide": 3,
        "water": 0,
    }

    suc_sp_sec1 = State.define(p=Q_(47.39, "bar"), T=Q_(40, "degC"), fluid=fluid_sp)
    disch_sp_sec1 = State.define(
        p=Q_(136.27, "bar"), T=Q_(123.7, "degC"), fluid=fluid_sp
    )
    guarantee_point_sec1 = Point(
        suc=suc_sp_sec1,
        disch=disch_sp_sec1,
        flow_v=Q_(2283, "m³/h"),
        speed=Q_(12360, "RPM"),
        b=Q_(10.15, "mm"),
        D=Q_(365, "mm"),
    )
    suc_sp_sec2 = State.define(p=Q_(135.38, "bar"), T=Q_(40, "degC"), fluid=fluid_sp)
    disch_sp_sec2 = State.define(
        p=Q_(250.44, "bar"), T=Q_(86.7, "degC"), fluid=fluid_sp
    )
    guarantee_point_sec2 = Point(
        suc=suc_sp_sec2,
        disch=disch_sp_sec2,
        flow_v=Q_(726, "m³/h"),
        speed=Q_(12360, "RPM"),
        b=Q_(6.38, "mm"),
        D=Q_(320, "mm"),
    )

    test_points_sec1 = [
        PointFirstSection(
            flow_m=Q_(8.716, "kg/s"),
            speed=Q_(9024, "RPM"),
            b=Q_(10.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(7.083, "bar"),
                T=Q_(298.9, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(14.16, "bar"),
                T=Q_(377.1, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=None,
            seal_gas_flow_m=0.06504,
            seal_gas_temperature=299.5,
            first_section_discharge_flow_m=None,
            div_wall_flow_m=None,
            end_seal_upstream_temperature=303.5,
            end_seal_upstream_pressure=Q_(13.1, "bar"),
            div_wall_upstream_temperature=361.8,
            div_wall_upstream_pressure=Q_(23.13, "bar"),
            oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
            oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
            oil_inlet_temperature=Q_(41.544, "degC"),
            oil_outlet_temperature_de=Q_(49.727, "degC"),
            oil_outlet_temperature_nde=Q_(50.621, "degC"),
            casing_area=5.5,
            casing_temperature=Q_(23.895, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointFirstSection(
            flow_m=Q_(5.724, "kg/s"),
            speed=Q_(9057, "RPM"),
            b=Q_(10.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(5.592, "bar"),
                T=Q_(298.7, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(14.78, "bar"),
                T=Q_(389.8, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=None,
            seal_gas_flow_m=Q_(0.05942, "kg/s"),
            seal_gas_temperature=299.1,
            first_section_discharge_flow_m=None,
            div_wall_flow_m=None,
            end_seal_upstream_temperature=304.1,
            end_seal_upstream_pressure=Q_(14.27, "bar"),
            div_wall_upstream_temperature=363.7,
            div_wall_upstream_pressure=Q_(25.43, "bar"),
            oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
            oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
            oil_inlet_temperature=Q_(41.544, "degC"),
            oil_outlet_temperature_de=Q_(49.727, "degC"),
            oil_outlet_temperature_nde=Q_(50.621, "degC"),
            casing_area=5.5,
            casing_temperature=Q_(23.895, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointFirstSection(
            flow_m=Q_(4.325, "kg/s"),
            speed=Q_(9096, "RPM"),
            b=Q_(10.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(5.182, "bar"),
                T=Q_(299.5, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(14.95, "bar"),
                T=Q_(397.6, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=Q_(0.1625, "kg/s"),
            seal_gas_flow_m=Q_(0.0616, "kg/s"),
            seal_gas_temperature=299.7,
            first_section_discharge_flow_m=4.8059,
            div_wall_flow_m=None,
            end_seal_upstream_temperature=304.3,
            end_seal_upstream_pressure=Q_(14.59, "bar"),
            div_wall_upstream_temperature=362.5,
            div_wall_upstream_pressure=Q_(26.15, "bar"),
            oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
            oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
            oil_inlet_temperature=Q_(41.544, "degC"),
            oil_outlet_temperature_de=Q_(49.727, "degC"),
            oil_outlet_temperature_nde=Q_(50.621, "degC"),
            casing_area=5.5,
            casing_temperature=Q_(23.895, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointFirstSection(
            flow_m=Q_(3.888, "kg/s"),
            speed=Q_(9071, "RPM"),
            b=Q_(10.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(5.16, "bar"),
                T=Q_(300.4, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(15.07, "bar"),
                T=Q_(400.2, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=None,
            seal_gas_flow_m=Q_(0.06099, "kg/s"),
            seal_gas_temperature=300.6,
            first_section_discharge_flow_m=None,
            div_wall_flow_m=None,
            end_seal_upstream_temperature=304.6,
            end_seal_upstream_pressure=Q_(14.66, "bar"),
            div_wall_upstream_temperature=361.8,
            div_wall_upstream_pressure=Q_(25.99, "bar"),
            oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
            oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
            oil_inlet_temperature=Q_(41.544, "degC"),
            oil_outlet_temperature_de=Q_(49.727, "degC"),
            oil_outlet_temperature_nde=Q_(50.621, "degC"),
            casing_area=5.5,
            casing_temperature=Q_(23.895, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointFirstSection(
            flow_m=Q_(3.277, "kg/s"),
            speed=Q_(9123, "RPM"),
            b=Q_(10.5, "mm"),
            D=Q_(365, "mm"),
            suc=State.define(
                p=Q_(5.038, "bar"),
                T=Q_(300.9, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(15.04, "bar"),
                T=Q_(404.3, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=None,
            seal_gas_flow_m=Q_(0.06143, "kg/s"),
            seal_gas_temperature=301,
            first_section_discharge_flow_m=None,
            div_wall_flow_m=None,
            end_seal_upstream_temperature=304.8,
            end_seal_upstream_pressure=Q_(14.6, "bar"),
            div_wall_upstream_temperature=363.7,
            div_wall_upstream_pressure=Q_(26.27, "bar"),
            oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
            oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
            oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
            oil_inlet_temperature=Q_(41.544, "degC"),
            oil_outlet_temperature_de=Q_(49.727, "degC"),
            oil_outlet_temperature_nde=Q_(50.621, "degC"),
            casing_area=5.5,
            casing_temperature=Q_(23.895, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
    ]

    test_points_sec2 = [
        PointSecondSection(
            flow_m=Q_(4.927, "kg/s"),
            speed=Q_(7739, "RPM"),
            b=Q_(6.38, "mm"),
            D=Q_(320, "mm"),
            suc=State.define(
                p=Q_(13.11, "bar"),
                T=Q_(305.1, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(16.31, "bar"),
                T=Q_(335.1, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=0.1066,
            seal_gas_flow_m=0.06367,
            casing_area=5.5,
            casing_temperature=Q_(17.97, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointSecondSection(
            flow_m=Q_(4.105, "kg/s"),
            speed=Q_(7330, "RPM"),
            b=Q_(6.38, "mm"),
            D=Q_(320, "mm"),
            suc=State.define(
                p=Q_(12.69, "bar"),
                T=Q_(304.5, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(16.78, "bar"),
                T=Q_(333.3, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=0.1079,
            seal_gas_flow_m=0.06692,
            casing_area=5.5,
            casing_temperature=Q_(17.97, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointSecondSection(
            flow_m=Q_(3.36, "kg/s"),
            speed=Q_(7412, "RPM"),
            b=Q_(6.38, "mm"),
            D=Q_(320, "mm"),
            suc=State.define(
                p=Q_(12.62, "bar"),
                T=Q_(304.4, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(18.15, "bar"),
                T=Q_(339.9, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=0.1222,
            seal_gas_flow_m=0.07412,
            casing_area=5.5,
            casing_temperature=Q_(17.97, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointSecondSection(
            flow_m=Q_(2.587, "kg/s"),
            speed=Q_(7449, "RPM"),
            b=Q_(6.38, "mm"),
            D=Q_(320, "mm"),
            suc=State.define(
                p=Q_(12.46, "bar"),
                T=Q_(304.5, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(18.6, "bar"),
                T=Q_(344.1, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=0.1171,
            seal_gas_flow_m=0.05892,
            casing_area=5.5,
            casing_temperature=Q_(17.97, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
        PointSecondSection(
            flow_m=Q_(2.075, "kg/s"),
            speed=Q_(7399, "RPM"),
            b=Q_(6.38, "mm"),
            D=Q_(320, "mm"),
            suc=State.define(
                p=Q_(12.52, "bar"),
                T=Q_(304.5, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            disch=State.define(
                p=Q_(18.88, "bar"),
                T=Q_(346.4, "degK"),
                fluid={
                    "carbon dioxide": 1,
                },
            ),
            balance_line_flow_m=0.1211,
            seal_gas_flow_m=0.06033,
            casing_area=5.5,
            casing_temperature=Q_(17.97, "degC"),
            ambient_temperature=Q_(0, "degC"),
        ),
    ]

    compressor_kwargs = dict(
        guarantee_point_sec1=guarantee_point_sec1,
        guarantee_point_sec2=guarantee_point_sec2,
        test_points_sec1=test_points_sec1,
        test_points_sec2=test_points_sec2,
        speed=Q_(12152.45187, "RPM"),
    )

    return compressor_kwargs


def test_back_to_back(back_to_back):
    back_to_back = BackToBack(**back_to_back)
    # check flows for first point sec1
    p0f = back_to_back.points_flange_t_sec1[0]
    assert_allclose(p0f.end_seal_flow_m, Q_(386.62, "kg/h").to("kg/s"), rtol=1e-5)
    assert_allclose(p0f.end_seal_downstream_state.T(), 297.02, rtol=1e-4)
    assert_allclose(p0f.div_wall_flow_m, Q_(884.50, "kg/h").to("kg/s"), rtol=1e-5)
    assert_allclose(p0f.div_wall_downstream_state.p(), Q_(1.416, "MPa").to("Pa"))
    assert_allclose(p0f.div_wall_downstream_state.T(), 355.64, rtol=1e-4)

    # flange test sec1
    p0f = back_to_back.points_flange_t_sec1[0]
    assert_allclose(p0f.suc.fluid["CO2"], 1)
    assert_allclose(p0f.volume_ratio, 1.57845097)
    assert_allclose(p0f.mach, 0.65270166, rtol=1e-6)
    assert_allclose(p0f.reynolds, 1568657.944014, rtol=1e-6)
    assert_allclose(p0f.flow_m, Q_(31377.6, "kg/h").to("kg/s"))
    assert_allclose(p0f.head, 42576.6847, rtol=1e-6)
    assert_allclose(p0f.casing_heat_loss, 1787.346)
    assert_allclose(p0f.eff, 0.62769838, rtol=1e-6)
    assert_allclose(p0f.power, 591204.944665)
    k_seal = back_to_back.k_end_seal[0]
    assert_allclose(k_seal, 7.829411e-06)

    # rotor test sec1
    p0r = back_to_back.points_rotor_t_sec1[0]
    assert_allclose(p0r.flow_m, Q_(31986.6583, "kg/h").to("kg/s"))
    assert_allclose(p0r.suc.T(), 298.881396)
    assert_allclose(p0r.suc.p(), 708300)
    assert_allclose(p0r.head, 42614.2514, rtol=1e-6)
    assert_allclose(p0r.casing_heat_loss, 1787.346)
    assert_allclose(p0r.eff, 0.62286967, rtol=1e-6)
    assert_allclose(p0r.power, 607888.669)

    # flange test sec2
    p0f = back_to_back.points_flange_t_sec2[0]
    assert_allclose(p0f.suc.fluid["CO2"], 1)
    assert_allclose(p0f.volume_ratio, 1.125059893)
    assert_allclose(p0f.mach, 0.49393364, rtol=1e-6)
    assert_allclose(p0f.reynolds, 1303631.450003, rtol=1e-6)
    assert_allclose(p0f.flow_m, Q_(17737.2, "kg/h").to("kg/s"))
    assert_allclose(p0f.head, 12411.07461, rtol=1e-6)
    assert_allclose(p0f.casing_heat_loss, 1344.156)
    assert_allclose(p0f.eff, 0.474667774, rtol=1e-6)
    assert_allclose(p0f.power, 128825.608)

    # rotor test sec2
    p0r = back_to_back.points_rotor_t_sec2[0]
    assert_allclose(p0r.flow_m, 4.850643)
    assert_allclose(p0r.suc.T(), 305.1)
    assert_allclose(p0r.suc.p(), 1311000)
    assert_allclose(p0r.head, 12411.07461, rtol=1e-6)
    assert_allclose(p0r.casing_heat_loss, 1344.156)
    assert_allclose(p0r.eff, 0.47459, rtol=1e-6)
    assert_allclose(p0r.power, 126849.949491)

    # rotor specified sec2
    p0r = back_to_back.points_rotor_sp_sec2[0]
    assert_allclose(p0r.flow_v.to("m³/h"), 1129.74495)
    assert_allclose(p0r.flow_m, 52.082125, rtol=1e-4)
    assert_allclose(p0r.suc.T(), 313.15)
    assert_allclose(p0r.suc.p(), 13350788.401188, rtol=1e-5)
    assert_allclose(p0r.head, 30603.247711, rtol=1e-6)
    assert_allclose(p0r.eff, 0.47459, rtol=1e-6)
    assert_allclose(p0r.power, 3358441.494485, rtol=1e-4)

    # flange specified sec2
    p0f_sp = back_to_back.points_flange_sp_sec2[0]
    assert_allclose(p0f_sp.flow_m, 53.092244, rtol=1e-4)
    assert_allclose(p0f_sp.suc.T(), 313.15)
    assert_allclose(p0f_sp.suc.p(), 13350788.401188, rtol=1e-5)
    assert_allclose(p0f_sp.head, 30603.247711, rtol=1e-6)
    assert_allclose(p0f_sp.eff, 0.47459, rtol=1e-6)
    assert_allclose(p0f_sp.power, 3423577.541135, 1e-4)

    # rotor specified sec1
    p0r_sp = back_to_back.points_rotor_sp_sec1[0]
    assert_allclose(p0r_sp.flow_m, Q_(156223.564, "kg/h").to("kg/s"), rtol=1e-3)
    assert_allclose(p0r_sp.suc.T(), 312.76555064737, rtol=1e-3)
    assert_allclose(p0r_sp.suc.p(), 4739000)
    assert_allclose(p0r_sp.disch.T(), 380.541484, rtol=1e-5)
    assert_allclose(p0r_sp.head, 77283.0955755209, rtol=1e-6)
    assert_allclose(p0r_sp.eff, 0.622869673032321, rtol=1e-6)
    assert_allclose(p0r_sp.power, 5384326.21375024, rtol=1e-3)

    # flange specified
    p0f_sp = back_to_back.points_flange_sp_sec1[0]
    assert_allclose(p0f_sp.flow_m, Q_(153951.321926329, "kg/h").to("kg/s"), rtol=1e-2)
    assert_allclose(p0f_sp.suc.T(), 313.15, rtol=1e-3)
    assert_allclose(p0f_sp.suc.p(), 4739000)
    assert_allclose(p0f_sp.disch.T(), 378.811147, rtol=1e-5)
    assert_allclose(p0f_sp.head, 77063.137578, rtol=1e-6)
    assert_allclose(p0f_sp.eff, 0.649591, rtol=1e-6)
    assert_allclose(p0f_sp.power, 5077064.78668, rtol=1e-3)

    # imp_sec1 specified
    p0f_sp = back_to_back.point_sec1(
        flow_m=Q_(153951.321926329, "kg/h"),
        speed=back_to_back.speed,
    )
    assert_allclose(p0f_sp.flow_m, Q_(153951.321926329, "kg/h").to("kg/s"), rtol=1e-2)
    assert_allclose(p0f_sp.suc.T(), 313.15, rtol=1e-3)
    assert_allclose(p0f_sp.suc.p(), 4739000)
    assert_allclose(p0f_sp.disch.T(), 378.811147, rtol=1e-2)
    assert_allclose(p0f_sp.head, 77063.137578, rtol=1e-2)
    assert_allclose(p0f_sp.eff, 0.649591, rtol=1e-2)
    # power in this case is the 'real' power consumed by the rotor
    assert_allclose(p0f_sp.power, 5384326.21375024, rtol=1e-3)

    # imp_sec2 specified
    p0f_sp = back_to_back.point_sec2(
        flow_m=Q_(53.092244, "kg/s"),
        speed=back_to_back.speed,
    )
    assert_allclose(p0f_sp.flow_m, 53.092244)
    assert_allclose(p0f_sp.suc.T(), 313.15)
    assert_allclose(p0f_sp.suc.p(), 13350788.401188, rtol=1e-5)
    assert_allclose(p0f_sp.head, 30603.247711, rtol=1e-4)
    assert_allclose(p0f_sp.eff, 0.47459, rtol=1e-4)
    # power in this case is the 'real' power consumed by the rotor
    assert_allclose(p0f_sp.power, 3359509.626922, 1e-4)


def test_back_to_back_with_reynolds_correction(back_to_back):
    back_to_back = BackToBack(**back_to_back, reynolds_correction=True)
    # check flows for first point sec1
    p0f = back_to_back.points_flange_t_sec1[0]
    assert_allclose(p0f.end_seal_flow_m, Q_(386.62, "kg/h").to("kg/s"), rtol=1e-5)
    assert_allclose(p0f.end_seal_downstream_state.T(), 297.02, rtol=1e-4)
    assert_allclose(p0f.div_wall_flow_m, Q_(884.50, "kg/h").to("kg/s"), rtol=1e-5)
    assert_allclose(p0f.div_wall_downstream_state.p(), Q_(1.416, "MPa").to("Pa"))
    assert_allclose(p0f.div_wall_downstream_state.T(), 355.64, rtol=1e-4)

    # flange test sec1
    p0f = back_to_back.points_flange_t_sec1[0]
    assert_allclose(p0f.suc.fluid["CO2"], 1)
    assert_allclose(p0f.volume_ratio, 1.57845097)
    assert_allclose(p0f.mach, 0.65270166, rtol=1e-6)
    assert_allclose(p0f.reynolds, 1568657.944014, rtol=1e-6)
    assert_allclose(p0f.flow_m, Q_(31377.6, "kg/h").to("kg/s"))
    assert_allclose(p0f.head, 42576.6847, rtol=1e-6)
    assert_allclose(p0f.casing_heat_loss, 1787.346)
    assert_allclose(p0f.eff, 0.62769838, rtol=1e-6)
    assert_allclose(p0f.power, 591204.944665)
    k_seal = back_to_back.k_end_seal[0]
    assert_allclose(k_seal, 7.829411e-06)

    # rotor test sec1
    p0r = back_to_back.points_rotor_t_sec1[0]
    assert_allclose(p0r.flow_m, Q_(31986.6583, "kg/h").to("kg/s"))
    assert_allclose(p0r.suc.T(), 298.881396)
    assert_allclose(p0r.suc.p(), 708300)
    assert_allclose(p0r.head, 42614.2514, rtol=1e-6)
    assert_allclose(p0r.casing_heat_loss, 1787.346)
    assert_allclose(p0r.eff, 0.62286967, rtol=1e-6)
    assert_allclose(p0r.power, 607888.669)

    # flange test sec2
    p0f = back_to_back.points_flange_t_sec2[0]
    assert_allclose(p0f.suc.fluid["CO2"], 1)
    assert_allclose(p0f.volume_ratio, 1.125059893)
    assert_allclose(p0f.mach, 0.49393364, rtol=1e-6)
    assert_allclose(p0f.reynolds, 1303631.450003, rtol=1e-6)
    assert_allclose(p0f.flow_m, Q_(17737.2, "kg/h").to("kg/s"))
    assert_allclose(p0f.head, 12411.07461, rtol=1e-6)
    assert_allclose(p0f.casing_heat_loss, 1344.156)
    assert_allclose(p0f.eff, 0.474667774, rtol=1e-6)
    assert_allclose(p0f.power, 128825.608)

    # rotor test sec2
    p0r = back_to_back.points_rotor_t_sec2[0]
    assert_allclose(p0r.flow_m, 4.850643)
    assert_allclose(p0r.suc.T(), 305.1)
    assert_allclose(p0r.suc.p(), 1311000)
    assert_allclose(p0r.head, 12411.07461, rtol=1e-6)
    assert_allclose(p0r.casing_heat_loss, 1344.156)
    assert_allclose(p0r.eff, 0.47459, rtol=1e-6)
    assert_allclose(p0r.power, 126849.949491)

    # rotor specified sec2
    p0r = back_to_back.points_rotor_sp_sec2[0]
    assert_allclose(p0r.flow_v.to("m³/h"), 1129.74495)
    assert_allclose(p0r.flow_m, 52.349973, rtol=1e-4)
    assert_allclose(p0r.suc.T(), 313.15)
    assert_allclose(p0r.suc.p(), 13413110.609268, rtol=1e-5)
    assert_allclose(p0r.head, 30836.456326, rtol=1e-6)
    assert_allclose(p0r.eff, 0.478206, rtol=1e-6)
    assert_allclose(p0r.power, 3375713.294289, rtol=1e-4)

    # flange specified sec2
    p0f_sp = back_to_back.points_flange_sp_sec2[0]
    assert_allclose(p0f_sp.flow_m, 53.360084, rtol=1e-4)
    assert_allclose(p0f_sp.suc.T(), 313.15)
    assert_allclose(p0f_sp.suc.p(), 13413110.609268, rtol=1e-5)
    assert_allclose(p0f_sp.head, 30836.456326, rtol=1e-6)
    assert_allclose(p0f_sp.eff, 0.478206, rtol=1e-6)
    assert_allclose(p0f_sp.power, 3440848.856175, 1e-4)

    # rotor specified sec1
    p0r_sp = back_to_back.points_rotor_sp_sec1[0]
    assert_allclose(p0r_sp.flow_m, Q_(156223.564, "kg/h").to("kg/s"), rtol=1e-3)
    assert_allclose(p0r_sp.suc.T(), 312.76555064737, rtol=1e-3)
    assert_allclose(p0r_sp.suc.p(), 4739000)
    assert_allclose(p0r_sp.disch.T(), 380.655898, rtol=1e-5)
    assert_allclose(p0r_sp.head, 77770.015818, rtol=1e-6)
    assert_allclose(p0r_sp.eff, 0.626794, rtol=1e-6)
    assert_allclose(p0r_sp.power, 5384326.21375024, rtol=1e-3)

    # flange specified
    p0f_sp = back_to_back.points_flange_sp_sec1[0]
    assert_allclose(p0f_sp.flow_m, Q_(153951.321926329, "kg/h").to("kg/s"), rtol=1e-2)
    assert_allclose(p0f_sp.suc.T(), 313.15, rtol=1e-3)
    assert_allclose(p0f_sp.suc.p(), 4739000)
    assert_allclose(p0f_sp.disch.T(), 378.904722, rtol=1e-5)
    assert_allclose(p0f_sp.head, 77545.81942, rtol=1e-6)
    assert_allclose(p0f_sp.eff, 0.654042, rtol=1e-6)
    assert_allclose(p0f_sp.power, 5077064.78668, rtol=1e-3)

    # imp_sec1 specified
    p0f_sp = back_to_back.point_sec1(
        flow_m=Q_(153951.321926329, "kg/h"),
        speed=back_to_back.speed,
    )
    assert_allclose(p0f_sp.flow_m, Q_(153951.321926329, "kg/h").to("kg/s"), rtol=1e-2)
    assert_allclose(p0f_sp.suc.T(), 313.15, rtol=1e-3)
    assert_allclose(p0f_sp.suc.p(), 4739000)
    assert_allclose(p0f_sp.disch.T(), 378.811147, rtol=1e-2)
    assert_allclose(p0f_sp.head, 77063.137578, rtol=1e-2)
    assert_allclose(p0f_sp.eff, 0.649591, rtol=1e-2)
    # power in this case is the 'real' power consumed by the rotor
    assert_allclose(p0r_sp.power, 5384326.21375024, rtol=1e-3)

    # imp_sec2 specified
    p0f_sp = back_to_back.point_sec2(
        flow_m=Q_(53.092244, "kg/s"),
        speed=back_to_back.speed,
    )
    assert_allclose(p0f_sp.flow_m, 53.092244)
    assert_allclose(p0f_sp.suc.T(), 313.15)
    assert_allclose(p0f_sp.suc.p(), 13413110.609268, rtol=1e-5)
    assert_allclose(p0f_sp.head, 31556.381204, rtol=1e-4)
    assert_allclose(p0f_sp.eff, 0.489115, rtol=1e-4)
    # power in this case is the 'real' power consumed by the rotor
    assert_allclose(p0r.power, 3375713.294289, 1e-4)


def test_back_to_back_calculate_speed(back_to_back):
    back_to_back = BackToBack(**back_to_back, reynolds_correction=True)
    back_to_back.calculate_speed_to_match_discharge_pressure()
    point_sp = back_to_back.point_sec2(
        speed=back_to_back.speed,
        flow_m=back_to_back.guarantee_point_sec2.flow_m,
    )
    assert_allclose(point_sp.disch.p(), back_to_back.guarantee_point_sec2.disch.p())
