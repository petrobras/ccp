import pytest
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
def point_0():
    assert 0


