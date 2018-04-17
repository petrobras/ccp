import pytest
from prf2 import Q_
from prf2.state import State


@pytest.fixture
def suc_1():
    fluid = dict(CarbonDioxide=0.76064, R134a=0.23581,
                 Nitrogen=0.00284, Oxygen=0.00071)
    return State.define(p=Q_(1.839, 'bar'), T=Q_(291.5), fluid=fluid)

