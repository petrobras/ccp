import pytest
from prf2.config.units import check_units, Q_, units


def test_new_units_loaded():
    speed = Q_(1, 'RPM')
    assert speed.magnitude == 1


@pytest.fixture
def auxiliary_function():
    @check_units
    def func(p=None, T=None, speed=None, flow_v=None):
        return p, T, speed, flow_v
    return func


def test_units(auxiliary_function):
    results = auxiliary_function(p=1, T=1, speed=1, flow_v=1)
    # check if all available units are tested
    assert len(results) == len(units)

    p, T, speed, flow_v = results

    assert p.magnitude == 1
    assert p.units == 'pascal'

    assert T.magnitude == 1
    assert T.units == 'kelvin'

    assert speed.magnitude == 1
    assert speed.units == 'radian/second'

    assert flow_v.magnitude == 1
    assert flow_v.units == 'meter**3/second'



def test_unit_Q_(auxiliary_function):
    results = auxiliary_function(p=Q_(1, 'pascal'), T=Q_(1, 'kelvin'),
                                 speed=Q_(1, 'radian/second'),
                                 flow_v=Q_(1, 'meter**3/second'))
    # check if all available units are tested
    assert len(results) == len(units)

    p, T, speed, flow_v = results

    assert p.magnitude == 1
    assert p.units == 'pascal'

    assert T.magnitude == 1
    assert T.units == 'kelvin'

    assert speed.magnitude == 1
    assert speed.units == 'radian/second'

    assert flow_v.magnitude == 1
    assert flow_v.units == 'meter**3/second'


def test_unit_Q_conversion(auxiliary_function):
    results = auxiliary_function(p=Q_(1, 'bar'), T=Q_(1, 'celsius'),
                                 speed=Q_(1, 'RPM'),
                                 flow_v=Q_(1, 'foot**3/second'))
    # check if all available units are tested
    assert len(results) == len(units)

    p, T, speed, flow_v = results

    assert p.magnitude == 1e5
    assert p.units == 'pascal'

    assert T.magnitude == 274.15
    assert T.units == 'kelvin'

    assert speed.magnitude == 0.10471975511965977
    assert speed.units == 'radian/second'

    assert flow_v.magnitude == 0.028316846591999994
    assert flow_v.units == 'meter**3/second'
