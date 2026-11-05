"""Tests of EOS="ideal": closed forms, mixture rules, propagation and failures."""

import inspect
import math
import pickle
import threading
import warnings
from copy import copy, deepcopy

import CoolProp.CoolProp as CP
import numpy as np
import pytest
import toml
from numpy.testing import assert_allclose
from scipy.integrate import quad
from scipy.optimize import brentq

import ccp
from ccp import Q_
from ccp.point import (
    eff_isentropic,
    eff_pol_huntington,
    eff_pol_mallen_saville,
    eff_pol_pvn,
    eff_pol_schultz,
    f_schultz,
    head_isentropic,
    head_isentropic_pvn,
    head_pol_huntington,
    head_pol_mallen_saville,
    head_pol_pvn,
    head_pol_sandberg_colby,
    head_pol_sandberg_colby_f,
    head_pol_sandberg_colby_multistep,
    head_pol_schultz,
    head_reference,
    head_reference_2017,
)
from ccp.state import IdealGasWarning, State, _IdealGasState

pytestmark = pytest.mark.filterwarnings("ignore::ccp.state.IdealGasWarning")

R_MOLAR = Q_(1, "molar_gas_constant").to("J/(mol K)").m
N2 = {"Nitrogen": 1.0}
NG = {"Methane": 0.9, "Ethane": 0.05, "Propane": 0.03, "CO2": 0.01, "Nitrogen": 0.01}
GEOMETRY = dict(flow_v=1.0, speed=Q_(9000, "RPM"), b=0.02, D=0.4)
EXACT_CONSTANT_K = ["schultz", "mallen_saville", "huntington"]
REAL_EOS = "REFPROP" if ccp.REFPROP_AVAILABLE else "HEOS"
needs_refprop = pytest.mark.skipif(not ccp.REFPROP_AVAILABLE, reason="needs REFPROP")


def ideal(fluid=N2, EOS="ideal:k=1.4", **kwargs):
    return ccp.State(fluid=fluid, EOS=EOS, **kwargs)


def gas_constant(state):
    return (state.gas_constant() / state.molar_mass()).to("J/(kg K)").m


def closed_form(state, k, r, eta):
    """Constant-k polytropic discharge: T2, head for pressure ratio r."""
    sigma = (k - 1) / (k * eta)
    T1 = state.T().m
    return T1 * r**sigma, gas_constant(state) * T1 * (r**sigma - 1) / sigma


def reference_cp0(names_fractions, T1, r, eta):
    """Constant-efficiency path for cp0(T), independent of _IdealGasState."""
    sources = [(x, CP.AbstractState("HEOS", name)) for name, x in names_fractions]
    for _, source in sources:
        source.specify_phase(CP.iphase_gas)
    M = sum(x * source.molar_mass() for x, source in sources)

    def cp_molar(T):
        total = 0.0
        for x, source in sources:
            source.update(CP.DmolarT_INPUTS, 40.0, T)
            total += x * source.cp0molar()
        return total

    def residual(T2):
        return eta * quad(lambda T: cp_molar(T) / T, T1, T2, epsabs=0, epsrel=1e-12)[
            0
        ] - R_MOLAR * math.log(r)

    T2 = brentq(residual, T1, 3 * T1, xtol=1e-10, rtol=1e-13)
    dh = quad(cp_molar, T1, T2, epsabs=0, epsrel=1e-12)[0] / M
    return T2, eta * dh


@pytest.mark.parametrize("EOS", ["ideal", "ideal:k=1.3"])
@pytest.mark.parametrize("fluid", [N2, NG], ids=["N2", "NG"])
def test_state_relations(EOS, fluid):
    s = ideal(fluid, EOS, p=Q_(3, "bar"), T=Q_(40, "degC"))
    R = gas_constant(s)
    assert s.gas_constant().m == R_MOLAR
    assert s.z().m == 1.0
    assert_allclose(s.p().m, s.rho().m * R * s.T().m, rtol=1e-14)
    assert_allclose(s.cp().m - s.cv().m, R, rtol=1e-14)
    k = s.cp().m / s.cv().m
    assert_allclose(s.kv().m, k, rtol=1e-14)
    assert_allclose(s.kT().m, k, rtol=1e-14)
    assert_allclose(s.speed_sound().m, math.sqrt(k * R * s.T().m), rtol=1e-14)
    assert s.Q() == -1.0
    assert s.phase_is_stable() is True
    assert isinstance(s, ccp.State)


def test_constant_k_reference_and_values():
    s = ideal(p=Q_(1, "atm"), T=Q_(25, "degC"))
    assert s.h().m == 0.0 and s.s().m == 0.0
    R = gas_constant(s)
    s.update(p=2e5, T=400.0)
    assert_allclose(s.cp().m, 3.5 * R, rtol=1e-14)
    assert_allclose(s.h().m, 3.5 * R * (400 - 298.15), rtol=1e-14)
    assert_allclose(
        s.s().m,
        3.5 * R * math.log(400 / 298.15) - R * math.log(2e5 / 101325),
        rtol=1e-14,
    )


@pytest.mark.parametrize("EOS", ["ideal", "ideal:k=1.4"])
@pytest.mark.parametrize("fluid", [N2, NG], ids=["N2", "NG"])
def test_update_pairs_roundtrip(EOS, fluid):
    ref = ideal(fluid, EOS, p=5e5, T=350.0)
    p, T, rho, h, s = ref.p(), ref.T(), ref.rho(), ref.h(), ref.s()
    pairs = [
        dict(p=p, T=T),
        dict(p=p, rho=rho),
        dict(p=p, h=h),
        dict(p=p, s=s),
        dict(rho=rho, s=s),
        dict(rho=rho, T=T),
        dict(h=h, s=s),
        dict(T=T, s=s),
    ]
    expected = [p.m, T.m, rho.m, h.m, s.m]
    for pair in pairs:
        built = ideal(fluid, EOS, **pair)
        moved = ideal(fluid, EOS, p=1e5, T=900.0)
        moved.update(**pair)
        for state in (built, moved):
            values = [state.p().m, state.T().m, state.rho().m, state.h().m, state.s().m]
            assert_allclose(values, expected, rtol=1e-10, atol=1e-9, err_msg=str(pair))


