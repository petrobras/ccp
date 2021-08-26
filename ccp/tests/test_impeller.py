import pytest
import numpy as np
from pathlib import Path
from tempfile import tempdir
from numpy.testing import assert_allclose
from ccp import ureg, Q_, State, Point, Curve, Impeller, impeller_example


@pytest.fixture
def points0():
    #  see Ludtke pg. 173 for values.
    fluid = dict(
        n2=0.0318,
        co2=0.0118,
        methane=0.8737,
        ethane=0.0545,
        propane=0.0178,
        ibutane=0.0032,
        nbutane=0.0045,
        ipentane=0.0011,
        npentane=0.0009,
        nhexane=0.0007,
    )
    suc = State.define(p=Q_(62.7, "bar"), T=Q_(31.2, "degC"), fluid=fluid)
    disch = State.define(p=Q_(76.82, "bar"), T=Q_(48.2, "degC"), fluid=fluid)
    disch1 = State.define(p=Q_(76.0, "bar"), T=Q_(48.0, "degC"), fluid=fluid)
    p0 = Point(
        suc=suc,
        disch=disch,
        flow_m=85.9,
        speed=Q_(13971, "RPM"),
        b=Q_(44.2, "mm"),
        D=0.318,
    )
    p1 = Point(
        suc=suc,
        disch=disch1,
        flow_m=86.9,
        speed=Q_(13971, "RPM"),
        b=Q_(44.2, "mm"),
        D=0.318,
    )
    return p0, p1


@pytest.fixture
def imp0(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1])
    return imp0


