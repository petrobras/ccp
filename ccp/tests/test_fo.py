import pytest
import ccp
from numpy.testing import assert_allclose

Q_ = ccp.Q_


@pytest.fixture
def fo1():
    fluid = {
        "R134A": 0.018,
        "R1234ZE": 31.254,
        "N2": 67.588,
        "o2": 1.14,
    }
    D = Q_(250, "mm")
    d = Q_(170, "mm")
    p1 = Q_(10, "bar")
    T1 = Q_(40, "degC")
    delta_p = Q_(0.1, "bar")
    state = ccp.State(p=p1, T=T1, fluid=fluid)

    return ccp.FlowOrifice(state, delta_p, D, d)


@pytest.fixture
def fo2():
    """fo1 with different units to assure unit conversion works"""
    fluid = {
        "R134A": 0.018,
        "R1234ZE": 31.254,
        "N2": 67.588,
        "o2": 1.14,
    }
    D = Q_(250 / 1000, "m")
    d = Q_(6.692913385826772, "in")
    p1 = Q_(1000, "kPa")
    T1 = Q_(104, "degF")
    delta_p = Q_(10, "kPa")
    state = ccp.State(p=p1, T=T1, fluid=fluid)

    return ccp.FlowOrifice(state, delta_p, D, d)


@pytest.fixture
def fo3():
    """fo1 with no units to assure unit conversion works"""
    fluid = {
        "R134A": 0.018,
        "R1234ZE": 31.254,
        "N2": 67.588,
        "o2": 1.14,
    }
    D = 0.250
    d = 0.170
    p1 = 1000000.0
    T1 = 313.15
    delta_p = 10000.0
    state = ccp.State(p=p1, T=T1, fluid=fluid)

    return ccp.FlowOrifice(state, delta_p, D, d)


@pytest.fixture
def fo4():
    """fo3 with pressure measured downstream of the flow element."""
    fluid = {
        "R134A": 0.018,
        "R1234ZE": 31.254,
        "N2": 67.588,
        "o2": 1.14,
    }
    D = 0.250
    d = 0.170
    p1 = 990000.0
    T1 = 313.15
    delta_p = 10000.0
    state = ccp.State(p=p1, T=T1, fluid=fluid)

    return ccp.FlowOrifice(state, delta_p, D, d, state_upstream=False)


def test_flow_orifice(fo1, fo2, fo3, fo4):
    assert_allclose(fo1.qm.to("kg/h").m, 36408.6871553386)
    assert_allclose(fo2.qm.to("kg/h").m, 36408.6871553386)
    assert_allclose(fo3.qm.to("kg/h").m, 36408.6871553386)
    assert_allclose(fo4.qm.to("kg/h").m, 36408.6871553386)
