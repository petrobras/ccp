import pytest
import pickle
import ccp
from ccp.state import *
from numpy.testing import assert_allclose


def test_state_possible_name():
    with pytest.raises(ValueError) as exc:
        State.define(p=100000, T=300, fluid={"fake_name": 0.5, "fake_name2": 0.5})
    assert "Fluid fake_name not available." in str(exc.value)


def test_state_define():
    with pytest.raises(TypeError) as exc:
        State.define(p=100000, T=300)
    assert "A fluid is required" in str(exc.value)

    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert_allclose(state.rhomass(), 0.6442542612980722, rtol=1e-7)


def test_eos():
    ccp.config.EOS = "REFPROP"
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert_allclose(state.rhomass(), 0.6442542612980722, rtol=1e-7)

    ccp.config.EOS = "PR"
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert_allclose(state.rhomass(), 0.6445687063978816, rtol=1e-7)

    ccp.config.EOS = "SRK"
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert_allclose(state.rhomass(), 0.6442384800595821, rtol=1e-7)

    ccp.config.EOS = "HEOS"
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert_allclose(state.p().magnitude, 100000)
    assert state.T().magnitude == 300
    assert state.rhomass() == 0.6442581578304425
    assert_allclose(state.rhomass(), 0.6442581578304425, rtol=1e-7)

    ccp.config.EOS = "REFPROP"


def test_new_binary_pairs():
    state = State.define(
        p=100000, T=300, fluid={"r134a": 0.6, "co2": 0.2, "n2": 0.1, "o2": 0.1}
    )
    assert_allclose(state.rho(), 3.076654, rtol=1e-6)
    state = State.define(
        p=100000, T=300, fluid={"r1234ze": 0.6, "co2": 0.2, "n2": 0.1, "o2": 0.1}
    )
    assert_allclose(state.rho(), 3.373371, rtol=1e-6)


def test_state_define_units():
    state = State.define(
        p=Q_(1, "bar"),
        T=Q_(300 - 273.15, "celsius"),
        fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15},
    )

    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.rho().units == "kilogram/meter**3"
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert_allclose(state.rhomass(), 0.6442542612980722, rtol=1e-7)


def test_state_define_units_mix():
    state = State.define(
        p=Q_(1, "bar"),
        T=Q_(300 - 273.15, "celsius"),
        fluid={"Methane": 0.5, "Ethane": 0.5},
    )

    assert state.fluid == {"METHANE": 0.5, "ETHANE": 0.5}

    assert state.gas_constant().units == "joule/(kelvin mole)"
    assert state.molar_mass().units == "kilogram/mole"
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.rho().units == "kilogram/meter**3"
    assert state.v().units == "meter**3/kilogram"
    assert state.z().units == ""
    assert state.h().units == "joule/kilogram"
    assert state.s().units == "joule/(kelvin kilogram)"
    assert state.dpdv_s().units == "kilogram*pascal/meter**3"
    assert state.kv().units == ""
    assert state.dTdp_s().units == "kelvin/pascal"
    assert state.kT().units == ""

    assert state.gas_constant().magnitude == 8.314491
    assert state.molar_mass().magnitude == 0.02305592
    assert state.p().magnitude == 100000
    assert state.T().magnitude == 300
    assert_allclose(state.rho().magnitude, 0.9280595769591103)
    assert_allclose(state.v().magnitude, (1 / 0.9280595769591103))
    assert_allclose(state.z().magnitude, 0.99597784424262)
    assert_allclose(state.h().magnitude, 755784.43407392, rtol=1e-5)
    assert_allclose(state.s().magnitude, 4805.332018156618, rtol=1e-5)
    assert_allclose(state.dpdv_s().magnitude, -114182.00416892, rtol=1e-5)
    assert_allclose(state.kv().magnitude, 1.230331, rtol=1e-5)
    assert_allclose(state.dTdp_s().magnitude, 0.5664135e-3, rtol=1e-5)
    assert_allclose(state.kT().magnitude, 1.232748, rtol=1e-5)
    assert (
        state.__repr__()
        == 'State.define(p=Q_("100000 Pa"), T=Q_("300 K"), fluid={"METHANE": 0.50000, "ETHANE": 0.50000})'
    )

    state.update(p=200000, T=310)
    assert state.p().units == "pascal"
    assert state.T().units == "kelvin"
    assert state.rho().units == "kilogram/meter**3"
    assert state.p().magnitude == 200000
    assert state.T().magnitude == 310
    assert_allclose(state.rho().magnitude, 1.8020813868455758)
    assert (
        state.__repr__()
        == 'State.define(p=Q_("200000 Pa"), T=Q_("310 K"), fluid={"METHANE": 0.50000, "ETHANE": 0.50000})'
    )


def test_state_copy():
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    state1 = copy(state)

    assert state == state
    assert state.rho() == state1.rho()


def test_rho_p_inputs():
    state = State.define(
        rho=0.9280595769591103, p=Q_(1, "bar"), fluid={"Methane": 0.5, "Ethane": 0.5}
    )
    assert_allclose(state.T().m, 300)


def test_rho_T_inputs():
    state = State.define(
        rho=0.9280595769591103, T=300, fluid={"Methane": 0.5, "Ethane": 0.5}
    )
    assert_allclose(state.p().m, 100000)