def test_degenerate_and_unimplemented_pairs():
    s = ideal(p=5e5, T=350.0)
    with pytest.raises(ValueError, match="depends on T only"):
        s.update(T=s.T(), h=s.h())
    with pytest.raises(ValueError, match="depends on T only"):
        ideal(T=350.0, h=1e5)
    for pair in (dict(rho=s.rho(), h=s.h()), dict(p=s.p()), dict(T=s.T()), dict()):
        with pytest.raises(KeyError):
            s.update(**pair)


@pytest.mark.parametrize("EOS", ["ideal", "ideal:k=1.4"])
@pytest.mark.parametrize(
    "bad",
    [
        dict(p=math.nan, T=300.0),
        dict(p=-1.0, T=300.0),
        dict(p=1e5, T=0.0),
        dict(p=1e5, T=math.inf),
        dict(p=1e5, h=math.nan),
        dict(p=1e5, s=math.inf),
        dict(rho=0.0, T=300.0),
        dict(T=300.0, s=-1e9),
        dict(T=300.0, s=1e9),
        dict(p=1e5, h=-1e12),
        dict(rho=1.0, s=1e9),
    ],
    ids=str,
)
def test_invalid_inputs(EOS, bad):
    s = ideal(N2, EOS, p=1e5, T=300.0)
    before = (s.p().m, s.T().m, s.h().m, s.s().m)
    with pytest.raises(ValueError):
        s.update(**bad)
    assert (s.p().m, s.T().m, s.h().m, s.s().m) == before


@pytest.mark.parametrize(
    "EOS",
    [
        "Ideal",
        "idealgas",
        "ideal()",
        "ideal:k=1",
        "ideal:k=0.5",
        "ideal:k=abc",
        "ideal:k=nan",
        "ideal:k=inf",
        "ideal:cp=1000",
    ],
)
def test_invalid_eos(EOS):
    with pytest.raises(ValueError, match="Invalid EOS"):
        ccp.State(p=1e5, T=300.0, fluid=N2, EOS=EOS)


def test_eos_is_canonical():
    assert ideal(EOS="ideal:k=1.40", p=1e5, T=300.0).EOS == "ideal:k=1.4"
    assert ideal(EOS="ideal", p=1e5, T=300.0).EOS == "ideal"


def test_phase():
    for phase in (None, False, "gas"):
        s = ideal(p=1e5, T=300.0, phase=phase)
        assert s.phase == "gas" and s._phase_auto is False
        s.update(p=2e5, T=300.0, phase=phase)
        assert s.phase == "gas"
    for phase in ("liquid", "two_phase", "supercritical", "supercritical_gas", "x"):
        with pytest.raises(ValueError):
            ideal(p=1e5, T=300.0, phase=phase)
        with pytest.raises(ValueError):
            ideal(p=1e5, T=300.0).update(p=1e5, T=300.0, phase=phase)
    s = ideal(p=1e5, T=300.0)
    s.specify_phase(CP.iphase_gas)
    with pytest.raises(ValueError):
        s.specify_phase(CP.iphase_liquid)


def test_default_phase_is_ignored():
    ccp.config.DEFAULT_PHASE = None
    s = ideal(p=1e5, T=300.0)
    assert s.phase == "gas"


def test_condensing_conditions_are_a_gas():
    water = ideal({"Water": 1}, "ideal", p=50e5, T=300.0)
    point = ccp.Point(suc=water, disch_p=100e5, eff=0.8, **GEOMETRY)
    assert point.head.m > 0


def test_every_coolprop_method_is_implemented_or_raises():
    s = ideal(NG, "ideal", p=1e5, T=300.0)
    implemented = {
        "Q",
        "T",
        "gas_constant",
        "molar_mass",
        "p",
        "set_mole_fractions",
        "specify_phase",
        "speed_sound",
        "update",
        "viscosity",
    }
    assert implemented <= set(vars(_IdealGasState))
    for name in dir(CP.AbstractState):
        if name.startswith("__") or name in implemented:
            continue
        assert name in vars(_IdealGasState), name
        with pytest.raises(NotImplementedError):
            getattr(_IdealGasState, name)(s)
    for name in ("get_coolprop_state", "plot_envelope", "_X", "_Y", "conductivity"):
        with pytest.raises(NotImplementedError):
            getattr(s, name)()


def test_state_methods_reading_the_backend_are_not_reachable():
    """A new State method that reads the backend must be overridden on the model."""
    unreachable = {
        "_impose_default_phase",  # the phase is always given to State.__init__
        "_spurious_two_phase",  # only from _impose_default_phase
        "_solve_T_at_p",  # only from State.update
    }
    reads_backend = {
        name
        for name, member in vars(State).items()
        if inspect.isfunction(member)
        and (
            "super()." in inspect.getsource(member)
            or "CP.AbstractState." in inspect.getsource(member)
        )
    }
    assert reads_backend - set(vars(_IdealGasState)) == unreachable


@pytest.mark.parametrize(
    "fluid",
    [N2, NG, {"Hydrogen": 0.7, "Methane": 0.3}, {"CO2": 1.0}],
    ids=["N2", "NG", "H2CH4", "CO2"],
)
@pytest.mark.parametrize(
    "EOS",
    ["HEOS", pytest.param("REFPROP", marks=needs_refprop)],
)
def test_dilute_limit_of_real_gas(fluid, EOS):
    T1, T2, p1, p2 = 320.0, 420.0, 5.0, 20.0
    i1, i2 = ideal(fluid, "ideal", p=p1, T=T1), ideal(fluid, "ideal", p=p2, T=T2)
    r1 = ccp.State(p=p1, T=T1, fluid=fluid, EOS=EOS, phase="gas")
    r2 = ccp.State(p=p2, T=T2, fluid=fluid, EOS=EOS, phase="gas")
    assert_allclose(i1.molar_mass().m, r1.molar_mass().m, rtol=1e-6)
    assert_allclose(i1.cp().m, r1.cp().m, rtol=3e-5)
    assert_allclose(i1.cv().m, r1.cv().m, rtol=3e-5)
    assert_allclose(i1.rho().m, r1.rho().m, rtol=1e-4)
    assert_allclose(i1.speed_sound().m, r1.speed_sound().m, rtol=3e-5)
    assert_allclose(i2.h().m - i1.h().m, r2.h().m - r1.h().m, rtol=1e-4)
    assert_allclose(i2.s().m - i1.s().m, r2.s().m - r1.s().m, rtol=1e-4, atol=0.01)


