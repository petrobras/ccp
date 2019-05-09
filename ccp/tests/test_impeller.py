import pytest
import numpy as np
from numpy.testing import assert_allclose
from ccp import ureg, Q_, State, Point, Curve, Impeller


@pytest.fixture
def points0():
    #  see Ludtke pg. 173 for values.
    fluid = dict(n2=0.0318,
                 co2=0.0118,
                 methane=0.8737,
                 ethane=0.0545,
                 propane=0.0178,
                 ibutane=0.0032,
                 nbutane=0.0045,
                 ipentane=0.0011,
                 npentane=0.0009,
                 nhexane=0.0007)
    suc = State.define(p=Q_(62.7, 'bar'), T=Q_(31.2, 'degC'), fluid=fluid)
    disch = State.define(p=Q_(76.82, 'bar'), T=Q_(48.2, 'degC'), fluid=fluid)
    disch1 = State.define(p=Q_(76., 'bar'), T=Q_(48., 'degC'), fluid=fluid)
    p0 = Point(suc=suc, disch=disch, flow_m=85.9, speed=Q_(13971, 'RPM'))
    p1 = Point(suc=suc, disch=disch1, flow_m=86.9, speed=Q_(13971, 'RPM'))
    return p0, p1


@pytest.fixture
def imp0(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1], b=Q_(44.2, 'mm'), D=0.318)
    return imp0


def test_impeller_tip_speed(imp0):
    assert imp0._u(point=imp0[0]).units == 'meter * radian/second'
    assert imp0._u(point=imp0[0]).magnitude == 232.62331210550587


def test_impeller_phi(imp0):
    assert imp0._phi(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._phi(point=imp0[0]).magnitude, 0.089302, rtol=1e-3)


def test_impeller_psi(imp0):
    assert imp0._psi(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._psi(point=imp0[0]).magnitude, 0.932116, rtol=1e-3)


def test_impeller_s(imp0):
    assert imp0._work_input_factor(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._work_input_factor(point=imp0[0]).magnitude, 0.547231, rtol=1e-6)


def test_impeller_mach(imp0):
    assert imp0._mach(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._mach(point=imp0[0]).magnitude, 0.578539, rtol=1e-4)


def test_impeller_reynolds(imp0):
    assert imp0._reynolds(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._reynolds(point=imp0[0]).magnitude,
                    41962131.803386, rtol=1e-4)


def test_impeller_s(imp0):
    assert imp0._sigma(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._sigma(point=imp0[0]).magnitude, 0.31502, rtol=1e-6)


def test_impeller_non_dimensional_parameters_for_points(imp0):
    assert_allclose(imp0.points[0].phi, 0.089292, rtol=1e-5)
    assert_allclose(imp0.points[0].psi, 0.932116, rtol=1e-3)
    assert_allclose(imp0.points[0].eff, 0.851666, rtol=1e-3)
    assert_allclose(imp0.points[0].volume_ratio, 0.867777, rtol=1e-5)
    assert_allclose(imp0.points[0].mach, 0.578539, rtol=1e-4)
    assert_allclose(imp0.points[0].reynolds, 41962131.803386, rtol=1e-3)


@pytest.fixture
def imp1():
    fluid = dict(methane=0.69945,
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
                 water=0.002)
    suc = State.define(p=Q_(1.6995, 'MPa'), T=311.55, fluid=fluid)

    p0 = Point(suc=suc, flow_v=Q_(6501.67, 'm**3/h'), speed=Q_(11145, 'RPM'),
               head=Q_(179.275, 'kJ/kg'), eff=0.826357)
    p1 = Point(suc=suc, flow_v=Q_(7016.72, 'm**3/h'), speed=Q_(11145, 'RPM'),
               head=Q_(173.057, 'kJ/kg'), eff=0.834625)

    imp1 = Impeller([p0, p1], b=Q_(28.5, 'mm'), D=Q_(365, 'mm'))

    return imp1


def test_impeller_new_suction(imp1):
    new_suc = State.define(p=Q_(0.2, 'MPa'), T=301.58,
                           fluid='nitrogen')
    imp1.suc = new_suc
    p0 = imp1[0]
    new_p0 = imp1.new.points[0]

    assert_allclose(new_p0.eff, p0.eff)
    assert_allclose(new_p0.phi, p0.phi, rtol=1e-2)
    assert_allclose(new_p0.psi, p0.psi, rtol=1e-2)
    assert_allclose(new_p0.head, 208933.668804)
    assert_allclose(new_p0.power, 1101698.5104, rtol=1e-3)
    assert_allclose(new_p0.speed, 1257.17922, rtol=1e-3)


def test_impeller_new_speed(imp1):
    assert imp1.speed is None
    new_suc = State.define(p=Q_(0.2, 'MPa'), T=301.58,
                           fluid='nitrogen')
    with pytest.raises(NotImplementedError) as ex:
        imp1.suc = new_suc
        imp1.flow_v = 2.
        imp1.speed = 1000.
    assert 'Not implemented for less' in str(ex)


@pytest.fixture()
def imp2():
    points = [
        Point(suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
              speed=Q_("1263 rad/s"), flow_v=Q_("1.15 m³/s"),
              head=Q_("147634 J/kg"), eff=Q_("0.819")),
        Point(suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
              speed=Q_("1263 rad/s"), flow_v=Q_("1.26 m³/s"),
              head=Q_("144664 J/kg"), eff=Q_("0.829")),
        Point(suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
              speed=Q_("1263 rad/s"), flow_v=Q_("1.36 m³/s"),
              head=Q_("139945 J/kg"), eff=Q_("0.831")),
        Point(suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
             speed=Q_("1337 rad/s"), flow_v=Q_("1.22 m³/s"),
             head=Q_("166686 J/kg"), eff=Q_("0.814")),
        Point(suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
              speed=Q_("1337 rad/s"), flow_v=Q_("1.35 m³/s"),
              head=Q_("163620 J/kg"), eff=Q_("0.825")),
        Point(suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
              speed=Q_("1337 rad/s"), flow_v=Q_("1.48 m³/s"),
              head=Q_("158536 J/kg"), eff=Q_("0.830"))
    ]

    imp2 = Impeller(points, b=0.010745, D=0.32560)

    return imp2


def test_impeller_disch_state(imp2):
    T_magnitude = np.array([[482.850310, 477.243856, 471.29533],
                            [506.668177, 500.418404, 493.30993]])
    assert_allclose(imp2.disch.T().magnitude, T_magnitude, )


