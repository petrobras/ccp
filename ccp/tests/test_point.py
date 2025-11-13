import pytest
import ccp
from numpy.testing import assert_allclose
from ccp.point import *
from pathlib import Path
from tempfile import tempdir
import pickle

skip = False  # skip slow tests


@pytest.fixture
def suc_0():
    fluid = dict(CarbonDioxide=0.76064, Nitrogen=0.23581, Oxygen=0.00284)
    return State(p=Q_(1.839, "bar"), T=291.5, fluid=fluid)


@pytest.fixture
def disch_0():
    fluid = dict(CarbonDioxide=0.76064, Nitrogen=0.23581, Oxygen=0.00284)
    return State(p=Q_(5.902, "bar"), T=405.7, fluid=fluid)


@pytest.fixture
def point_disch_flow_v_speed_suc(suc_0, disch_0):
    point_disch_suc = Point(suc=suc_0, disch=disch_0, flow_v=1, speed=1, b=1, D=1)
    return point_disch_suc


def test_point_disch_flow_v_speed_suc(suc_0, disch_0, point_disch_flow_v_speed_suc):
    assert point_disch_flow_v_speed_suc.suc == suc_0
    assert point_disch_flow_v_speed_suc.disch == disch_0
    assert_allclose(point_disch_flow_v_speed_suc.flow_v.m, 1.0)
    assert_allclose(point_disch_flow_v_speed_suc.flow_m.m, 3.072307, rtol=1e-4)
    assert_allclose(point_disch_flow_v_speed_suc.speed.m, 1.0)
    assert_allclose(point_disch_flow_v_speed_suc.head.m, 82816.596731, rtol=1e-4)
    assert_allclose(point_disch_flow_v_speed_suc.eff.m, 0.797226, rtol=1e-4)
    assert_allclose(point_disch_flow_v_speed_suc.phi.m, 2.546479)
    assert_allclose(point_disch_flow_v_speed_suc.psi.m, 662532.773850)
    assert_allclose(point_disch_flow_v_speed_suc.volume_ratio.m, 2.304738, rtol=1e-4)
    assert_allclose(point_disch_flow_v_speed_suc.power.m, 319154.332272)


@pytest.fixture
def point_eff_phi_psi_suc_volume_ratio(suc_0):
    point_eff_phi_psi_suc_volume_ratio = Point(
        suc=suc_0,
        eff=0.797811,
        phi=2.546479,
        psi=663018.928304,
        volume_ratio=2.304738,
        b=1,
        D=1,
    )
    return point_eff_phi_psi_suc_volume_ratio


def test_point_eff_suc_volume_ratio(suc_0, disch_0, point_eff_phi_psi_suc_volume_ratio):
    assert point_eff_phi_psi_suc_volume_ratio.suc == suc_0
    assert point_eff_phi_psi_suc_volume_ratio.disch == disch_0
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.flow_v.m, 0.999411, rtol=1e-4)
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.flow_m.m, 3.070496, rtol=1e-4)
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.speed.m, 0.999411, rtol=1e-4)
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.head.m, 82779.695820, rtol=1e-4)
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.eff.m, 0.797811, rtol=1e-4)
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.phi, 2.546479, rtol=1e-4)
    assert_allclose(point_eff_phi_psi_suc_volume_ratio.psi, 663018.928304, rtol=1e-4)
    assert_allclose(
        point_eff_phi_psi_suc_volume_ratio.volume_ratio, 2.304738, rtol=1e-4
    )
    assert_allclose(
        point_eff_phi_psi_suc_volume_ratio.power.m, 318590.196620, rtol=1e-3
    )


@pytest.fixture
def point_eff_flow_v_head_speed_suc(suc_0):
    point_eff_flow_v_head_speed_suc = Point(
        suc=suc_0, head=82876.226229, eff=0.797811, flow_v=1, speed=1, b=1, D=1
    )
    return point_eff_flow_v_head_speed_suc


