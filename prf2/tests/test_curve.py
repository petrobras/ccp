import pytest
import numpy as np
from numpy.testing import assert_allclose
from prf2 import ureg, Q_
from prf2.state import State
from prf2.point import Point
from prf2.curve import Curve


def test_raise_1_point():
    with pytest.raises(TypeError) as ex:
        Curve([1])
    assert 'At least 2 points' in str(ex)


@pytest.fixture
def curve0():
    suc = State.define(p=Q_(1, 'bar'), T=300, fluid='co2')
    disch = State.define(p=Q_(2, 'bar'), T=310, fluid='co2')
    disch1 = State.define(p=Q_(2.5, 'bar'), T=315, fluid='co2')
    p0 = Point(suc=suc, disch=disch, flow_v=1, speed=1)
    p1 = Point(suc=suc, disch=disch1, flow_v=2, speed=1)
    return Curve([p0, p1])


def test_curve_suc_parameters(curve0):
    assert curve0.suc.p().units == 'pascal'
    assert_allclose(curve0.suc.p(), np.array([100000., 100000.]))
    assert curve0.suc.T().units == 'kelvin'
    assert_allclose(curve0.suc.T(), np.array([300., 300.]))


def test_curve_disch_parameters(curve0):
    assert curve0.disch.p().units == 'pascal'
    assert_allclose(curve0.disch.p(), np.array([200000., 250000.]))
    assert curve0.disch.T().units == 'kelvin'
    assert_allclose(curve0.disch.T(), np.array([310., 315.]))


def test_curve_performance_parameters(curve0):
    assert curve0.head.units == 'joule/kilogram'
    assert curve0.eff.units == ureg.dimensionless
    assert curve0.power.units == 'watts'