def test_mixture_rules():
    fluid = {"Methane": 0.75, "Nitrogen": 0.25}
    T, p = 350.0, 2e5
    mix = ideal(fluid, "ideal", p=p, T=T)
    pure = {name: ideal({name: 1}, "ideal", p=p, T=T) for name in fluid}
    x = {name: fraction for name, fraction in fluid.items()}
    M = sum(x[n] * pure[n].molar_mass().m for n in x)
    assert_allclose(mix.molar_mass().m, M, rtol=1e-14)
    assert_allclose(mix.rho().m, p * M / (R_MOLAR * T), rtol=1e-14)
    for prop in ("cp", "h"):
        molar = sum(
            x[n] * getattr(pure[n], prop)().m * pure[n].molar_mass().m for n in x
        )
        assert_allclose(getattr(mix, prop)().m * M, molar, rtol=1e-13)
    s_mix = -R_MOLAR * sum(v * math.log(v) for v in x.values())
    molar = sum(x[n] * pure[n].s().m * pure[n].molar_mass().m for n in x) + s_mix
    assert_allclose(mix.s().m * M, molar, rtol=1e-13)


def test_constant_k_mixture_uses_molar_mass_weighted_R():
    fluid = {"Methane": 0.75, "Nitrogen": 0.25}
    s = ideal(fluid, "ideal:k=1.3", p=1e5, T=300.0)
    M = 0.75 * 0.0160428 + 0.25 * 0.0280134
    assert_allclose(gas_constant(s), R_MOLAR / M, rtol=1e-5)
    assert_allclose(s.kv().m, 1.3, rtol=1e-14)


def test_percentages_and_zero_fraction():
    a = ideal({"Methane": 100.0, "Nitrogen": 0.0}, "ideal", p=1e5, T=300.0)
    b = ideal({"Methane": 1.0}, "ideal", p=1e5, T=300.0)
    assert_allclose(
        [a.rho().m, a.h().m, a.s().m, a.viscosity().m],
        [b.rho().m, b.h().m, b.s().m, b.viscosity().m],
        rtol=1e-14,
    )
    with pytest.raises(ValueError):
        ideal({"Methane": 1.5, "Nitrogen": -0.5}, "ideal", p=1e5, T=300.0)


def test_repeated_component():
    with pytest.raises(ValueError, match="Repeated"):
        ideal({"butane": 0.5, "n-butane": 0.5}, "ideal", p=1e5, T=300.0)


def test_no_binary_pair_needed():
    fluid = {"R134a": 0.25, "CO2": 0.25, "Nitrogen": 0.25, "Oxygen": 0.25}
    with pytest.raises(ValueError):
        ccp.State(p=1e5, T=300.0, fluid=fluid, EOS="HEOS")
    point = ccp.Point(
        suc=ideal(fluid, "ideal", p=1e5, T=300.0), disch_p=4e5, eff=0.8, **GEOMETRY
    )
    assert point.head.m > 0 and point.reynolds.m > 0


def test_monatomic_k():
    for name in ("Argon", "Helium"):
        s = ideal({name: 1}, "ideal", p=1e5, T=300.0)
        assert_allclose(s.kv().m, 5 / 3, rtol=2e-5)
        s.update(p=1e5, T=900.0)
        assert_allclose(s.kv().m, 5 / 3, rtol=2e-5)


@needs_refprop
@pytest.mark.parametrize("name", ["13Butadiene", "1-Pentene"])
def test_refprop_only_fluids(name):
    fluid = {name: 0.1, "Methane": 0.9}
    i1, i2 = (
        ideal(fluid, "ideal", p=5.0, T=320.0),
        ideal(fluid, "ideal", p=5.0, T=420.0),
    )
    r1 = ccp.State(p=5.0, T=320.0, fluid=fluid, EOS="REFPROP", phase="gas")
    r2 = ccp.State(p=5.0, T=420.0, fluid=fluid, EOS="REFPROP", phase="gas")
    assert_allclose(i1.cp().m, r1.cp().m, rtol=3e-5)
    assert_allclose(i2.h().m - i1.h().m, r2.h().m - r1.h().m, rtol=1e-4)
    point = ccp.Point(suc=i1, disch_p=20.0, eff=0.8, **GEOMETRY)
    assert point.head.m > 0


# ---------------------------------------------------------------- constant k
@pytest.mark.parametrize("k", [1.4, 1.2, 5 / 3])
@pytest.mark.parametrize("r", [1.2, 4.0, 10.0])
@pytest.mark.parametrize("eta", [0.6, 0.85])
def test_functions_constant_k(k, r, eta):
    EOS = f"ideal:k={k}"
    suc = ideal(EOS=EOS, p=1e5, T=300.0)
    T2, H = closed_form(suc, k, r, eta)
    disch = ideal(EOS=EOS, p=r * 1e5, T=T2)
    assert_allclose(H, eta * suc.cp().m * (T2 - 300.0), rtol=1e-13)

    for function, tol in [
        (head_pol_pvn, 1e-12),
        (head_pol_schultz, 1e-12),
        (head_pol_mallen_saville, 1e-12),
        (head_pol_huntington, 1e-11),
    ]:
        assert_allclose(function(suc, disch).m, H, rtol=tol, err_msg=function.__name__)
    for function in (
        eff_pol_pvn,
        eff_pol_schultz,
        eff_pol_mallen_saville,
        eff_pol_huntington,
    ):
        assert_allclose(function(suc, disch).m, eta, rtol=1e-11)
    assert_allclose(f_schultz(suc, disch).m, 1.0, rtol=1e-12)
    assert_allclose(head_reference_2017(suc, disch)[0].m, H, rtol=1e-10)
    assert_allclose(head_reference(suc, disch)[0].m, H, rtol=1e-6)
    assert_allclose(head_pol_sandberg_colby_multistep(suc, disch).m, H, rtol=2e-3)

    exponent = (k - 1) / k
    Hs = suc.cp().m * 300.0 * (r**exponent - 1)
    assert_allclose(head_isentropic(suc, disch).m, Hs, rtol=1e-10)
    assert_allclose(head_isentropic_pvn(suc, disch).m, Hs, rtol=1e-10)
    assert_allclose(
        eff_isentropic(suc, disch).m,
        (r**exponent - 1) / ((T2 / 300.0) - 1),
        rtol=1e-10,
    )

    x = math.log(T2 / 300.0)
    predicted = H * (1 - (x / 2 / math.tanh(x / 2) - 1) * (1 - eta) / eta)
    assert_allclose(head_pol_sandberg_colby(suc, disch).m, predicted, rtol=1e-12)
    assert_allclose(head_pol_sandberg_colby_f(suc, disch).m, predicted, rtol=1e-12)