def test_point_eff_flow_v_head_speed_suc(
    suc_0, disch_0, point_eff_flow_v_head_speed_suc
):
    assert point_eff_flow_v_head_speed_suc.suc == suc_0
    assert point_eff_flow_v_head_speed_suc.disch == disch_0
    assert_allclose(point_eff_flow_v_head_speed_suc.flow_v.m, 1.0, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.flow_m.m, 3.072307, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.speed.m, 1.0, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.head.m, 82876.226229, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.eff.m, 0.797811, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.phi.m, 2.546479, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.psi.m, 663009.809832, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.volume_ratio.m, 2.306675, rtol=1e-4)
    assert_allclose(point_eff_flow_v_head_speed_suc.power.m, 319149.832746, rtol=1e-4)


@pytest.fixture
def point_eff_flow_m_head_speed_suc(suc_0):
    point_eff_flow_v_head_speed_suc = Point(
        suc=suc_0, head=82876.226229, eff=0.797811, flow_m=3.072307, speed=1, b=1, D=1
    )
    return point_eff_flow_v_head_speed_suc


def test_point_eff_flow_m_head_speed_suc(
    suc_0, disch_0, point_eff_flow_m_head_speed_suc
):
    assert point_eff_flow_m_head_speed_suc.suc == suc_0
    assert point_eff_flow_m_head_speed_suc.disch == disch_0
    assert_allclose(point_eff_flow_m_head_speed_suc.flow_v.m, 1.0, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.flow_m.m, 3.072307, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.speed.m, 1.0, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.head.m, 82876.226229, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.eff.m, 0.797811, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.phi.m, 2.546479, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.psi.m, 663009.809832, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.volume_ratio.m, 2.306675, rtol=1e-4)
    assert_allclose(point_eff_flow_m_head_speed_suc.power.m, 319149.786073, rtol=1e-4)


@pytest.fixture
def point_disch_p_eff_flow_m_speed_suc(suc_0):
    point_disch_p_eff_flow_v_speed_suc = Point(
        suc=suc_0,
        disch_p=Q_(5.902, "bar"),
        eff=0.797811,
        flow_m=3.072307,
        speed=1,
        b=1,
        D=1,
    )
    return point_disch_p_eff_flow_v_speed_suc


def test_point_disch_p_eff_flow_m_head_speed_suc(
    suc_0, disch_0, point_disch_p_eff_flow_m_speed_suc
):
    assert point_disch_p_eff_flow_m_speed_suc.suc == suc_0
    assert point_disch_p_eff_flow_m_speed_suc.disch == disch_0
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.flow_v.m, 1.0, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.flow_m.m, 3.072307, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.speed.m, 1.0, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.head.m, 82806.904136, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.eff.m, 0.797811, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.phi.m, 2.546479, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_m_speed_suc.psi.m, 662455.233087, rtol=1e-4)
    assert_allclose(
        point_disch_p_eff_flow_m_speed_suc.volume_ratio.m, 2.305269, rtol=1e-4
    )
    assert_allclose(
        point_disch_p_eff_flow_m_speed_suc.power.m, 318882.832181, rtol=1e-4
    )


@pytest.fixture
def point_disch_p_eff_flow_v_speed_suc(suc_0):
    point_disch_p_eff_flow_v_speed_suc = Point(
        suc=suc_0, disch_p=Q_(5.902, "bar"), eff=0.797811, flow_v=1, speed=1, b=1, D=1
    )
    return point_disch_p_eff_flow_v_speed_suc


def test_point_disch_p_eff_flow_v_head_speed_suc(
    suc_0, disch_0, point_disch_p_eff_flow_v_speed_suc
):
    assert point_disch_p_eff_flow_v_speed_suc.suc == suc_0
    assert point_disch_p_eff_flow_v_speed_suc.disch == disch_0
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.flow_v.m, 1.0, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.flow_m.m, 3.072307, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.speed.m, 1.0, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.head.m, 82806.904136, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.eff.m, 0.797811, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.phi.m, 2.546479, rtol=1e-4)
    assert_allclose(point_disch_p_eff_flow_v_speed_suc.psi.m, 662455.233087, rtol=1e-4)
    assert_allclose(
        point_disch_p_eff_flow_v_speed_suc.volume_ratio.m, 2.305269, rtol=1e-4
    )
    assert_allclose(
        point_disch_p_eff_flow_v_speed_suc.power.m, 318882.878815, rtol=1e-4
    )


