import pytest
from pathlib import Path
from numpy.testing import assert_allclose
import ccp

Q_ = ccp.Q_

test_dir = Path(__file__).parent
data_dir = test_dir / "data"


@pytest.fixture
def impeller_lp_sec1_from_csv():
    suc = ccp.State.define(
        p=Q_(4.08, "bar"),
        T=Q_(33.6, "degC"),
        fluid={
            "METHANE": 58.976,
            "ETHANE": 3.099,
            "PROPANE": 0.6,
            "N-BUTANE": 0.08,
            "I-BUTANE": 0.05,
            "N-PENTANE": 0.01,
            "I-PENTANE": 0.01,
            "NITROGEN": 0.55,
            "HYDROGEN SULFIDE": 0.02,
            "CARBON DIOXIDE": 36.605,
        },
    )
    imp = ccp.Impeller.from_engauge_csv(
        suc=suc,
        curve_name="lp-sec1-caso-a",
        curve_path=data_dir,
        b=Q_(5.7, "mm"),
        D=Q_(550, "mm"),
        head_units="kJ/kg",
        flow_units="m³/h",
        speeds=Q_([6882, 7865, 8848, 9831, 10322], "RPM"),
        number_of_points=7,
    )

    return imp


def test_impeller_lp_sec1_from_csv(impeller_lp_sec1_from_csv):
    p0 = impeller_lp_sec1_from_csv[0]
    assert_allclose(p0.flow_v.to("m³/h"), 11218.7)
    assert_allclose(p0.speed.to("RPM"), 6882.0)
    assert_allclose(p0.disch.p().to("bar"), 9.039631560903004)
    assert_allclose(p0.head.to("kJ/kg"), 83.0088)
    assert_allclose(p0.eff, 0.789377, rtol=1e-5)
    assert_allclose(p0.power.to("kW"), 1431.024873304792)