@pytest.mark.parametrize("method", EXACT_CONSTANT_K)
@pytest.mark.parametrize(
    "k,r,eta", [(1.4, 4.0, 0.8), (1.15, 4.0, 0.8), (5 / 3, 10.0, 0.7)]
)
def test_point_closures_constant_k(method, k, r, eta):
    EOS = f"ideal:k={k}"
    p1, T1 = 2e5, 300.0
    suc = ideal(EOS=EOS, p=p1, T=T1)
    T2, H = closed_form(suc, k, r, eta)
    p2 = p1 * r
    volume_ratio = r * T1 / T2
    common = dict(polytropic_method=method, **GEOMETRY)
    points = [
        ccp.Point(suc=suc, disch=ideal(EOS=EOS, p=p2, T=T2), **common),
        ccp.Point(suc=suc, disch_p=Q_(p2, "Pa"), eff=eta, **common),
        ccp.Point(suc=suc, pressure_ratio=r, eff=eta, **common),
        ccp.Point(suc=suc, head=Q_(H, "J/kg"), eff=eta, **common),
        ccp.Point(suc=suc, disch_T=Q_(T2, "K"), head=Q_(H, "J/kg"), **common),
        ccp.Point(suc=suc, disch_T=Q_(T2, "K"), disch_p=Q_(p2, "Pa"), **common),
        ccp.Point(suc=suc, eff=eta, volume_ratio=volume_ratio, **common),
    ]
    for point in points:
        assert point.disch.EOS == EOS
        assert_allclose(point.disch.T().m, T2, rtol=1e-9)
        assert_allclose(point.disch.p().m, p2, rtol=1e-9)
        assert_allclose(point.head.m, H, rtol=1e-9)
        assert_allclose(point.eff.m, eta, rtol=1e-9)
        assert_allclose(
            Q_(point.volume_ratio, "dimensionless").m, volume_ratio, rtol=1e-9
        )
        assert_allclose(point.power.m, point.flow_m.m * H / eta, rtol=1e-9)
        assert_allclose(
            point.disch.h().m - suc.h().m, suc.cp().m * (T2 - T1), rtol=1e-9
        )
        k_R = suc.cp().m / suc.cv().m
        assert_allclose(
            point.disch.s().m - suc.s().m,
            suc.cp().m * math.log(T2 / T1) - gas_constant(suc) * math.log(r),
            rtol=1e-8,
        )
        assert_allclose(k_R, k, rtol=1e-13)


@pytest.mark.parametrize("method", ["sandberg_colby", "sandberg_colby_f"])
def test_default_method_is_not_the_closed_form(method):
    """Documented deviation: the path temperature is the arithmetic mean."""
    k, p1, T1, r, T2 = 1.4, 2e5, 300.0, 4.0, 300.0 * 4.0 ** (0.4 / 1.4 / 0.8)
    suc = ideal(p=p1, T=T1)
    eta = (k - 1) / k * math.log(r) / math.log(T2 / T1)
    H = closed_form(suc, k, r, eta)[1]
    point = ccp.Point(
        suc=suc, disch=ideal(p=p1 * r, T=T2), polytropic_method=method, **GEOMETRY
    )
    x = math.log(T2 / T1)
    deviation = -(x / 2 / math.tanh(x / 2) - 1) * (1 - eta) / eta
    assert_allclose(deviation, -5.09e-3, rtol=2e-3)
    assert_allclose(point.head.m / H - 1, deviation, rtol=1e-6)


def test_multistep_constant_k():
    k, p1, T1, r, eta = 1.4, 2e5, 300.0, 4.0, 0.8
    suc = ideal(p=p1, T=T1)
    T2, H = closed_form(suc, k, r, eta)
    common = dict(polytropic_method="sandberg_colby_multistep", **GEOMETRY)
    for point in (
        ccp.Point(suc=suc, disch_p=p1 * r, eff=eta, **common),
        ccp.Point(suc=suc, head=Q_(H, "J/kg"), eff=eta, **common),
        ccp.Point(suc=suc, disch=ideal(p=p1 * r, T=T2), **common),
    ):
        assert_allclose(point.head.m, H, rtol=1e-4)
        assert_allclose(point.disch.T().m, T2, rtol=1e-4)
        assert_allclose(point.disch.p().m, p1 * r, rtol=1e-4)


# ---------------------------------------------------------------- cp0(T)
CP0_CASES = [
    ({"METHANE": 1.0}, 4.0, 0.8),
    ({"CO2": 1.0}, 4.0, 0.75),
    ({"METHANE": 0.85, "ETHANE": 0.10, "CO2": 0.05}, 8.0, 0.8),
]


@pytest.mark.parametrize("fluid,r,eta", CP0_CASES, ids=["CH4", "CO2", "mix"])
def test_huntington_is_exact_for_cp0(fluid, r, eta):
    p1, T1 = 2e5, 300.0
    T2, H = reference_cp0(list(fluid.items()), T1, r, eta)
    suc = ideal(fluid, "ideal", p=p1, T=T1)
    common = dict(polytropic_method="huntington", **GEOMETRY)
    points = [
        ccp.Point(suc=suc, disch_p=p1 * r, eff=eta, **common),
        ccp.Point(suc=suc, disch=ideal(fluid, "ideal", p=p1 * r, T=T2), **common),
        ccp.Point(suc=suc, head=Q_(H, "J/kg"), eff=eta, **common),
    ]
    for point in points:
        assert_allclose(point.disch.T().m, T2, rtol=1e-9)
        assert_allclose(point.disch.p().m, p1 * r, rtol=1e-9)
        assert_allclose(point.head.m, H, rtol=1e-9)
        assert_allclose(point.eff.m, eta, rtol=1e-9)


