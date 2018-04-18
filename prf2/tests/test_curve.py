import pytest
from prf2.state import State
from prf2.point import Point
from prf2.curve import Curve


def test_raise_1_point():
    with pytest.raises(TypeError) as ex:
        Curve([1])
    assert 'At least 2 points' in str(ex)
