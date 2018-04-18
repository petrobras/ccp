import pytest
from numpy.testing import assert_allclose
from prf2 import Q_
from prf2.state import State
from prf2.point import Point


@pytest.fixture
def suc_0():
    fluid = dict(CarbonDioxide=0.76064, R134a=0.23581,
                 Nitrogen=0.00284, Oxygen=0.00071)
    return State.define(p=Q_(1.839, 'bar'), T=291.5, fluid=fluid)


@pytest.fixture
def disch_0():
    fluid = dict(CarbonDioxide=0.76064, R134a=0.23581,
                 Nitrogen=0.00284, Oxygen=0.00071)
    return State.define(p=Q_(5.902, 'bar'), T=380.7, fluid=fluid)


def test_speed_not_given(suc_0, disch_0):
    with pytest.raises(TypeError) as ex:
        Point(suc=suc_0, disch=disch_0, flow_v=0)
    assert "missing 1 required keyword-only argument: 'speed'" \
           in ex.__str__()


def test_flow_not_given(suc_0, disch_0):
    with pytest.raises(TypeError) as ex:
        Point(suc=suc_0, disch=disch_0, speed=0)
    assert "missing 1 required keyword-only argument: 'flow_v' or 'flow_m'." \
           in ex.__str__()


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
    assert_allclose(point_0._n_exp(), 1.2910625831119145)


def test_point_head_pol(point_0):
    assert point_0._head_pol().units == 'joule/kilogram'
    assert_allclose(point_0._head_pol(), 55280.691617)


def test_point_eff_pol(point_0):
    assert_allclose(point_0._eff_pol(), 0.711186, rtol=1e-5)


def test_point_eff_pol_schultz(point_0):
    assert_allclose(point_0._eff_pol_schultz(), 0.71243, rtol=1e-5)


def test_point_head_isen(point_0):
    assert point_0._head_isen().units == 'joule/kilogram'
    assert_allclose(point_0._head_isen().magnitude, 53165.986507, rtol=1e-5)


def test_eff_isen(point_0):
    assert_allclose(point_0._eff_isen(), 0.68398, rtol=1e-5)


def test_schultz_f(point_0):
    assert_allclose(point_0._schultz_f(), 1.00175, rtol=1e-5)


def test_head_pol_schultz(point_0):
    assert point_0._head_pol_schultz().units == 'joule/kilogram'
    assert_allclose(point_0._head_pol_schultz(), 55377.406664)