@pytest.mark.parametrize("fluid,r,eta", CP0_CASES, ids=["CH4", "CO2", "mix"])
@pytest.mark.parametrize(
    "method,lower,upper",
    [
        ("sandberg_colby_multistep", 0.0, 5e-5),
        ("sandberg_colby", 1e-5, 1.5e-2),
        ("sandberg_colby_f", 1e-5, 1.5e-2),
        ("schultz", 1e-5, 1.5e-2),
        ("mallen_saville", 1e-5, 1.5e-2),
    ],
)
def test_other_methods_with_cp0_are_approximate(fluid, r, eta, method, lower, upper):
    p1, T1 = 2e5, 300.0
    T2, H = reference_cp0(list(fluid.items()), T1, r, eta)
    suc = ideal(fluid, "ideal", p=p1, T=T1)
    point = ccp.Point(
        suc=suc, disch_p=p1 * r, eff=eta, polytropic_method=method, **GEOMETRY
    )
    assert lower <= abs(point.head.m / H - 1) < upper
    assert abs(point.disch.T().m / T2 - 1) < upper


@pytest.mark.parametrize(
    "method,deviation,tol",
    [
        ("schultz", -2.406e-3, 0.02),
        ("mallen_saville", 1.642e-3, 0.02),
        ("sandberg_colby", -1.760e-3, 0.02),
        ("sandberg_colby_multistep", -7.6e-6, 0.2),
    ],
)
def test_documented_cp0_deviations(method, deviation, tol):
    fluid, r, eta = CP0_CASES[0]
    p1, T1 = 2e5, 300.0
    _, H = reference_cp0(list(fluid.items()), T1, r, eta)
    point = ccp.Point(
        suc=ideal(fluid, "ideal", p=p1, T=T1),
        disch_p=p1 * r,
        eff=eta,
        polytropic_method=method,
        **GEOMETRY,
    )
    assert_allclose(point.head.m / H - 1, deviation, rtol=tol)


def test_documented_constant_k_deviation():
    k, r, eta = 1.4, 4.0, 0.8
    suc = ideal(EOS="ideal:k=1.4", p=2e5, T=300.0)
    point = ccp.Point(suc=suc, disch_p=2e5 * r, eff=eta, **GEOMETRY)
    sigma = (k - 1) / (k * eta)
    H = gas_constant(suc) * 300.0 * (r**sigma - 1) / sigma
    assert_allclose(point.head.m / H - 1, -6.221e-3, rtol=0.02)


def test_absolute_h_and_s_use_the_source_reference():
    source = CP.AbstractState("HEOS", "Nitrogen")
    source.specify_phase(CP.iphase_gas)
    p, T = Q_(1, "atm").to("Pa").m, 300.0
    source.update(CP.DmolarT_INPUTS, p / (R_MOLAR * T), T)
    s = ideal({"Nitrogen": 1}, "ideal", p=p, T=T)
    M = s.molar_mass().m
    assert_allclose(s.h().m, source.hmolar_idealgas() / M, rtol=1e-12)
    assert_allclose(s.s().m, source.smolar_idealgas() / M, rtol=1e-12)


def test_diverging_polytropic_path_is_not_cut_at_the_solver_bracket():
    # the exact discharge (8048 K) lies above the search interval of the solver,
    # which used to return its upper end with a head 21% low
    suc = ideal(p=1e5, T=300.0)
    with pytest.raises(ValueError):
        ccp.Point(
            suc=suc, disch_p=1e6, eff=0.2, polytropic_method="huntington", **GEOMETRY
        )


@pytest.mark.parametrize("fluid,r,eta", CP0_CASES[:2], ids=["CH4", "CO2"])
def test_reference_functions_with_cp0(fluid, r, eta):
    p1, T1 = 2e5, 300.0
    T2, H = reference_cp0(list(fluid.items()), T1, r, eta)
    suc = ideal(fluid, "ideal", p=p1, T=T1)
    disch = ideal(fluid, "ideal", p=p1 * r, T=T2)
    assert_allclose(head_reference(suc, disch)[0].m, H, rtol=1e-5)
    assert_allclose(head_reference_2017(suc, disch)[0].m, H, rtol=1e-5)
    assert_allclose(eff_pol_huntington(suc, disch).m, eta, rtol=1e-9)


# ---------------------------------------------------------------- conversion
K = 1.35
CONVERSION_RTOL = 1e-6
EOS_K = f"ideal:k={K}"


def _map(suc, method):
    points = []
    for speed in (8000, 9000, 10000):
        scale = speed / 9000
        for flow, head, eff in [
            (1.0, 80.0, 0.78),
            (1.4, 72.0, 0.80),
            (1.8, 60.0, 0.79),
            (2.2, 40.0, 0.70),
        ]:
            points.append(
                ccp.Point(
                    suc=suc,
                    speed=Q_(speed, "RPM"),
                    flow_v=Q_(flow * scale, "m**3/s"),
                    head=Q_(head * scale**2, "kJ/kg"),
                    eff=eff,
                    b=Q_(20, "mm"),
                    D=Q_(400, "mm"),
                    polytropic_method=method,
                )
            )
    return ccp.Impeller(points)


def _assert_closed_form(point, k, tol):
    suc = point.suc
    sigma = (k - 1) / (k * point.eff.m)
    r = (1 + point.head.m * sigma / (gas_constant(suc) * suc.T().m)) ** (1 / sigma)
    assert_allclose(point.disch.p().m / suc.p().m, r, rtol=tol)
    assert_allclose(point.disch.T().m / suc.T().m, r**sigma, rtol=tol)
    assert point.suc.EOS == point.disch.EOS


@pytest.mark.parametrize("method", EXACT_CONSTANT_K)
def test_point_convert_from_constant_k(method):
    suc1 = ideal(EOS=EOS_K, p=2e6, T=300.0)
    suc2 = ideal({"Methane": 1}, EOS_K, p=5e6, T=350.0)
    original = ccp.Point(
        suc=suc1, disch_p=6e6, eff=0.8, polytropic_method=method, **GEOMETRY
    )
    ratio = gas_constant(suc2) * 350.0 / (gas_constant(suc1) * 300.0)

    converted = ccp.Point.convert_from(
        original, suc=suc2, find="speed", polytropic_method=method
    )
    assert_allclose(converted.head.m, original.head.m * ratio, rtol=1e-10)
    assert_allclose(converted.speed.m, original.speed.m * math.sqrt(ratio), rtol=1e-10)
    assert_allclose(converted.eff.m, original.eff.m, rtol=1e-10)
    assert_allclose(converted.disch.p().m / 5e6, 3.0, rtol=1e-10)
    assert_allclose(converted.volume_ratio.m, original.volume_ratio.m, rtol=1e-10)
    assert_allclose(converted.phi.m, original.phi.m, rtol=1e-10)
    assert_allclose(converted.psi.m, original.psi.m, rtol=1e-10)
    _assert_closed_form(converted, K, 1e-10)

    converted = ccp.Point.convert_from(
        original, suc=suc2, find="volume_ratio", polytropic_method=method
    )
    assert_allclose(converted.head.m, original.head.m, rtol=1e-10)
    assert_allclose(converted.eff.m, original.eff.m, rtol=1e-10)
    _assert_closed_form(converted, K, 1e-10)


