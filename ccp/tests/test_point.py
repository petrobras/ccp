import pytest
from numpy.testing import assert_allclose
from ccp import ureg, Q_
from ccp.state import State
from ccp.point import Point
from pathlib import Path
from tempfile import tempdir

skip = False  # skip slow tests


@pytest.fixture
def suc_0():
    fluid = dict(CarbonDioxide=0.76064, R134a=0.23581, Nitrogen=0.00284, Oxygen=0.00071)
    return State.define(p=Q_(1.839, "bar"), T=291.5, fluid=fluid)


@pytest.fixture
def disch_0():
    fluid = dict(CarbonDioxide=0.76064, R134a=0.23581, Nitrogen=0.00284, Oxygen=0.00071)
    return State.define(p=Q_(5.902, "bar"), T=380.7, fluid=fluid)


@pytest.fixture
def point_0(suc_0, disch_0):
    point_0 = Point(suc=suc_0, disch=disch_0, flow_v=1, speed=1)

    return point_0


def test_point(suc_0, disch_0, point_0):
    assert point_0.suc == suc_0
    assert point_0.disch == disch_0
    assert point_0.suc.rhomass() == suc_0.rhomass()
    assert point_0.disch.rhomass() == disch_0.rhomass()


def test_point_n_exp(point_0):
    assert_allclose(point_0._n_exp(), 1.2910625831119145, rtol=1e-6)


def test_point_head_pol(point_0):
    assert point_0._head_pol().units == "joule/kilogram"
    assert_allclose(point_0._head_pol(), 55280.691617)


def test_point_head_pol_mallen_saville(point_0):
    assert point_0._head_pol_mallen_saville().units == "joule/kilogram"
    assert_allclose(point_0._head_pol_mallen_saville(), 55497.486223)


def test_point_eff_pol(point_0):
    assert_allclose(point_0._eff_pol(), 0.711186, rtol=1e-5)


def test_point_eff_pol_schultz(point_0):
    assert_allclose(point_0._eff_pol_schultz(), 0.71243, rtol=1e-5)


def test_point_head_isen(point_0):
    assert point_0._head_isen().units == "joule/kilogram"
    assert_allclose(point_0._head_isen().magnitude, 53165.986507, rtol=1e-5)


def test_eff_isen(point_0):
    assert_allclose(point_0._eff_isen(), 0.68398, rtol=1e-5)


def test_schultz_f(point_0):
    assert_allclose(point_0._schultz_f(), 1.00175, rtol=1e-5)


def test_head_pol_schultz(point_0):
    assert point_0._head_pol_schultz().units == "joule/kilogram"
    assert_allclose(point_0._head_pol_schultz(), 55377.406664, rtol=1e-6)


def test_volume_ratio(point_0):
    assert point_0._volume_ratio().units == ureg.dimensionless
    assert_allclose(point_0._volume_ratio(), 0.40527649030, rtol=1e-6)


def test_calc_from_eff_suc_volume_ratio(suc_0, point_0):
    flow_v = point_0.flow_v
    eff = point_0.eff
    volume_ratio = point_0.volume_ratio
    point_1 = Point(flow_v=flow_v, suc=suc_0, eff=eff, volume_ratio=volume_ratio)
    assert_allclose(point_1.eff, point_0.eff)
    assert_allclose(point_1.disch.p(), point_0.disch.p())
    assert_allclose(point_1.disch.T(), point_0.disch.T())


@pytest.mark.skipif(skip is True, reason="Slow test")
def test_calc_from_eff_head_suc():
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
    suc = State.define(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    p0 = Point(
        suc=suc, flow_v=Q_(6501.67, "m**3/h"), head=Q_(179.275, "kJ/kg"), eff=0.826357
    )

    assert_allclose(p0.volume_ratio, 0.326647, rtol=1e-4)


def test_calc_from_eff_head_suc_fast():
    fluid = dict(methane=0.8, ethane=0.2)

    suc = State.define(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    p0 = Point(
        suc=suc, flow_v=Q_(6501.67, "m**3/h"), head=Q_(179.275, "kJ/kg"), eff=0.826357
    )

    assert_allclose(p0.volume_ratio, 0.413837, rtol=1e-6)


def test_equality(point_0):
    point_1 = Point(suc=point_0.suc, speed=point_0.speed, flow_v=point_0.flow_v, head=point_0.head, eff=point_0.eff)
    assert point_0 == point_1


def test_save_load(point_0):
    file = Path(tempdir) / "suc_0.toml"
    point_0.save(file)
    point_0_loaded = Point.load(file)
    assert point_0 == point_0_loaded