def test_h_s_inputs():
    state = State.define(
        h=755784.43407392, s=4805.332018156618, fluid={"Methane": 0.5, "Ethane": 0.5}
    )
    assert_allclose(state.h().magnitude, 755784.43407392, rtol=1e-5)
    assert_allclose(state.s().magnitude, 4805.332018156618, rtol=1e-5)
    assert_allclose(state.rho().magnitude, 0.9280595769591103, rtol=1e-5)


def test_h_p_inputs():
    state = State.define(
        h=755784.43407392, p=Q_(1, "bar"), fluid={"Methane": 0.5, "Ethane": 0.5}
    )
    assert_allclose(state.h().magnitude, 755784.43407392, rtol=1e-5)
    assert_allclose(state.s().magnitude, 4805.332018156618, rtol=1e-5)
    assert_allclose(state.rho().magnitude, 0.9280595769591103)


def test_T_s_inputs():
    state = State.define(
        T=300, s=4805.332018156618, fluid={"Methane": 0.5, "Ethane": 0.5}
    )
    assert_allclose(state.h().magnitude, 755784.43407392, rtol=1e-5)
    assert_allclose(state.s().magnitude, 4805.332018156618, rtol=1e-5)
    assert_allclose(state.rho().magnitude, 0.9280595769591103, rtol=1e-5)


def test_equality():
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    state1 = State.define(p=state.p(), T=state.T(), fluid=state.fluid)
    state2 = State.define(h=state.h(), s=state.s(), fluid=state.fluid)

    assert state == state1
    assert state == state2
    assert state1 == state2

    state_mix = State.define(p=100000, T=300, fluid={"Methane": 0.5, "Ethane": 0.5})
    state1_mix = State.define(p=state_mix.p(), T=state_mix.T(), fluid=state_mix.fluid)
    state2_mix = State.define(h=state_mix.h(), s=state_mix.s(), fluid=state_mix.fluid)

    assert state_mix == state1_mix
    assert state_mix == state2_mix
    assert state1_mix == state2_mix


def test_mix_composition():
    fluid = {
        "Isobutene": 0.20,
        "HYDROGEN SULFIDE": 2.67,
        "HEXANE": 7.01,
        "propylene": 0.55,
        "ISOBUTANE": 5.43,
        "Methane": 7.04,
        "ethylene": 0.24,
        "hydrogen": 0.75,
        "Nitrogen": 11.39,
        "BUTANE": 26.70,
        "PROPANE": 21.23,
        "ETHANE": 2.88,
        "1Butene": 0.16,
        "C2BUTENE": 0.02,
        "ISOPENTANE": 5.12,
        "PENTANE": 7.11,
        "T2BUTENE": 0.02,
        "CO": 0.03,
        "carbon dioxide": 1.15,
        "N2": 0.30,
    }

    with pytest.raises(ValueError) as exc:
        State.define(p=Q_(0.804, "kgf/cm**2"), T=Q_(37.4, "degC"), fluid=fluid)
    assert "You might have repeated" in str(exc.value)


def test_pickle():
    state = State.define(p=100000, T=300, fluid={"Methane": 1 - 1e-15, "Ethane": 1e-15})
    assert pickle.loads(pickle.dumps(state)) == state


def test_improved_error_message():
    with pytest.raises(ValueError) as exc:
        ccp.State.define(p=100000, T=20, fluid={"methane": 1 - 1e-15, "ethane": 1e-15})

    assert (
        "Could not define state with {'T': <Quantity(20, 'kelvin')>, 'p': <Quantity(100000, 'pascal')>} and {'METHANE': 0.999999999999999, 'ETHANE': 9.992007221626409e-16}"
        in str(exc.value)
    )


def test_normalization():
    suc0 = ccp.State.define(
        p=Q_("5338000 Pa"),
        T=Q_("313.15 K"),
        fluid={
            "METHANE": 0.48732,
            "CO2": 0.40163,
            "ETHANE": 0.05469,
            "PROPANE": 0.03069,
            "BUTANE": 0.00970,
            "PENTANE": 0.00500,
            "ISOBUTAN": 0.00430,
            "NITROGEN": 0.00390,
            "IPENTANE": 0.00190,
            "HEPTANE": 0.00040,
            "HEXANE": 0.00020,
            "NONANE": 0.0,
            "H2S": 0.00017,
            "OCTANE": 0.00010,
            "WATER": 0.00000,
        },
    )
    # same state with different order for fluid names
    suc1 = ccp.State.define(
        p=Q_("5338000 Pa"),
        T=Q_("313.15 K"),
        fluid={
            "BUTANE": 0.0097,
            "CO2": 0.40163,
            "ETHANE": 0.05469,
            "H2S": 0.00017,
            "HEPTANE": 0.0004,
            "HEXANE": 0.0002,
            "IPENTANE": 0.0019,
            "ISOBUTAN": 0.0043,
            "METHANE": 0.48732,
            "NITROGEN": 0.0039,
            "OCTANE": 0.0001,
            "NONANE": 0.0,
            "PENTANE": 0.005,
            "PROPANE": 0.03069,
            "WATER": 0.0,
        },
    )

    assert sum(suc0.fluid.values()) == 1.0
    assert sum(suc1.fluid.values()) == 1.0

    for k in suc0.fluid.keys():
        # values won't be equal, since the float sum:  sum(molar_fractions)
        # is dependent on the list order and will impact in last digits
        assert suc0.fluid[k] == suc1.fluid[k]

        # no negativa values
        assert suc0.fluid[k] >= 0.0