@pytest.mark.parametrize("method", EXACT_CONSTANT_K)
def test_impeller_and_curve_constant_k(method):
    ccp.config.PARALLEL = False
    ccp.config.POLYTROPIC_METHOD = method
    suc1 = ideal(EOS=EOS_K, p=2e6, T=300.0)
    suc2 = ideal({"Methane": 1}, EOS_K, p=5e6, T=350.0)
    imp = _map(suc1, method)
    for point in imp.points:
        _assert_closed_form(point, K, 1e-9)

    interpolated = imp.point(flow_v=Q_(1.5, "m**3/s"), speed=Q_(9000, "RPM"))
    assert interpolated.suc.EOS == EOS_K
    _assert_closed_form(interpolated, K, 1e-9)
    curve = imp.curve(speed=Q_(8500, "RPM"))
    for point in curve.points:
        _assert_closed_form(point, K, 1e-9)

    for kwargs in (dict(speed="same"), dict(speed=Q_(9500, "RPM"))):
        converted = ccp.Impeller.convert_from(imp, suc=suc2, **kwargs)
        assert len(converted.points) == len(imp.points)
        for point in converted.points:
            assert point.suc.EOS == EOS_K and point.disch.EOS == EOS_K
            _assert_closed_form(point, K, 1e-9)
    # the closed form above also holds for a wrong head: pin the converted map
    # to each point converted on its own and brought to the same speed
    converted = ccp.Impeller.convert_from(imp, suc=suc2, speed="same")
    for new, old in zip(converted.points, imp.points):
        assert new.speed == old.speed
        reference = ccp.Point.convert_from(
            old, suc=suc2, find="volume_ratio", speed=new.speed
        )
        assert_allclose(new.head.m, reference.head.m, rtol=CONVERSION_RTOL)
        assert_allclose(new.eff.m, reference.eff.m, rtol=CONVERSION_RTOL)
        assert_allclose(new.flow_v.m, reference.flow_v.m, rtol=CONVERSION_RTOL)

    converted = ccp.Impeller.convert_from(imp, suc=suc2, speed=Q_(9500, "RPM"))
    assert_allclose([p.speed.to("RPM").m for p in converted.points], 9500.0)

    # default speed: each curve runs at the mean of its similar speeds
    converted = ccp.Impeller.convert_from(imp, suc=suc2)
    for curve, new_curve in zip(imp.curves, converted.curves):
        similar = [ccp.Point.convert_from(p, suc=suc2, find="speed") for p in curve]
        speed_mean = np.mean([p.speed.m for p in similar])
        assert_allclose(new_curve.speed.m, speed_mean, rtol=CONVERSION_RTOL)


def test_impeller_with_cp0_huntington_is_exact():
    ccp.config.PARALLEL = False
    ccp.config.POLYTROPIC_METHOD = "huntington"
    fluid = {"METHANE": 0.85, "ETHANE": 0.10, "CO2": 0.05}
    suc = ideal(fluid, "ideal", p=2e6, T=300.0)
    imp = _map(suc, "huntington")
    for point in imp.points:
        r = point.disch.p().m / point.suc.p().m
        T2, H = reference_cp0(list(fluid.items()), 300.0, r, point.eff.m)
        assert_allclose(point.disch.T().m, T2, rtol=1e-8)
        assert_allclose(point.head.m, H, rtol=1e-8)
    new_suc = ideal({"METHANE": 0.7, "ETHANE": 0.3}, "ideal", p=3e6, T=320.0)
    converted = ccp.Impeller.convert_from(imp, suc=new_suc, speed="same")
    assert {p.suc.EOS for p in converted.points} == {"ideal"}
    assert {p.disch.EOS for p in converted.points} == {"ideal"}


def test_real_map_converted_to_ideal_suction_and_back():
    ccp.config.PARALLEL = False
    real_suc = ccp.State(p=2e6, T=300.0, fluid=N2)
    real_imp = _map(real_suc, "sandberg_colby")
    ideal_suc = ideal(N2, EOS_K, p=2e6, T=320.0)
    converted = ccp.Impeller.convert_from(real_imp, suc=ideal_suc, speed="same")
    assert {p.suc.EOS for p in converted.points} == {EOS_K}
    assert {p.disch.EOS for p in converted.points} == {EOS_K}
    back = ccp.Impeller.convert_from(converted, suc=real_suc, speed="same")
    assert {p.suc.EOS for p in back.points} == {real_suc.EOS}
    assert {p.disch.EOS for p in back.points} == {real_suc.EOS}


# ---------------------------------------------------------------- propagation
def _models(point):
    return {point.suc.EOS, point.disch.EOS, point._dummy_state.EOS}


@pytest.mark.parametrize("EOS", ["ideal", "ideal:k=1.4"])
def test_copy_pickle_and_dict(EOS):
    suc = ideal(NG, EOS, p=2e5, T=300.0)
    point = ccp.Point(suc=suc, disch_p=4e5, eff=0.8, **GEOMETRY)
    assert _models(point) == {EOS}
    for other in (copy(suc), deepcopy(suc), pickle.loads(pickle.dumps(suc))):
        assert type(other) is _IdealGasState
        assert other.EOS == EOS and other == suc
        assert other.h().m == suc.h().m and other.phase == "gas"
    assert b"_IdealGasState" not in pickle.dumps(suc)
    assert _models(pickle.loads(pickle.dumps(point))) == {EOS}

    data = point.to_dict()
    assert data["EOS"] == EOS and data["phase"] == "gas"
    reloaded = ccp.Point.from_dict(toml.loads(toml.dumps(data)))
    assert _models(reloaded) == {EOS}
    assert_allclose(reloaded.head.m, point.head.m, rtol=1e-10)
    assert_allclose(reloaded.disch.T().m, point.disch.T().m, rtol=1e-10)

    measured = ccp.Point(suc=suc, disch=point.disch, **GEOMETRY)
    reloaded = ccp.Point.from_dict(measured.to_dict())
    assert _models(reloaded) == {EOS}
    assert_allclose(reloaded.head.m, measured.head.m, rtol=1e-12)


