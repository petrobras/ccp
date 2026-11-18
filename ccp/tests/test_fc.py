import warnings

import CoolProp.CoolProp as CP
import numpy as np
import pytest
from numpy.testing import assert_allclose

import ccp
from ccp.fc import FlowMeterWarning

Q_ = ccp.Q_

fluid = {"R134A": 0.018, "R1234ZE": 31.254, "N2": 67.588, "o2": 1.14}


@pytest.fixture
def state():
    return ccp.State(p=Q_(10, "bar"), T=Q_(40, "degC"), fluid=fluid)


@pytest.fixture
def no_meter_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error", FlowMeterWarning)
        yield


def cone(state, **kwargs):
    """Cone meter of the ccp.FlowCone docstring example."""
    args = dict(delta_p=Q_(0.1, "bar"), D=Q_(250, "mm"), dc=Q_(180, "mm"))
    args.update(kwargs)
    return ccp.FlowCone(state, **args)


def test_flow_cone_hand_calculation(no_meter_warnings):
    """ISO 5167-5 flow evaluated with CoolProp properties, outside ccp."""
    p1, T1, dp, D, dc = 10e5, 300.0, 0.25e5, 0.30, 0.21
    rho, mu, c = (
        CP.PropsSI(k, "P", p1, "T", T1, "HEOS::Methane") for k in ("D", "V", "A")
    )
    kappa = rho * c**2 / p1  # isentropic exponent, -(v/p)(dp/dv)_s
    beta = np.sqrt(1 - (dc / D) ** 2)
    epsilon = 1 - (0.649 + 0.696 * beta**4) * dp / (kappa * p1)
    qm = (
        0.82
        / np.sqrt(1 - beta**4)
        * epsilon
        * np.pi
        / 4
        * (D * beta) ** 2
        * np.sqrt(2 * dp * rho)
    )

    state = ccp.State(p=p1, T=T1, fluid={"methane": 1}, EOS="HEOS")
    fc = ccp.FlowCone(state, dp, D, dc=dc)

    assert_allclose(fc.beta.m, beta)
    assert_allclose(fc.epsilon.m, epsilon)
    assert_allclose(fc.C.m, 0.82)
    assert not fc.calibrated
    assert_allclose(fc.flow_m.to("kg/s").m, qm, rtol=1e-9)
    assert_allclose(fc.reynolds.m, 4 * qm / (np.pi * mu * D), rtol=1e-9)
    assert_allclose(fc.flow_v.to("m³/s").m, qm / rho, rtol=1e-9)
    assert fc.outside_limits == {}


def test_flow_cone(state, no_meter_warnings):
    fc = cone(state)
    assert_allclose(fc.flow_m.to("kg/h").m, 52066.669044036775)
    assert_allclose(fc.beta.m, np.sqrt(1 - 0.72**2))
    assert_allclose(fc.d.to("mm").m, 250 * np.sqrt(1 - 0.72**2))
    assert_allclose(fc.dc.to("mm").m, 180)


def test_flow_cone_units(state, no_meter_warnings):
    expected = cone(state).flow_m.m
    state_us = ccp.State(p=Q_(145.0377, "psi"), T=Q_(104, "degF"), fluid=fluid)
    in_us_units = ccp.FlowCone(
        state_us,
        Q_(1.450377, "psi"),
        Q_(250 / 25.4, "in"),
        dc=Q_(180 / 25.4, "in"),
    )
    assert_allclose(in_us_units.flow_m.m, expected, rtol=1e-5)
    # floats are taken as SI
    assert_allclose(ccp.FlowCone(state, 1e4, 0.25, dc=0.18).flow_m.m, expected)


def test_flow_cone_d_or_dc(state, no_meter_warnings):
    """The equivalent diameter d = beta * D and the cone diameter agree."""
    fc = cone(state)
    by_d = cone(state, dc=None, d=fc.d)
    assert_allclose(by_d.flow_m.m, fc.flow_m.m)
    assert_allclose(by_d.dc.m, fc.dc.m)
    # positional d, as in FlowOrifice
    by_d = ccp.FlowCone(state, Q_(0.1, "bar"), Q_(250, "mm"), fc.d)
    assert_allclose(by_d.flow_m.m, fc.flow_m.m)


def test_flow_cone_state_downstream(state, no_meter_warnings):
    downstream = ccp.State(p=Q_(9.9, "bar"), T=Q_(40, "degC"), fluid=fluid)
    fc = cone(downstream, state_upstream=False)
    assert_allclose(fc.flow_m.m, cone(state).flow_m.m)
    assert_allclose(fc.state.p().to("bar").m, 10)
    # the state passed in is left unchanged
    assert_allclose(downstream.p().to("bar").m, 9.9)


