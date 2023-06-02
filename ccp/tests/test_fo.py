import pytest
import ccp
from numpy.testing import assert_allclose

Q_ = ccp.Q_

@pytest.fixture
def fo1():
    fluid = {'R134A': 0.018, 'R1234ZE': 31.254, 'N2': 67.588, "o2":1.14}
    D = Q_(250, 'mm')
    d = Q_(170, 'mm')
    p1 = Q_(10, 'bar')
    T1 = Q_(40, 'degC')
    delta_p = Q_(0.1, 'bar')
    state = ccp.State(p=p1, T=T1, fluid=fluid)

    return ccp.FlowOrifice(state, delta_p, D, d)

def test_flow_orifice(fo1):

    assert_allclose(fo1.qm.to('kg/h').m, 36408.6871553386)





