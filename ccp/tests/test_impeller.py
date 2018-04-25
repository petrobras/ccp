import pytest
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
    assert_allclose(imp0._phi(point=imp0[0]).magnitude, 0.089302, rtol=1e-6)


def test_impeller_psi(imp0):
    assert imp0._psi(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0._psi(point=imp0[0]).magnitude, 0.932116, rtol=1e-6)


def test_impeller_s(imp0):
    assert imp0.work_input_factor(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0.work_input_factor(point=imp0[0]).magnitude, 0.547231, rtol=1e-6)


def test_impeller_mach(imp0):
    assert imp0.mach(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0.mach(point=imp0[0]).magnitude, 0.578539, rtol=1e-6)


def test_impeller_reynolds(imp0):
    assert imp0.reynolds(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0.reynolds(point=imp0[0]).magnitude,
                    41962131.803386, rtol=1e-6)


def test_impeller_s(imp0):
    assert imp0.sigma(point=imp0[0]).units == ureg.dimensionless
    assert_allclose(imp0.sigma(point=imp0[0]).magnitude, 0.31501267, rtol=1e-6)


def test_impeller_non_dimensional_points(imp0):
    assert_allclose(imp0.non_dimensional_points[0].phi, 0.089302)
    assert_allclose(imp0.non_dimensional_points[0].psi, 0.932116, rtol=1e-6)
    assert_allclose(imp0.non_dimensional_points[0].eff, 0.851666, rtol=1e-5)
    assert_allclose(imp0.non_dimensional_points[0].volume_ratio, 0.867777)
    assert_allclose(imp0.non_dimensional_points[0].mach, 0.578539, rtol=1e-6)
    assert_allclose(imp0.non_dimensional_points[0].reynolds, 41962131.803386)

    assert_allclose(imp0.non_dimensional_points[1].phi, 0.090342, rtol=1e-5)
    assert_allclose(imp0.non_dimensional_points[1].psi, 0.882954, rtol=1e-6)
    assert_allclose(imp0.non_dimensional_points[1].eff, 0.800351, rtol=1e-6)
    assert_allclose(imp0.non_dimensional_points[1].volume_ratio, 0.87728)
    assert_allclose(imp0.non_dimensional_points[1].mach, 0.578539, rtol=1e-6)
    assert_allclose(imp0.non_dimensional_points[1].reynolds, 41962131.803386)


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
    new_p0 = imp1.new_points[0]

    assert_allclose(new_p0.eff, p0.eff)
    assert_allclose(new_p0.head, 208918.88)
    assert_allclose(new_p0.power, 1101698.5104)
    assert_allclose(new_p0.speed, 1259.9046)

