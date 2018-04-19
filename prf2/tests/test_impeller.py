import pytest
from prf2 import ureg, Q_, State, Point, Curve, Impeller


@pytest.fixture
def points0():
    suc = State.define(p=Q_(1, 'bar'), T=300, fluid='co2')
    disch = State.define(p=Q_(2, 'bar'), T=370, fluid='co2')
    disch1 = State.define(p=Q_(2.5, 'bar'), T=375, fluid='co2')
    p0 = Point(suc=suc, disch=disch, flow_v=1, speed=1)
    p1 = Point(suc=suc, disch=disch1, flow_v=2, speed=1)
    return p0, p1


@pytest.fixture
def points1():
    suc = State.define(p=Q_(1, 'bar'), T=300, fluid='co2')
    disch = State.define(p=Q_(2.1, 'bar'), T=371, fluid='co2')
    disch1 = State.define(p=Q_(2.6, 'bar'), T=376, fluid='co2')
    p2 = Point(suc=suc, disch=disch, flow_v=1, speed=2)
    p3 = Point(suc=suc, disch=disch1, flow_v=2, speed=2)
    return p2, p3


def test_impeller(points0, points1):
    p0, p1 = points0
    p2, p3 = points1
    imp0 = Impeller([p0, p1, p2, p3], b=0.1, D=1)
    assert imp0.suc is None


def test_impeller_tip_speed(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1], b=0.1, D=1)
    assert imp0.tip_speed(point=imp0[0]).units == 'meter * radian/second'
    assert imp0.tip_speed(point=imp0[0]).magnitude == 0.5


def test_impeller_phi(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1], b=0.1, D=1)
    assert imp0.phi(point=imp0[0]).units == ureg.dimensionless
    assert imp0.phi(point=imp0[0]).magnitude == 2.5464790894703255


def test_impeller_psi(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1], b=0.1, D=1)
    assert imp0.psi(point=imp0[0]).units == ureg.dimensionless
    assert imp0.psi(point=imp0[0]).magnitude == 348222.2409628553

