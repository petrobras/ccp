import pytest
from numpy.testing import assert_allclose

from ccp import Q_, Point, State
from ccp.similarity import check_similarity, reynolds_limits


@pytest.mark.parametrize("remsp", [9e4, 3e5, 5e5, 8e5, 2e6, 5e7])
def test_reynolds_limits_shared_with_point(remsp):
    suc = State(p=Q_(3, "bar"), T=Q_(300, "K"), fluid={"n2": 1})
    point = Point(
        suc=suc,
        head=Q_(50, "kJ/kg"),
        eff=0.8,
        flow_v=Q_(1, "m**3/s"),
        speed=Q_(7000, "RPM"),
        b=Q_(0.03, "m"),
        D=Q_(0.4, "m"),
    )
    lower, upper = reynolds_limits(remsp)
    limits = point.reynolds_limits(remsp)
    assert_allclose(limits["lower"], lower)
    assert_allclose(limits["upper"], upper)
    assert lower < remsp < upper


def test_reynolds_limits_envelope_is_continuous():
    for edge in (5e5, 8e5):
        below = reynolds_limits(edge * (1 - 1e-6))
        above = reynolds_limits(edge * (1 + 1e-6))
        assert_allclose(below, above, rtol=0.03)
    with pytest.raises(ValueError):
        reynolds_limits(5e4)


def test_check_similarity_reports_the_2022_envelope():
    suc = State(p=Q_(3, "bar"), T=Q_(300, "K"), fluid={"n2": 1})
    kwargs = dict(
        head=Q_(50, "kJ/kg"),
        eff=0.8,
        flow_v=Q_(1, "m**3/s"),
        b=Q_(0.03, "m"),
        D=Q_(0.4, "m"),
    )
    point_sp = Point(suc=suc, speed=Q_(7000, "RPM"), **kwargs)
    point_t = Point(suc=suc, speed=Q_(7200, "RPM"), **kwargs)
    report = check_similarity(point_sp, point_t)
    lower, upper = reynolds_limits(point_sp.reynolds.m)
    remsp = point_sp.reynolds.m
    assert f"({lower / remsp}, {upper / remsp})" in report