def test_impeller_and_curve_files(tmp_path):
    ccp.config.PARALLEL = False
    imp = _map(ideal(EOS=EOS_K, p=2e6, T=300.0), "sandberg_colby")
    path = tmp_path / "imp.toml"
    imp.save(path)
    loaded = ccp.Impeller.load(path)
    assert {p.suc.EOS for p in loaded.points} == {EOS_K}
    assert {p.disch.EOS for p in loaded.points} == {EOS_K}
    assert_allclose(
        [p.head.m for p in loaded.points], [p.head.m for p in imp.points], rtol=1e-10
    )
    curve = imp.curves[0]
    reloaded = ccp.Curve.from_dict(curve.to_dict())
    assert {p.suc.EOS for p in reloaded.points} == {EOS_K}


def test_real_files_have_no_eos_key_and_stay_real():
    real = ccp.Point(
        suc=ccp.State(p=1e5, T=300.0, fluid=N2), disch_p=4e5, eff=0.8, **GEOMETRY
    )
    data = real.to_dict()
    assert "EOS" not in data
    ccp.config.EOS = "ideal"
    reloaded = ccp.Point.from_dict(data)
    assert type(reloaded.suc) is ccp.State and type(reloaded.disch) is ccp.State
    assert reloaded.suc.EOS == REAL_EOS


def test_config_selects_the_model_for_new_states_only():
    real = ccp.State(p=1e5, T=300.0, fluid=N2)
    assert real.EOS == REAL_EOS
    ccp.config.EOS = "ideal:k=1.4"
    new = ccp.State(p=1e5, T=300.0, fluid=N2)
    assert type(new) is _IdealGasState and new.EOS == "ideal:k=1.4"
    assert type(copy(real)) is ccp.State and copy(real).EOS == REAL_EOS
    point = ccp.Point(suc=real, disch_p=4e5, eff=0.8, **GEOMETRY)
    assert _models(point) == {REAL_EOS} and type(point.disch) is ccp.State
    point = ccp.Point(suc=new, disch_p=4e5, eff=0.8, **GEOMETRY)
    assert _models(point) == {"ideal:k=1.4"}


def test_rebuild_of_saved_states():
    kwargs = dict(p=Q_(1e5, "Pa"), T=Q_(300, "K"), fluid=N2, phase=False)
    ccp.config.EOS = "ideal"
    legacy = State._rebuild(State, {**kwargs, "EOS": None})
    assert type(legacy) is State and legacy.EOS == REAL_EOS


def test_rebuild_without_refprop(monkeypatch):
    monkeypatch.setattr(ccp, "REFPROP_AVAILABLE", False)
    ccp.config.EOS = "HEOS"
    kwargs = dict(p=Q_(1e5, "Pa"), T=Q_(300, "K"), fluid=N2, phase=False)
    state = State._rebuild(State, {**kwargs, "EOS": "REFPROP"})
    assert state.EOS == "HEOS"


def test_equality():
    a = ideal(p=1e5, T=300.0)
    assert a == ideal(p=1e5, T=300.0) and hash(a) == hash(ideal(p=1e5, T=300.0))
    real = ccp.State(p=1e5, T=300.0, fluid=N2)
    assert a != real and real != a
    assert len({a, real}) == 2
    assert a != ideal(EOS="ideal:k=1.3", p=1e5, T=300.0)
    assert a != ideal(EOS="ideal", p=1e5, T=300.0)


def test_mixed_models_are_refused():
    suc = ideal(p=1e5, T=300.0)
    real_disch = ccp.State(p=4e5, T=500.0, fluid=N2)
    other_k = ideal(EOS="ideal:k=1.3", p=4e5, T=500.0)
    with pytest.raises(ValueError, match="different gas models"):
        ccp.Point(suc=suc, disch=real_disch, **GEOMETRY)
    with pytest.raises(ValueError, match="different gas models"):
        ccp.Point(suc=real_disch, disch=suc, **GEOMETRY)
    with pytest.raises(ValueError, match="different gas models"):
        ccp.Point(suc=suc, disch=other_k, **GEOMETRY)
    ccp.Point(
        suc=ccp.State(p=1e5, T=300.0, fluid=N2, EOS="HEOS"),
        disch=ccp.State(p=4e5, T=500.0, fluid=N2, EOS=REAL_EOS),
        **GEOMETRY,
    )


# ---------------------------------------------------------------- transport
def test_viscosity_is_a_dilute_gas_value():
    s = ideal(NG, "ideal", p=2e6, T=300.0)
    mu = s.viscosity().m
    assert 5e-6 < mu < 3e-5
    s.update(p=2e4, T=300.0)
    assert s.viscosity().m == mu
    assert_allclose(s.kinematic_viscosity().m, mu / s.rho().m, rtol=1e-14)
    assert s.viscosity("uPa*s").units == Q_(1, "uPa*s").units


@needs_refprop
@pytest.mark.parametrize(
    "fluid,tol",
    [
        ({"Nitrogen": 0.79, "Oxygen": 0.21}, 0.01),
        ({"Methane": 0.85, "Ethane": 0.1, "CO2": 0.05}, 0.03),
    ],
    ids=["air", "NG"],
)
def test_viscosity_against_refprop_mixture(fluid, tol):
    real = ccp.State(rho=1e-5, T=350.0, fluid=fluid, EOS="REFPROP", phase="gas")
    assert_allclose(
        ideal(fluid, "ideal", p=1e5, T=350.0).viscosity().m,
        real.viscosity().m,
        rtol=tol,
    )


