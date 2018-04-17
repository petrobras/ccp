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


def test_state_coolprop_units():
    state = State('REFPROP', 'Methane')
    state.set_mole_fractions([1])
    state.update(CP.PT_INPUTS, 100000, 300)

    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.rhomass() == 0.6442542612980722


def test_state_define():
    state = State.define(p=100000, T=300, fluid='Methane')

    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert state.rhomass() == 0.6442542612980722


def test_state_define_units():
    state = State.define(p=Q_(1, 'bar'), T=Q_(300 - 273.15, 'celsius'),
                         fluid='Methane')

    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert state.rhomass() == 0.6442542612980722


def test_state_define_units_mix():
    state = State.define(p=Q_(1, 'bar'), T=Q_(300 - 273.15, 'celsius'),
                         fluid={'Methane': 0.5, 'Ethane': 0.5})

    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert state.rhomass() == 0.9280595769591103

    state.update(p=200000, T=310)
    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.p().magnitude == 200000
    assert state.T().magnitude == 310
    assert state.rhomass() == 1.8020813868455758


