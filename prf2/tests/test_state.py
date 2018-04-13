import pytest
from prf2.state import *
from numpy.testing import assert_allclose


def test_state_coolprop():
    state = State('REFPROP', 'Methane')
    state.set_mole_fractions([1])
    state.update(CP.PT_INPUTS, 100000, 300)

    assert_allclose(state.p(), 100000)
    assert_allclose(state.T(), 300)
    assert_allclose(state.rhomass(), 0.6442542612980722)


def test_state_coolprop_mix():
    state_mix = State('REFPROP', 'Methane&Ethane')
    state_mix.set_mole_fractions([0.5, 0.5])
    state_mix.update(CP.PT_INPUTS, 100000, 300)

    assert_allclose(state_mix.p(), 100000)
    assert_allclose(state_mix.T(), 300)
    assert_allclose(state_mix.rhomass(), 0.9280595769591103)

