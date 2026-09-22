import math

import pytest
from numpy.testing import assert_allclose

from ccp.roots import solve_monotone


def counting(f):
    calls = []

    def inner(x):
        calls.append(x)
        return f(x)

    inner.calls = calls
    return inner


def test_secant_from_good_guess_is_cheap():
    f = counting(lambda x: x**3 - 2.0)
    root = 2.0 ** (1 / 3)
    x = solve_monotone(f, 1.25, 0.0, 10.0)
    assert_allclose(x, root, rtol=1e-8)
    assert len(f.calls) <= 6
    # every evaluation stays inside the physical interval
    assert all(0.0 <= c <= 10.0 for c in f.calls)


def test_decreasing_residual_and_far_guess():
    f = counting(lambda x: math.exp(-x) - 0.3)
    x = solve_monotone(f, 10.0, 0.0, 50.0, increasing=False)
    assert_allclose(x, -math.log(0.3), rtol=1e-8)
    assert len(f.calls) <= 15


def test_guess_at_the_boundary_is_clamped():
    f = counting(lambda x: x - 3.0)
    x = solve_monotone(f, -5.0, 0.0, 10.0)
    assert_allclose(x, 3.0, rtol=1e-8)
    assert f.calls[0] == 0.0


def test_second_guess_secant():
    f = counting(lambda x: x**2 - 4.0)
    x = solve_monotone(f, 1.9, 0.0, 10.0, x1=2.1)
    assert_allclose(x, 2.0, rtol=1e-8)
    assert len(f.calls) <= 6


def test_no_root_in_interval_raises():
    with pytest.raises(ValueError, match="no root"):
        solve_monotone(lambda x: x + 1.0, 5.0, 0.0, 10.0)
    with pytest.raises(ValueError, match="no root"):
        solve_monotone(lambda x: x - 20.0, 5.0, 0.0, 10.0)


def test_residual_failures_are_stepped_around():
    # the residual cannot be evaluated above 5: the solver shortens its steps
    def f(x):
        if x > 5.0:
            raise ValueError("flash failed")
        return x - 4.0

    f = counting(f)
    x = solve_monotone(f, 2.0, 0.0, 100.0)
    assert_allclose(x, 4.0, rtol=1e-8)


def test_flat_then_steep_residual_converges():
    # convex residual: the one-sided secant must still bracket or stop cleanly
    f = counting(lambda x: x**8 - 256.0)
    x = solve_monotone(f, 1.0, 0.0, 100.0)
    assert_allclose(x, 2.0, rtol=1e-8)
    assert len(f.calls) <= 30


def test_max_evals():
    with pytest.raises(ValueError, match="no convergence"):
        solve_monotone(lambda x: math.tanh(x - 3.0), 0.0, -1e6, 1e6, max_evals=3)