def test_flow_cone_calibrated_constant(state, no_meter_warnings):
    fc = cone(state, C=0.8)
    assert fc.calibrated
    assert_allclose(fc.C.m, 0.8)
    assert_allclose(fc.flow_m.m, cone(state).flow_m.m * 0.8 / 0.82)
    # the limits of the uncalibrated C do not apply to a calibrated meter
    assert cone(state, C=0.8, D=Q_(600, "mm"), dc=Q_(500, "mm")).outside_limits == {}


def test_flow_cone_C_function(state, no_meter_warnings):
    def C(Re):
        return 0.80 + 0.01 * np.log10(Re / 1e6)

    fc = cone(state, C=C)
    assert_allclose(fc.C.m, C(fc.reynolds.m), rtol=1e-12)
    # the flow is proportional to C
    assert_allclose(fc.flow_m.m / fc.C.m, cone(state).flow_m.m / 0.82)
    # the Reynolds number is that of the flow
    mu = state.viscosity().to("Pa*s").m
    assert_allclose(fc.reynolds.m, 4 * fc.flow_m.m / (np.pi * mu * 0.25))


def test_flow_cone_C_table(state, no_meter_warnings):
    reynolds, C = [1e7, 1e5, 1e6], [0.83, 0.80, 0.81]  # unsorted on purpose
    fc = cone(state, C=(reynolds, C))
    assert 1e6 < fc.reynolds.m < 1e7
    expected = np.interp(np.log10(fc.reynolds.m), [5, 6, 7], [0.80, 0.81, 0.83])
    assert_allclose(fc.C.m, expected, rtol=1e-12)


def test_flow_cone_C_table_outside_calibrated_range(state):
    with pytest.warns(FlowMeterWarning, match="outside the calibrated range"):
        fc = cone(state, C=([1e5, 1e6], [0.80, 0.81]))
    assert fc.reynolds.m > 1e6
    assert_allclose(fc.C.m, 0.81)
    assert set(fc.outside_limits) == {"calibration"}


@pytest.mark.parametrize(
    "kwargs,limit,match",
    [
        (dict(D=Q_(600, "mm"), dc=Q_(432, "mm")), "D", "D = 600.0 mm"),
        (dict(D=Q_(40, "mm"), dc=Q_(28.8, "mm")), "D", "D = 40.0 mm"),
        (dict(dc=Q_(150, "mm")), "beta", "beta = 0.8"),
        (dict(dc=Q_(225, "mm")), "beta", "beta = 0.43"),
        (dict(delta_p=Q_(0.1, "Pa")), "reynolds", "ReD = "),
        # a smaller pipe keeps ReD within its limits at this delta_p
        (
            dict(delta_p=Q_(3, "bar"), D=Q_(100, "mm"), dc=Q_(72, "mm")),
            "pressure_ratio",
            "p2/p1 = 0.7",
        ),
    ],
)
def test_flow_cone_limits(state, kwargs, limit, match):
    with pytest.warns(FlowMeterWarning, match=match):
        fc = cone(state, **kwargs)
    assert set(fc.outside_limits) == {limit}


def test_flow_cone_pressure_ratio_limit_applies_to_calibrated_meters(state):
    with pytest.warns(FlowMeterWarning, match="expansibility"):
        fc = cone(state, C=0.8, delta_p=Q_(3, "bar"))
    assert set(fc.outside_limits) == {"pressure_ratio"}


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (dict(d=Q_(170, "mm")), "exactly one of d"),
        (dict(dc=None), "exactly one of d"),
        (dict(dc=Q_(250, "mm")), "dc must be between"),
        (dict(dc=None, d=Q_(300, "mm")), "d must be between"),
        (dict(D=0), "positive pipe diameter"),
        (dict(delta_p=0), "delta_p must be positive"),
        (dict(C=[[1e5, 1e6, 1e7]]), "calibration table"),
        (dict(C=([0, 1e6], [0.8, 0.81])), "must be > 0"),
        (dict(C=lambda Re: Re / 1e6), "did not converge"),
    ],
)
def test_flow_cone_invalid_input(state, kwargs, match):
    with pytest.raises(ValueError, match=match):
        cone(state, **kwargs)


@pytest.mark.filterwarnings("ignore::ccp.state.IdealGasWarning")
def test_flow_cone_ideal_gas(no_meter_warnings):
    s = ccp.State(p=1e6, T=300.0, fluid={"n2": 1}, EOS="ideal")
    fc = ccp.FlowCone(s, Q_(0.1, "bar"), D=0.3, d=0.18)
    assert fc.flow_m.m > 0
    assert_allclose(
        fc.epsilon.m, 1 - (0.649 + 0.696 * 0.6**4) * 1e4 / (1.4 * 1e6), rtol=1e-3
    )
