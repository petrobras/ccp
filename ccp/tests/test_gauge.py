import logging
import pickle
import threading
import time

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose

import ccp
from ccp.config.units import _absolute, check_units
from ccp.units import absolute_to_gauge, gauge_to_absolute

Q_ = ccp.Q_
FLUID = {"CarbonDioxide": 1}


@pytest.mark.parametrize(
    "unit, reference",
    [("barg", "bar"), ("psig", "psi"), ("kPag", "kPa"), ("MPag", "MPa")],
)
def test_gauge_units(unit, reference):
    ambient = Q_(101325, "Pa").to(reference).m
    assert_allclose(Q_(10, unit).to(reference).m, 10 + ambient)
    assert_allclose(Q_(10 + ambient, reference).to(unit).m, 10)
    assert_allclose(Q_([0, 10], unit).to(reference).m, [ambient, 10 + ambient])
    # not only the round trip: also the scale
    assert_allclose(Q_(0, unit).to("Pa").m, 101325)
    assert pickle.loads(pickle.dumps(Q_(10, unit))).units == Q_(1, unit).units


def test_state():
    s = ccp.State(p=Q_(10, "barg"), T=300, fluid=FLUID, EOS="HEOS")
    reference = ccp.State(p=Q_(11.01325, "bar"), T=300, fluid=FLUID, EOS="HEOS")
    assert_allclose(s.p().m, reference.p().m)
    assert_allclose(s.rho().m, reference.rho().m)
    assert_allclose(s.p("barg").m, 10)
    s.update(p=Q_(5, "barg"), T=300)
    assert_allclose(s.p("bar").m, 6.01325)


def test_context():
    with ccp.ambient_pressure(Q_(0.9, "bar")):
        assert_allclose(ccp.config.AMBIENT_PRESSURE, 90000)
        assert_allclose(Q_(10, "barg").to("bar").m, 10.9)
        with ccp.ambient_pressure(80000):
            assert_allclose(Q_(0, "psig").to("Pa").m, 80000)
        assert_allclose(Q_(10, "barg").to("bar").m, 10.9)
    assert ccp.config.AMBIENT_PRESSURE == 101325
    assert_allclose(Q_(10, "barg").to("bar").m, 11.01325)


def test_context_restores_on_exception():
    with pytest.raises(KeyError):
        with ccp.ambient_pressure(Q_(0.9, "bar")):
            raise KeyError
    assert_allclose(Q_(0, "barg").to("Pa").m, 101325)
    # the lock was released
    thread = threading.Thread(target=ccp.set_ambient_pressure, args=(95000,))
    thread.start()
    thread.join(10)
    assert not thread.is_alive()
    assert ccp.config.AMBIENT_PRESSURE == 95000


def test_set_and_assign():
    ccp.set_ambient_pressure(Q_(0.95, "bar"))
    assert_allclose(Q_(0, "barg").to("Pa").m, 95000)
    # an assignment also redefines the units
    ccp.config.AMBIENT_PRESSURE = Q_(0.9, "bar")
    assert_allclose(Q_(0, "barg").to("Pa").m, 90000)
    assert_allclose(gauge_to_absolute(0).m, 90000)


@pytest.mark.parametrize(
    "value",
    [0, -1, np.nan, np.inf, Q_(0.1, "barg"), Q_(14.7, "psig")],
    ids=str,
)
def test_invalid_ambient(value):
    with pytest.raises(ValueError):
        ccp.set_ambient_pressure(value)
    with pytest.raises(ValueError):
        with ccp.ambient_pressure(value):
            pass
    assert ccp.config.AMBIENT_PRESSURE == 101325


def test_set_waits_for_context():
    with ccp.ambient_pressure(90000):
        thread = threading.Thread(target=ccp.set_ambient_pressure, args=(95000,))
        thread.start()
        thread.join(0.2)
        assert thread.is_alive()
        assert_allclose(Q_(0, "barg").to("Pa").m, 90000)
    thread.join(10)
    assert_allclose(Q_(0, "barg").to("Pa").m, 95000)


