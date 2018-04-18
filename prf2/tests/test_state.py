import pytest
from copy import copy
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
    assert state.rho().units == 'kilogram/meter**3'
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert state.rho().magnitude == 0.6442542612980722


def test_state_define_units_mix():
    state = State.define(p=Q_(1, 'bar'), T=Q_(300 - 273.15, 'celsius'),
                         fluid={'Methane': 0.5, 'Ethane': 0.5})

    assert state.fluid == {'METHANE': 0.5, 'ETHANE': 0.5}

    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.rho().units == 'kilogram/meter**3'
    assert state.h().units == 'joule/kilogram'
    assert state.s().units == 'joule/(kelvin kilogram)'
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert state.rho().magnitude == 0.9280595769591103
    assert_allclose(state.h().magnitude, 755784.43407392, rtol=1e-5)
    assert_allclose(state.s().magnitude, 4805.332018156618, rtol=1e-5)

    state.update(p=200000, T=310)
    assert state.p().units == 'pascal'
    assert state.T().units == 'kelvin'
    assert state.rho().units == 'kilogram/meter**3'
    assert state.p().magnitude == 200000
    assert state.T().magnitude == 310
    assert state.rho().magnitude == 1.8020813868455758


def test_state_copy():
    state = State.define(p=100000, T=300, fluid='Methane')
    state1 = copy(state)

    assert state == state
    assert state != state1
    assert state.rho() == state1.rho()
