import pytest
from prf2.config.units import check_units, Q_, units


def test_new_units_loaded():
    speed = Q_(1, 'RPM')
    assert speed.magnitude == 1


@pytest.fixture
def auxiliary_function():
    @check_units
    def func(p=None, T=None):
        return p, T
    return func


def test_units(auxiliary_function):
    results = auxiliary_function(p=1, T=1)
    # check if all available units are tested
    assert len(results) == len(units)

    p, T = results

    assert p.magnitude == 1
    assert p.units == 'pascal'

    assert T.magnitude == 1
    assert T.units == 'kelvin'


# def test_unit_Q_(auxiliary_function):
#     results = auxiliary_function(p=Q_(1, 'pascal'), T=(1, 'degK'))
#     # check if all available units are tested
#     assert len(results) == len(units)
#
#     p, T = results
#
#     assert p.magnitude == 1
#     assert p.units == 'pascal'
#
#     assert T.magnitude == 1
#     assert T.units == 'kelvin'
#
#

