"""Tests for the gp_surrogate converter (``Impeller.convert_from(method=...)``)."""

import numpy as np
import pytest
from numpy.testing import assert_allclose

import ccp
from ccp import Q_, Impeller, Point, State

B = Q_(28.5, "mm")
D = Q_(365, "mm")

FLUID = dict(methane=0.85, ethane=0.07, propane=0.04, co2=0.02, n2=0.02)


def _map_at(suc, speeds_rpm, phis=np.linspace(0.03, 0.09, 6)):
    """Build an Impeller from a fixed non-dimensional map evaluated at ``suc``.

    psi(phi) is a decreasing line and eff(phi) a parabola, so the surrogate has a real
    phi-dependence to recover (and a non-flat efficiency).
    """
    points = []
    for speed_rpm in speeds_rpm:
        speed = Q_(speed_rpm, "RPM")
        u = (speed * D / 2).to("m/s")
        for phi in phis:
            psi = 1.2 - 4.0 * phi  # decreasing head coefficient
            eff = 0.85 - 60.0 * (phi - 0.06) ** 2  # parabola peaking at phi=0.06
            flow_v = (phi * np.pi * D**2 * u / 4).to("m**3/s")
            head = (psi * u**2 / 2).to("J/kg")
            points.append(
                Point(
                    suc=suc,
                    flow_v=flow_v,
                    speed=speed,
                    head=head,
                    eff=Q_(eff, "dimensionless"),
                    b=B,
                    D=D,
                )
            )
    return Impeller(points)


@pytest.fixture
def maps():
    """Three measured maps at different suction pressures (-> different Mach)."""
    speeds = [9000, 10500, 12000]
    sucs = [
        State(p=Q_(p, "bar"), T=Q_(310, "K"), fluid=FLUID) for p in (15.0, 20.0, 25.0)
    ]
    return [_map_at(suc, speeds) for suc in sucs]


def test_returns_valid_impeller(maps):
    target = maps[1].points[0].suc
    conv = Impeller.convert_from(maps, suc=target, method="gp_surrogate")

    assert isinstance(conv, Impeller)
    # one curve per representative speed line (all maps share 3 speeds)
    assert len(conv.curves) == 3
    for curve in conv.curves:
        effs = np.array([p.eff.m for p in curve.points])
        assert np.all((effs > 0) & (effs < 1))


def test_no_extrapolation_artifact(maps):
    """Regression for the Mach-local phi grid (plan §6.1).

    Head must rise from choke (high flow) toward surge (low flow); a low-flow head dive
    would signal the GP extrapolating into the empty low-phi/high-Mach corner.
    """
    target = maps[2].points[0].suc
    conv = Impeller.convert_from(maps, suc=target, method="gp_surrogate")

    for curve in conv.curves:
        pts = sorted(curve.points, key=lambda p: p.flow_v.m)
        heads = np.array([p.head.m for p in pts])
        # head strictly decreasing from surge (low flow) to choke (high flow)
        assert np.all(np.diff(heads) < 0)


def test_efficiency_not_flat_and_deterministic(maps):
    """Regression for the bounded+seeded kernel (plan §6.2)."""
    target = maps[0].points[0].suc
    conv1 = Impeller.convert_from(maps, suc=target, method="gp_surrogate")
    conv2 = Impeller.convert_from(maps, suc=target, method="gp_surrogate")

    for curve in conv1.curves:
        effs = np.array([p.eff.m for p in curve.points])
        assert effs.max() - effs.min() > 0.03  # a real parabola, not collapsed to mean

    # random_state=0 -> deterministic across calls
    h1 = [p.head.m for c in conv1.curves for p in c.points]
    h2 = [p.head.m for c in conv2.curves for p in c.points]
    assert_allclose(h1, h2)


def test_single_impeller_allowed(maps):
    target = maps[0].points[0].suc
    conv = Impeller.convert_from(maps[0], suc=target, method="gp_surrogate")
    assert isinstance(conv, Impeller)
    assert len(conv.curves) == 3


def test_speed_argument_single_curve(maps):
    target = maps[1].points[0].suc
    conv = Impeller.convert_from(
        maps, suc=target, speed=Q_(10500, "RPM"), method="gp_surrogate"
    )
    assert len(conv.curves) == 1
    assert_allclose(conv.curves[0].speed.to("RPM").m, 10500, rtol=1e-6)


def test_default_method_unchanged():
    """method defaults to 'similarity' and matches an explicit similarity call."""
    imp = ccp.impeller_example()
    new_suc = imp.points[0].suc
    default = Impeller.convert_from(imp, suc=new_suc, speed="same")
    explicit = Impeller.convert_from(
        imp, suc=new_suc, speed="same", method="similarity"
    )
    h_default = [p.head.m for c in default.curves for p in c.points]
    h_explicit = [p.head.m for c in explicit.curves for p in c.points]
    assert_allclose(h_default, h_explicit)


def test_unknown_method_raises(maps):
    target = maps[0].points[0].suc
    with pytest.raises(ValueError, match="unknown method"):
        Impeller.convert_from(maps, suc=target, method="bogus")


def test_suc_none_raises(maps):
    with pytest.raises(ValueError, match="suc is required"):
        Impeller.convert_from(maps, suc=None, method="gp_surrogate")


def test_mismatched_geometry_raises(maps):
    # a map with a different impeller diameter D -> geometry mismatch
    big_D = Q_(400, "mm")
    suc = State(p=Q_(18, "bar"), T=Q_(310, "K"), fluid=FLUID)
    u = (Q_(9000, "RPM") * big_D / 2).to("m/s")
    points = []
    for phi in (0.04, 0.05, 0.06):
        points.append(
            Point(
                suc=suc,
                flow_v=(phi * np.pi * big_D**2 * u / 4).to("m**3/s"),
                speed=Q_(9000, "RPM"),
                head=((1.2 - 4.0 * phi) * u**2 / 2).to("J/kg"),
                eff=Q_(0.8, "dimensionless"),
                b=B,
                D=big_D,
            )
        )
    other = Impeller(points)
    with pytest.raises(ValueError, match="same\\s+geometry"):
        Impeller.convert_from(
            [maps[0], other], suc=maps[0].points[0].suc, method="gp_surrogate"
        )
