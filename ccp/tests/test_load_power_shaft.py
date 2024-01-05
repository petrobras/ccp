import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from numpy.testing import assert_allclose
import ccp
from ccp import Q_

test_dir = Path(__file__).parent
data_dir = test_dir / "data"


@pytest.fixture
def suc_0():
    patm = Q_(101.3, "kPa")

    suc = ccp.State(
        p=Q_(1599, "kPa") + patm,
        T=Q_(40, "degC"),
        fluid={"NITROGEN": 0.96, "OXYGEN": 0.04},
    )
    return suc


@pytest.fixture
def imp_0(suc_0):
    imp = ccp.Impeller.load_from_engauge_csv(
        suc=suc_0,
        curve_name="p78-main-N2",
        curve_path=data_dir,
        b=Q_(4, "mm"),
        D=Q_(375.13, "mm"),
        head_units="kJ/kg",
        power_shaft_units="kW",
        power_losses_units="kW",
        flow_units="m³/min",
        number_of_points=8,
    )
    return imp


@pytest.fixture
def test_point_0(imp_0):
    return imp_0.point(Q_(214.9, "m**3/min"), speed=Q_(13311, "rpm"))


def test_load_power_shaft(suc_0, test_point_0):
    # desired values: vendor results
    patm = Q_(101.3, "kPa")
    assert_allclose(test_point_0.disch.p().to("kPa").m - patm.m, 4770, atol=14)
    assert_allclose(test_point_0.disch.T().to("degC").m, 188.2, atol=1.3)

    assert_allclose(test_point_0.power.to("kW").m, 10242, atol=41)
    assert_allclose(test_point_0.power_shaft.to("kW").m, 10345, atol=43)
    assert_allclose(test_point_0.head.to("kJ/kg").m, 120.1, atol=1)
    assert_allclose(test_point_0.eff.m, 0.7721, atol=1e-2)
    assert test_point_0.speed.to("rpm").m == 13311
    assert_allclose(test_point_0.torque.to("N*m").m, 7421, atol=31)
    assert_allclose(suc_0.molar_mass().to("kg/kmol").m, 28.17, atol=1e-2)
    assert_allclose(
        test_point_0.flow_v.to("m**3/min").m * suc_0.rho().to("kg/m**3").m,
        3950,
        atol=8.4,
    )