def test_interrupted_redefinition(monkeypatch):
    from ccp.config.units import ureg

    build_cache = ureg._build_cache
    calls = []

    def interrupted():
        calls.append(1)
        if len(calls) == 1:
            raise KeyboardInterrupt
        return build_cache()

    monkeypatch.setattr(ureg, "_build_cache", interrupted)
    with pytest.raises(KeyboardInterrupt):
        with ccp.ambient_pressure(90000):
            pass
    assert ccp.config.AMBIENT_PRESSURE == 101325
    assert_allclose(Q_(0, "barg").to("Pa").m, 101325)


def test_units_redefined_by_other_code():
    ccp.ureg.define("barg = 1 * bar; offset: 0.9")
    ccp.set_ambient_pressure(101325)
    assert_allclose(Q_(0, "barg").to("Pa").m, 101325)


def test_no_redefinition_warnings(caplog):
    with caplog.at_level(logging.WARNING):
        ccp.set_ambient_pressure(np.float64(90000))
    assert not caplog.records


def test_pure_functions():
    p = gauge_to_absolute(Q_(10, "kgf/cm²"))
    assert p.units == Q_(1, "kgf/cm²").units
    assert_allclose(p.m, 10 + 101325 / 98066.5)
    ambient = Q_(0.9, "bar")
    assert_allclose(gauge_to_absolute(Q_(10, "bar"), ambient).m, 10.9)
    assert_allclose(gauge_to_absolute(Q_([0, 10], "bar"), ambient).m, [0.9, 10.9])
    assert_allclose(absolute_to_gauge(Q_(11, "bar"), units="bar").m, 11 - 1.01325)
    assert_allclose(
        absolute_to_gauge(Q_(11, "bar"), "kgf/cm²", ambient).m, 10.1e5 / 98066.5
    )
    assert_allclose(
        absolute_to_gauge(Q_(np.array([1.9, 2.9]), "bar"), "kPa", ambient).m, [100, 200]
    )
    ambients = Q_([0.9, 1.0], "bar")
    assert_allclose(gauge_to_absolute(Q_(10, "bar"), ambients).m, [10.9, 11])
    for bad in (Q_(1, "barg"), 0, Q_([1, -1], "bar")):
        with pytest.raises(ValueError):
            gauge_to_absolute(Q_(10, "bar"), bad)
    # an explicit ambient does not depend on the global one
    with ccp.ambient_pressure(50000):
        assert_allclose(gauge_to_absolute(Q_(10, "bar"), ambient).m, 10.9)


def test_pure_functions_refuse_gauge_units():
    # would add the ambient pressure twice
    with pytest.raises(ValueError, match="plain"):
        gauge_to_absolute(Q_(10, "barg"))
    with pytest.raises(ValueError, match="plain"):
        absolute_to_gauge(Q_(10, "barg"))
    with pytest.raises(ValueError, match="plain"):
        absolute_to_gauge(Q_(10, "bar"), units="barg")


def test_pressure_difference():
    s = ccp.State(p=Q_(10, "bar"), T=300, fluid=FLUID, EOS="HEOS")
    kwargs = dict(D=Q_(250, "mm"), d=Q_(170, "mm"))
    for meter in (ccp.FlowOrifice, ccp.FlowCone):
        with pytest.raises(ValueError, match="difference"):
            meter(s, Q_(0.1, "barg"), **kwargs)
        with pytest.raises(ValueError, match="difference"):
            meter(s, delta_p=Q_(0.1, "barg"), **kwargs)

    @check_units
    def func(delta_p):
        return delta_p

    assert_allclose(func(Q_(0.1, "bar")).m, 1e4)
    assert_allclose(func(Q_(1.1, "barg") - Q_(1, "barg")).m, 1e4)