@pytest.fixture
def point_disch_T_flow_v_pressure_ratio_speed_suc(suc_0):
    point_disch_T_flow_v_pressure_ratio_speed_suc = Point(
        suc=suc_0,
        pressure_ratio=Q_(3.2093529091897772, "dimensionless"),
        disch_T=Q_(405.7, "degK"),
        flow_v=1,
        speed=1,
        b=1,
        D=1,
    )
    return point_disch_T_flow_v_pressure_ratio_speed_suc


def testpoint_disch_T_flow_v_pressure_ratio_speed_suc(
    suc_0, disch_0, point_disch_T_flow_v_pressure_ratio_speed_suc
):
    assert point_disch_T_flow_v_pressure_ratio_speed_suc.suc == suc_0
    assert point_disch_T_flow_v_pressure_ratio_speed_suc.disch == disch_0
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.flow_v.m, 1.0, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.flow_m.m, 3.072307, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.speed.m, 1.0, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.head.m, 82816.596731, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.eff.m, 0.797226, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.phi.m, 2.546479, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.psi.m, 662532.773850, rtol=1e-4
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.volume_ratio.m,
        2.304738,
        rtol=1e-4,
    )
    assert_allclose(
        point_disch_T_flow_v_pressure_ratio_speed_suc.power.m, 319154.332272, rtol=1e-4
    )


def test_point_n_exp(suc_0, disch_0):
    assert_allclose(n_exp(suc_0, disch_0).m, 1.396545, rtol=1e-6)


def test_f_schultz(suc_0, disch_0):
    assert_allclose(f_schultz(suc_0, disch_0).m, 1.001647, rtol=1e-5)


def test_f_sandberg_colby(suc_0, disch_0):
    assert_allclose(f_sandberg_colby(suc_0, disch_0).m, 1.000912, rtol=1e-5)


def test_point_head_pol(suc_0, disch_0):
    h = head_pol(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82741.114339)


def test_head_pol_schultz(suc_0, disch_0):
    h = head_pol_schultz(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82877.366038, rtol=1e-6)


def test_head_pol_sandberg_colby(suc_0, disch_0):
    h = head_pol_sandberg_colby(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82816.596731, rtol=1e-6)


def test_head_pol_sandberg_colby_f(suc_0, disch_0):
    h = head_pol_sandberg_colby_f(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82816.596731, rtol=1e-6)


def test_point_head_pol_mallen_saville(suc_0, disch_0):
    h = head_pol_mallen_saville(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 83006.348299)


def test_point_head_isen(suc_0, disch_0):
    h = head_isentropic(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.magnitude, 79984.234009, rtol=1e-5)


def test_head_reference(suc_0, disch_0):
    h, eff = head_reference(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82951.386575, rtol=1e-8)


def test_head_reference_2017(suc_0, disch_0):
    h, eff = head_reference_2017(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82951.388465, rtol=1e-8)


def test_head_pol_huntington(suc_0, disch_0):
    h = head_pol_huntington(suc_0, disch_0)
    assert h.units == "joule/kilogram"
    assert_allclose(h.m, 82951.470027, rtol=1e-6)


def test_point_eff_polytropic(suc_0, disch_0):
    assert_allclose(eff_pol(suc_0, disch_0).m, 0.796499, rtol=1e-5)


def test_point_eff_pol_schultz(suc_0, disch_0):
    assert_allclose(eff_pol_schultz(suc_0, disch_0).m, 0.797811, rtol=1e-5)


def test_point_eff_pol_huntington(suc_0, disch_0):
    assert_allclose(eff_pol_huntington(suc_0, disch_0).m, 0.798524, rtol=1e-5)


def test_eff_isentropic(suc_0, disch_0):
    assert_allclose(eff_isentropic(suc_0, disch_0).m, 0.76996, rtol=1e-5)


def test_reynolds(suc_0):
    re = reynolds(suc_0, speed=1, b=1, D=1)
    assert str(re.units) == "dimensionless"
    assert_allclose(re.m, 99944.204545)


