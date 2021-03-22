import pytest
import ccp
from numpy.testing import assert_allclose

Q_ = ccp.Q_


@pytest.fixture
def fo0():
    n2 = ccp.State.define(
        p=Q_(9.85, "bar"), T=Q_(145, "degC"), fluid={"n2": 1 - 1e-15, "o2": 1e-15}
    )
    qm = Q_(71281, "kg/hr")
    delta_p = Q_(9.85 - 4, "bar")
    D = Q_(0.3032, "m")

    return ccp.FlowOrifice(n2, delta_p, qm, D)


def test_flow_orifice(fo0):
    assert_allclose(fo0.d.magnitude, 0.10960820617559523)
    fo0.D = 0.5
    fo0.update()
    assert_allclose(fo0.d.magnitude, 0.11028294814259916)