@pytest.fixture
def imp1():
    fluid = dict(
        methane=0.69945,
        ethane=0.09729,
        propane=0.0557,
        nbutane=0.0178,
        ibutane=0.0102,
        npentane=0.0039,
        ipentane=0.0036,
        nhexane=0.0018,
        n2=0.0149,
        co2=0.09259,
        h2s=0.00017,
        water=0.002,
    )
    suc = State.define(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    p0 = Point(
        suc=suc,
        flow_v=Q_(6501.67, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(179.275, "kJ/kg"),
        eff=0.826357,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )
    p1 = Point(
        suc=suc,
        flow_v=Q_(7016.72, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(173.057, "kJ/kg"),
        eff=0.834625,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )

    imp1 = Impeller([p0, p1])

    return imp1


def test_impeller_new_suction(imp1):
    new_suc = State.define(
        p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15}
    )
    imp2 = Impeller.convert_from(imp1, suc=new_suc, find="speed")
    p0 = imp1[0]
    new_p0 = imp2[0]

    assert_allclose(new_p0.eff, p0.eff, rtol=1e-4)
    assert_allclose(new_p0.phi, p0.phi, rtol=1e-2)
    assert_allclose(new_p0.psi, p0.psi, rtol=1e-2)
    assert_allclose(new_p0.head, 208933.668804, rtol=1e-2)
    assert_allclose(new_p0.power, 1101698.5104, rtol=1e-2)
    assert_allclose(new_p0.speed, 1257.17922, rtol=1e-3)


@pytest.fixture()
def imp2():
    points = [
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.15 m³/s"),
            head=Q_("147634 J/kg"),
            eff=Q_("0.819"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.26 m³/s"),
            head=Q_("144664 J/kg"),
            eff=Q_("0.829"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.36 m³/s"),
            head=Q_("139945 J/kg"),
            eff=Q_("0.831"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.22 m³/s"),
            head=Q_("166686 J/kg"),
            eff=Q_("0.814"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.35 m³/s"),
            head=Q_("163620 J/kg"),
            eff=Q_("0.825"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.48 m³/s"),
            head=Q_("158536 J/kg"),
            eff=Q_("0.830"),
            b=0.010745,
            D=0.32560,
        ),
    ]

    imp2 = Impeller(points)

    return imp2


def test_impeller_disch_state(imp2):
    T_magnitude = np.array(
        [[482.850310, 477.243856, 471.29533], [506.668177, 500.418404, 493.30993]]
    )
    assert_allclose(
        imp2.disch.T().magnitude,
        T_magnitude,
    )


def test_impeller2_new_suction(imp2):
    new_suc = State.define(
        p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15}
    )
    imp2_new = Impeller.convert_from(imp2, suc=new_suc, find="speed")
    p0 = imp2[0]
    new_p0 = imp2_new[0]

    assert_allclose(new_p0.eff, p0.eff, rtol=1e-4)
    assert_allclose(new_p0.phi, p0.phi, rtol=1e-2)
    assert_allclose(new_p0.psi, p0.psi, rtol=1e-2)
    assert_allclose(new_p0.head, 151889.637082, rtol=1e-2)
    assert_allclose(new_p0.power, 483519.884306, rtol=1e-2)
    assert_allclose(new_p0.speed, 1281.074036, rtol=1e-3)
    assert_allclose(new_p0.mach_diff, -7.12032e-05, rtol=1e-3)
    assert_allclose(new_p0.reynolds_ratio, 0.999879, rtol=1e-3)
    assert_allclose(new_p0.volume_ratio_ratio, 0.999815, rtol=1e-5)


def test_impeller_point():
    imp = impeller_example()
    p0 = imp.point(flow_v=5, speed=900)
    assert_allclose(p0.eff, 0.815333, rtol=1e-4)
    assert_allclose(p0.head, 123609.404849, rtol=1e-4)
    assert_allclose(p0.power, 3310198.015505, rtol=1e-4)


def test_impeller_curve():
    imp = impeller_example()
    c0 = imp.curve(speed=900)
    p0 = c0[0]
    assert_allclose(p0.eff, 0.819344, rtol=1e-4)
    assert_allclose(p0.head, 138229.8066, rtol=1e-4)
    assert_allclose(p0.power, 2959665.959049, rtol=1e-4)


def test_impeller_plot():
    imp = impeller_example()
    fig = imp.eff_plot(flow_v=5, speed=900)
    expected_eff_curve = np.array(
        [
            0.81934403,
            0.82067954,
            0.82181834,
            0.82276904,
            0.82354026,
            0.82414063,
            0.82457877,
            0.82486331,
            0.82500286,
            0.82500604,
            0.8248815,
            0.82463461,
            0.82422282,
            0.82356673,
            0.82258599,
            0.82120027,
            0.81932964,
            0.81691044,
            0.81389999,
            0.81025702,
            0.80594028,
            0.8009081,
            0.79503801,
            0.78802838,
            0.77955346,
            0.76928752,
            0.75690483,
            0.74207966,
            0.72448627,
            0.70379892,
        ]
    )
    assert_allclose(fig.data[5]["y"], expected_eff_curve, rtol=1e-4)
    assert_allclose(fig.data[6]["y"], 0.8153328087147174, rtol=1e-4)


def test_impeller_plot_units():
    imp = impeller_example()
    fig = imp.disch.rho_plot(
        flow_v=Q_(20000, "m³/h"),
        speed=Q_(8594, "RPM"),
        flow_v_units="m³/h",
        speed_units="RPM",
        rho_units="g/cm³",
    )
    expected_rho_curve = np.array(
        [
            0.01110513,
            0.01106211,
            0.01102135,
            0.0109822,
            0.01094401,
            0.01090614,
            0.01086793,
            0.01082874,
            0.01078792,
            0.01074483,
            0.01069882,
            0.01064922,
            0.01059512,
            0.01053538,
            0.01046888,
            0.0103945,
            0.01031111,
            0.01021801,
            0.01011507,
            0.01000216,
            0.00987917,
            0.00974597,
            0.00960169,
            0.00944373,
            0.00926927,
            0.00907549,
            0.00885957,
            0.00861869,
            0.00835002,
            0.00805075,
        ]
    )
    assert_allclose(fig.data[5]["y"], expected_rho_curve, rtol=1e-4)
    assert_allclose(fig.data[6]["y"], 0.00845738254224696, rtol=1e-4)


def test_save_load():
    composition_fd = dict(
        n2=0.4,
        co2=0.22,
        methane=92.11,
        ethane=4.94,
        propane=1.71,
        ibutane=0.24,
        butane=0.3,
        ipentane=0.04,
        pentane=0.03,
        hexane=0.01,
    )
    suc_fd = State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

    test_dir = Path(__file__).parent
    curve_path = test_dir / "data"
    curve_name = "normal"

    imp_fd = Impeller.load_from_engauge_csv(
        suc=suc_fd,
        curve_name=curve_name,
        curve_path=curve_path,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
        number_of_points=6,
        flow_units="kg/h",
        head_units="kJ/kg",
    )
    file = Path(tempdir) / "imp.toml"
    imp_fd.save(file)

    imp_fd_loaded = Impeller.load(file)

    assert imp_fd == imp_fd_loaded