def test_viscosity_mixing_rule_and_temperature():
    from ccp.state import _dilute_viscosity

    x = {"HYDROGEN": 0.7, "METHANE": 0.3}
    for T in (320.0, 500.0):
        s = ideal(x, "ideal", p=1e5, T=T)
        pure = {}
        for name in x:
            source = CP.AbstractState("HEOS", name)
            source.specify_phase(CP.iphase_gas)
            source.update(CP.DmolarT_INPUTS, 1.0 / (R_MOLAR * T), T)
            pure[name] = (source.viscosity(), source.molar_mass())
            assert_allclose(_dilute_viscosity(name, T), pure[name][0], rtol=1e-12)
        weights = {name: x[name] * math.sqrt(pure[name][1]) for name in x}
        expected = sum(weights[n] * pure[n][0] for n in x) / sum(weights.values())
        assert_allclose(s.viscosity().m, expected, rtol=1e-12)


def test_water_mixture_has_a_viscosity():
    s = ideal({"Methane": 0.97, "Water": 0.03}, "ideal", p=2e6, T=320.0)
    assert 5e-6 < s.viscosity().m < 3e-5


def test_missing_viscosity_model(monkeypatch):
    monkeypatch.setattr("ccp.state._dilute_viscosity", lambda name, T: math.nan)
    suc = ideal(p=1e5, T=300.0)
    with pytest.warns(IdealGasWarning, match="No viscosity model"):
        assert math.isnan(suc.viscosity().m)
    with pytest.warns(IdealGasWarning, match="No viscosity model"):
        point = ccp.Point(suc=suc, disch_p=4e5, eff=0.8, **GEOMETRY)
    assert math.isnan(point.reynolds.m) and point.head.m > 0


def test_flow_orifice():
    s = ideal(EOS="ideal", p=1e6, T=300.0)
    orifice = ccp.FlowOrifice(s, Q_(0.1, "bar"), D=0.3, d=0.15)
    assert orifice.qm.m > 0


# ---------------------------------------------------------------- independence
def test_refprop_only_fluid_without_refprop(monkeypatch):
    from ccp import state as state_module

    state_module._ideal_part_backend.cache_clear()
    monkeypatch.setattr(ccp, "REFPROP_AVAILABLE", False)
    with pytest.raises(ValueError, match="needs REFPROP"):
        ideal({"13Butadiene": 1}, "ideal", p=1e5, T=300.0)
    state_module._ideal_part_backend.cache_clear()


def test_results_ignore_refprop_availability(monkeypatch):
    from ccp import state as state_module

    fluid = {"Methane": 0.85, "Ethane": 0.10, "CO2": 0.05}
    state_module._ideal_part_backend.cache_clear()
    expected = ideal(fluid, "ideal", p=2e6, T=300.0)
    values = [expected.h().m, expected.s().m, expected.cp().m, expected.viscosity().m]
    state_module._ideal_part_backend.cache_clear()
    monkeypatch.setattr(ccp, "REFPROP_AVAILABLE", False)
    other = ideal(fluid, "ideal", p=2e6, T=300.0)
    state_module._ideal_part_backend.cache_clear()
    assert [other.h().m, other.s().m, other.cp().m, other.viscosity().m] == values


def test_threads_do_not_share_backends():
    errors = []

    def worker(T):
        try:
            s = ideal(NG, "ideal", p=1e5, T=T)
            expected = s.h().m
            for _ in range(500):
                s.update(p=1e5, T=T)
                if s.h().m != expected:
                    errors.append(T)
        except Exception as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=(300.0 + 50 * i,)) for i in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors


# ---------------------------------------------------------------- warning
@pytest.mark.filterwarnings("default::ccp.state.IdealGasWarning")
def test_warning():
    with pytest.warns(IdealGasWarning, match="only exists to replicate"):
        ideal(p=1e5, T=300.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warnings.filterwarnings("ignore", category=IdealGasWarning)
        ideal(p=1e5, T=300.0)
        ccp.State(p=1e5, T=300.0, fluid=N2)


# ---------------------------------------------------------------- workers
def _pool_conversion(suc1, suc2):
    imp = _map(suc1, "sandberg_colby")
    ccp.config.PARALLEL = True
    pool = ccp.Impeller.convert_from(imp, suc=suc2, speed="same")
    ccp.config.PARALLEL = False
    serial = ccp.Impeller.convert_from(imp, suc=suc2, speed="same")
    return pool, serial


@pytest.mark.slow
@pytest.mark.parametrize("via_config", [False, True])
def test_pool_matches_serial(via_config):
    if via_config:
        ccp.config.EOS = EOS_K
        suc1 = ccp.State(p=2e6, T=300.0, fluid=N2)
        suc2 = ccp.State(p=5e6, T=350.0, fluid={"Methane": 1})
    else:
        suc1 = ideal(EOS=EOS_K, p=2e6, T=300.0)
        suc2 = ideal({"Methane": 1}, EOS_K, p=5e6, T=350.0)
    pool, serial = _pool_conversion(suc1, suc2)
    for a, b in zip(pool.points, serial.points):
        assert a.suc.EOS == EOS_K and a.disch.EOS == EOS_K
        assert_allclose(a.head.m, b.head.m, rtol=1e-10)
        assert_allclose(a.disch.T().m, b.disch.T().m, rtol=1e-10)


# ---------------------------------------------------------------- collections
def test_collections_refuse_mixed_gas_models():
    fluid = {"Methane": 0.9, "CO2": 0.1}
    points = []
    for EOS, flow_v in ((REAL_EOS, 1.0), ("ideal:k=1.3", 1.2), (REAL_EOS, 1.4)):
        suc = ccp.State(p=2e6, T=310.0, fluid=fluid, EOS=EOS)
        kwargs = {**GEOMETRY, "flow_v": flow_v}
        points.append(ccp.Point(suc=suc, disch_p=4e6, eff=0.8, **kwargs))
    with pytest.raises(ValueError, match="different gas models"):
        ccp.Curve(points)
    with pytest.raises(ValueError, match="different gas models"):
        ccp.Impeller(points)
    ccp.Curve([points[0], points[2]])


def test_rebuild_of_refprop_state_without_refprop_prefers_heos(monkeypatch):
    monkeypatch.setattr(ccp, "REFPROP_AVAILABLE", False)
    ccp.config.EOS = "PR"
    kwargs = dict(p=1e5, T=300.0, fluid={"Methane": 1.0}, EOS="REFPROP", phase=False)
    assert State._rebuild(State, kwargs).EOS == "HEOS"