def test_equality(point_disch_flow_v_speed_suc):
    point_1 = Point(
        suc=point_disch_flow_v_speed_suc.suc,
        speed=point_disch_flow_v_speed_suc.speed,
        flow_v=point_disch_flow_v_speed_suc.flow_v,
        head=point_disch_flow_v_speed_suc.head,
        eff=point_disch_flow_v_speed_suc.eff,
        b=point_disch_flow_v_speed_suc.b,
        D=point_disch_flow_v_speed_suc.D,
    )
    assert point_disch_flow_v_speed_suc == point_1
    assert hash(point_disch_flow_v_speed_suc) == hash(point_1)


@pytest.fixture
def suc_1():
    fluid = dict(
        methane=0.69945,
        ethane=0.09729,
        propane=0.0557,
        nbutane=0.0178,
        ibutane=0.0102,
        npentane=0.0039,
        ipentane=0.0036,
        nhexane=0.0018,
        n2=0.0149,
        co2=0.09259,
        h2s=0.00017,
        water=0.002,
    )
    suc_1 = State(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    return suc_1


@pytest.fixture
def point_eff_flow_v_head_speed_suc_1(suc_1):
    point_eff_flow_v_head_speed_suc_1 = Point(
        suc=suc_1,
        flow_v=Q_(6501.67, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(179.275, "kJ/kg"),
        eff=0.826357,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )

    return point_eff_flow_v_head_speed_suc_1


def test_converted_from_find_speed(point_eff_flow_v_head_speed_suc_1):
    suc_2 = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    point_converted_from_find_speed = Point.convert_from(
        original_point=point_eff_flow_v_head_speed_suc_1, suc=suc_2, find="speed"
    )

    assert_allclose(
        point_converted_from_find_speed.b.m, point_eff_flow_v_head_speed_suc_1.b.m
    )
    assert_allclose(
        point_converted_from_find_speed.D.m, point_eff_flow_v_head_speed_suc_1.D.m
    )
    assert_allclose(
        point_converted_from_find_speed.eff.m,
        point_eff_flow_v_head_speed_suc_1.eff.m,
        rtol=1e-4,
    )
    assert_allclose(
        point_converted_from_find_speed.phi.m,
        point_eff_flow_v_head_speed_suc_1.phi.m,
        rtol=1e-2,
    )
    assert_allclose(
        point_converted_from_find_speed.psi.m,
        point_eff_flow_v_head_speed_suc_1.psi.m,
        rtol=1e-2,
    )
    assert_allclose(point_converted_from_find_speed.volume_ratio_ratio.m, 1.0)
    assert_allclose(point_converted_from_find_speed.speed.m, 1253.498131, rtol=1e-5)
    assert_allclose(point_converted_from_find_speed.head.m, 206799.617316, rtol=1e-2)
    assert_allclose(point_converted_from_find_speed.power.m, 1084977.717171, rtol=1e-2)


def test_converted_from_find_volume_ratio(point_eff_flow_v_head_speed_suc_1):
    suc_2 = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    point_converted_from_find_volume_ratio = Point.convert_from(
        original_point=point_eff_flow_v_head_speed_suc_1, suc=suc_2, find="volume_ratio"
    )

    assert_allclose(
        point_converted_from_find_volume_ratio.b.m,
        point_eff_flow_v_head_speed_suc_1.b.m,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.D.m,
        point_eff_flow_v_head_speed_suc_1.D.m,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.eff.m,
        point_eff_flow_v_head_speed_suc_1.eff.m,
        rtol=1e-4,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.phi.m,
        point_eff_flow_v_head_speed_suc_1.phi.m,
        rtol=1e-2,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.psi.m,
        point_eff_flow_v_head_speed_suc_1.psi.m,
        rtol=1e-2,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.volume_ratio.m, 2.719926, rtol=1e-4
    )
    assert_allclose(point_converted_from_find_volume_ratio.speed.m, 1167.101671)
    assert_allclose(point_converted_from_find_volume_ratio.head.m, 179275.0, rtol=1e-2)
    assert_allclose(
        point_converted_from_find_volume_ratio.power.m, 875741.275802, rtol=1e-2
    )
    assert_allclose(point_converted_from_find_volume_ratio.phi_ratio.m, 1.0)
    assert_allclose(point_converted_from_find_volume_ratio.psi_ratio.m, 1.0)
    assert_allclose(
        point_converted_from_find_volume_ratio.volume_ratio_ratio.m, 1.125238, rtol=1e-4
    )


def test_converted_from_find_volume_ratio_with_reynolds_correction_1997(
    point_eff_flow_v_head_speed_suc_1,
):
    suc_2 = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    point_converted_from_find_volume_ratio = Point.convert_from(
        original_point=point_eff_flow_v_head_speed_suc_1,
        suc=suc_2,
        find="volume_ratio",
        reynolds_correction="ptc1997",
    )

    assert_allclose(
        point_converted_from_find_volume_ratio.b.m,
        point_eff_flow_v_head_speed_suc_1.b.m,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.D.m,
        point_eff_flow_v_head_speed_suc_1.D.m,
    )
    print(
        point_converted_from_find_volume_ratio.eff,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.eff.m,
        0.819619,
        rtol=1e-4,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.phi.m,
        point_eff_flow_v_head_speed_suc_1.phi.m,
        rtol=1e-2,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.psi.m,
        7.838824,
        rtol=1e-6,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.volume_ratio.m, 2.687329, rtol=1e-4
    )
    assert_allclose(point_converted_from_find_volume_ratio.speed.m, 1167.101671)
    assert_allclose(
        point_converted_from_find_volume_ratio.head.m, 177813.215677, rtol=1e-2
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.power.m, 875741.275802, rtol=1e-2
    )
    assert_allclose(point_converted_from_find_volume_ratio.phi_ratio.m, 1.0)
    assert_allclose(
        point_converted_from_find_volume_ratio.psi_ratio.m, 1.008221, rtol=1e-4
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.volume_ratio_ratio.m, 1.138887, rtol=1e-4
    )


def test_converted_from_find_volume_ratio_with_reynolds_correction_2022(
    point_eff_flow_v_head_speed_suc_1,
):
    suc_2 = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    point_converted_from_find_volume_ratio = Point.convert_from(
        original_point=point_eff_flow_v_head_speed_suc_1,
        suc=suc_2,
        find="volume_ratio",
        reynolds_correction="ptc2022",
    )

    assert_allclose(
        point_converted_from_find_volume_ratio.b.m,
        point_eff_flow_v_head_speed_suc_1.b.m,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.D.m,
        point_eff_flow_v_head_speed_suc_1.D.m,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.eff.m,
        0.811481,
        rtol=1e-4,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.phi.m,
        0.080670,
        rtol=1e-4,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.psi.m,
        7.832131,
        rtol=1e-4,
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.volume_ratio.m, 2.667214, rtol=1e-4
    )
    assert_allclose(point_converted_from_find_volume_ratio.speed.m, 1167.101671)
    assert_allclose(
        point_converted_from_find_volume_ratio.head.m, 177661.399250, rtol=1e-4
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.power.m, 879781.798593, rtol=1e-4
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.phi_ratio.m, 1.004531, rtol=1e-4
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.psi_ratio.m, 1.009082, rtol=1e-4
    )
    assert_allclose(
        point_converted_from_find_volume_ratio.volume_ratio_ratio.m, 1.147477, rtol=1e-4
    )


def test_converted_from_find_volume_ratio_mach_plot(point_eff_flow_v_head_speed_suc_1):
    suc_2 = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    point_converted_from_find_volume_ratio = Point.convert_from(
        original_point=point_eff_flow_v_head_speed_suc_1, suc=suc_2, find="volume_ratio"
    )

    fig = point_converted_from_find_volume_ratio.plot_mach()

    assert_allclose(fig.data[2]["x"], 0.6012691126466259)
    assert_allclose(fig.data[2]["y"], 0.591181, rtol=1e-4)


def test_converted_from_find_volume_ratio_reynolds_plot(
    point_eff_flow_v_head_speed_suc_1,
):
    suc_2 = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    point_converted_from_find_volume_ratio = Point.convert_from(
        original_point=point_eff_flow_v_head_speed_suc_1, suc=suc_2, find="volume_ratio"
    )

    fig = point_converted_from_find_volume_ratio.plot_reynolds()

    assert_allclose(fig.data[2]["x"], 754805.237322)
    assert_allclose(fig.data[2]["y"], 8284271.505995, rtol=1e-4)


def test_save_load(point_disch_flow_v_speed_suc):
    file = Path(tempdir) / "suc_0.toml"
    point_disch_flow_v_speed_suc.save(file)
    point_0_loaded = Point.load(file)
    assert point_disch_flow_v_speed_suc == point_0_loaded


def test_pickle(point_disch_flow_v_speed_suc):
    pickled_point = pickle.loads(pickle.dumps(point_disch_flow_v_speed_suc))
    assert pickled_point == point_disch_flow_v_speed_suc
    assert hasattr(point_disch_flow_v_speed_suc, "head_plot") is True
    assert hasattr(pickled_point, "head_plot") is True


def test_global_polytropic_method(suc_0, disch_0):
    ccp.config.POLYTROPIC_METHOD = "huntington"
    p0 = Point(suc=suc_0, disch=disch_0, flow_v=1, speed=1, b=1, D=1)
    assert p0.head.units == "joule/kilogram"
    assert_allclose(p0.head.m, 82951.470027, rtol=1e-6)
    # go back to schultz for other tests
    ccp.config.POLYTROPIC_METHOD = "schultz"


def test_case_sc_at():
    suc = State(
        p=Q_("5516000 Pa"), T=Q_("311 K"), fluid={"CO2": 0.70000, "METHANE": 0.30000}
    )
    disch = State(
        p=Q_("16547000 Pa"), T=Q_("416 K"), fluid={"CO2": 0.70000, "METHANE": 0.30000}
    )
    assert_allclose(eff_pol_huntington(suc, disch).m, 0.818206, rtol=1e-6)


def test_point_casing_heat_loss():
    """P76 MAIN B - CASE A - point 0"""
    p = Point(
        flow_m=Q_(7.737, "kg/s"),
        speed=Q_(7894, "RPM"),
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
        suc=State(
            p=Q_(1.826, "bar"),
            T=Q_(296.7, "degK"),
            fluid={
                "carbon dioxide": 0.80218,
                "R134a": 0.18842,
                "nitrogen": 0.0091,
                "oxygen": 0.0003,
            },
        ),
        disch=State(
            p=Q_(6.142, "bar"),
            T=Q_(392.1, "degK"),
            fluid={
                "carbon dioxide": 0.80218,
                "R134a": 0.18842,
                "nitrogen": 0.0091,
                "oxygen": 0.0003,
            },
        ),
        casing_area=7.5,
        casing_temperature=Q_(31.309, "degC"),
        ambient_temperature=Q_(0, "degC"),
    )

    assert_allclose(p.eff.m, 0.735723, rtol=1e-6)
    assert_allclose(p.suc.fluid["CO2"], 0.80218)


def test_ptc10_c6_sample_calculation():
    suc_sp = ccp.State(
        p=Q_(200, "psi"),
        T=Q_(115, "degF"),
        fluid={"methane": 20, "ethane": 25, "propane": 50, "n-butane": 5},
    )
    suc_t = ccp.State(
        p=Q_(20, "psi"),
        T=Q_(100, "degF"),
        fluid={"r134a": 1},
    )
    disch_t = ccp.State(
        p=Q_(67.5, "psi"),
        T=Q_(187.4, "degF"),
        fluid={"r134a": 1},
    )
    point_t = ccp.Point(
        suc=suc_t,
        disch=disch_t,
        flow_v=Q_(14137, "ft³/min"),
        speed=Q_(2245, "RPM"),
        b=Q_(0.0635, "m"),
        D=Q_(1.033, "m"),
    )
    point_sp = ccp.Point.convert_from(
        point_t,
        suc=suc_sp,
        reynolds_correction="ptc1997",
        speed=Q_(3600, "rpm"),
        find="volume_ratio",
    )
    assert_allclose(point_sp.eff.m, 0.792242, rtol=1e-6)
    point_sp = ccp.Point.convert_from(
        point_t,
        suc=suc_sp,
        reynolds_correction="ptc2022",
        speed=Q_(3600, "rpm"),
        find="volume_ratio",
    )
    assert_allclose(point_sp.eff.m, 0.797659, rtol=1e-6)