def test_threads():
    n = 4
    barrier = threading.Barrier(n)
    errors = []

    def work(ambient):
        barrier.wait()
        for _ in range(10):
            with ccp.ambient_pressure(ambient):
                time.sleep(0.001)
                value = Q_(1, "barg").to("Pa").m
                if abs(value - 1e5 - ambient) > 1e-6:
                    errors.append((ambient, value))

    threads = [
        threading.Thread(target=work, args=(90000 + 1000 * i,)) for i in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not any(t.is_alive() for t in threads)
    assert not errors
    assert ccp.config.AMBIENT_PRESSURE == 101325


def _state_pressure(state):
    return state


def test_pool_in_context():
    # states are unpickled in a thread of the pool: must not need the lock
    from ccp.parallel import create_pool

    with ccp.ambient_pressure(90000):
        s = ccp.State(p=Q_(1, "barg"), T=300, fluid=FLUID, EOS="HEOS")
        with create_pool(processes=2) as pool:
            (back,) = pool.map(_state_pressure, [s])
    assert_allclose(back.p().m, 190000)
    assert _absolute(Q_(1, "barg")).units == Q_(1, "pascal").units


def _load(suc, offset, units):
    flow = [4.0, 5.0, 6.0, 7.0]
    disch_p = [offset + v for v in (9.0, 8.5, 8.0, 7.5)]
    disch_T = [440.0, 435.0, 430.0, 425.0]
    return ccp.Impeller.load_from_dict(
        suc=suc,
        disch_p_curves={900: {"x1": flow, "x2": disch_p, "x3": 0}},
        disch_T_curves={900: {"x1": flow, "x2": disch_T, "x3": 0}},
        b=0.01,
        D=0.5,
        number_of_points=3,
        flow_units="m**3/s",
        disch_p_units=units,
        disch_T_units="degK",
        speed_units="rad/s",
    )


@pytest.mark.parametrize("parallel", [True, False])
def test_load_from_dict_gauge(parallel):
    ccp.config.PARALLEL = parallel
    ccp.config.POOL_SIZE = 2
    suc = ccp.State(p=Q_(3, "bar"), T=300, fluid=FLUID, EOS="HEOS")
    with ccp.ambient_pressure(Q_(0.9, "bar")):
        gauge = _load(suc, -0.9, "barg")
    absolute = _load(suc, 0, "bar")
    for a, b in zip(gauge.points, absolute.points):
        assert_allclose(a.disch.p().m, b.disch.p().m, rtol=1e-9)


def _evaluation(units, ambient=None):
    e = object.__new__(ccp.Evaluation)
    e.data_units = units
    e.ambient_pressure = Q_(ambient or 101325, "Pa")
    e.data_type = {"ps": "pressure", "pd": "pressure"}
    e.window = 3
    e.temperature_fluctuation = e.speed_fluctuation = 0.5
    e.pressure_fluctuation = 2
    return e


def test_evaluation_filter_is_absolute():
    data = pd.DataFrame({"ps": [0.0, 0.01, 0.0, -0.01], "pd": [5.0] * 4})
    out = _evaluation({"ps": "barg", "pd": "barg"})._filter_dataframe(data)
    assert len(out) == 2
    assert_allclose(out["pd"], 5)
    # the data is not changed
    assert_allclose(data["ps"], [0.0, 0.01, 0.0, -0.01])


def test_evaluation_pressure():
    e = _evaluation({"ps": "barg", "pd": "bar"}, 90000)
    assert_allclose(e._pressure(1.0, "ps").to("bar").m, 1.9)
    # bound to the evaluation, not to the global ambient pressure
    with ccp.ambient_pressure(50000):
        assert_allclose(e._pressure(1.0, "ps").to("bar").m, 1.9)
    assert e._pressure(1.0, "pd") == Q_(1.0, "bar")


def test_evaluation_refuses_gauge_delta_p():
    with pytest.raises(ValueError, match="delta_p"):
        ccp.Evaluation(data=pd.DataFrame({"ps": []}), data_units={"delta_p": "barg"})
