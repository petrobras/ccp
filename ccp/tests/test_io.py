import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from numpy.testing import assert_allclose
from pandas.testing import assert_frame_equal
import ccp
import ccp.data_io

Q_ = ccp.Q_

test_dir = Path(__file__).parent
data_dir = test_dir / "data"


@pytest.fixture
def impeller_lp_sec1_from_csv():
    suc = ccp.State(
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
    imp = ccp.Impeller.load_from_engauge_csv(
        suc=suc,
        curve_name="lp-sec1-caso-a",
        curve_path=data_dir,
        b=Q_(5.7, "mm"),
        D=Q_(550, "mm"),
        head_units="kJ/kg",
        flow_units="m³/h",
        speed_units="RPM",
        number_of_points=7,
    )

    return imp


def test_impeller_lp_sec1_from_csv(impeller_lp_sec1_from_csv):
    p0 = impeller_lp_sec1_from_csv[0]
    assert_allclose(p0.flow_v.to("m³/h").m, 11250)
    assert_allclose(p0.speed.to("RPM").m, 6882.0)
    assert_allclose(p0.disch.p().to("bar").m, 9.028963080391938)
    assert_allclose(p0.head.to("kJ/kg").m, 82.87008516878088)
    assert_allclose(p0.eff.m, 0.789412, rtol=1e-5)
    assert_allclose(p0.power.to("kW").m, 1432.5554941076675, rtol=1e-4)


def test_fluctuation():
    assert_allclose(ccp.data_io.fluctuation(np.array([1, 2, 3, 4, 5])), 133.333333)
    assert_allclose(ccp.data_io.fluctuation(np.array([1, 1, 1, 1, 1])), 0.0)


def test_fluctuation_data():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [4, 5, 6, 7]})
    assert_frame_equal(
        ccp.data_io.fluctuation_data(df),
        pd.DataFrame(
            {"a": [100.0, 66.66666666666667], "b": [40.0, 33.333333333333336]},
            index=[2, 3],
        ),
    )


def test_mean_data():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [4, 5, 6, 7]})
    assert_frame_equal(
        ccp.data_io.mean_data(df),
        pd.DataFrame({"a": [2.0, 3.0], "b": [5.0, 6.0]}, index=[2, 3]),
    )


def test_filter_data():
    df = pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 4.01, 4.02, 5, 6.01, 6.02, 6.04, 6.05],
            "b": [4, 5, 6, 7, 7.01, 7.02, 8, 9, 10, 11, 12],
        }
    )
    assert_frame_equal(
        ccp.data_io.filter_data(df, data_type={"a": "pressure", "b": "temperature"}),
        pd.DataFrame(
            index=pd.Index([5]), data={"a": [4.01], "b": [7.01], "valid": [True]}
        ),
    )


def test_filter_data_flag():
    df = pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 4.01, 4.02, 5, 6.01, 6.02, 6.04, 6.05],
            "b": [4, 5, 6, 7, 7.01, 7.02, 8, 9, 10, 11, 12],
        }
    )
    assert_frame_equal(
        ccp.data_io.filter_data(
            df,
            data_type={"a": "pressure", "b": "temperature"},
            drop_invalid_values=False,
        ),
        pd.DataFrame(
            index=pd.Index(range(2, 11, 1)),
            data={
                "a": [
                    2.0,
                    3.0,
                    3.67,
                    4.01,
                    4.343333333333333,
                    5.01,
                    5.676666666666667,
                    6.023333333333333,
                    6.036666666666666,
                ],
                "b": [
                    5.0,
                    6.0,
                    6.669999999999999,
                    7.010000000000001,
                    7.343333333333334,
                    8.006666666666666,
                    9.0,
                    10.0,
                    11.0,
                ],
                "valid": [
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
            },
        ),
    )


def test_filter_real_data():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data.parquet")
    data_type = {
        "ps": "pressure",
        "Ts": "temperature",
        "pd": "pressure",
        "Td": "temperature",
        "speed": "speed",
        "delta_p": "delta_p",
    }

    df = ccp.data_io.filter_data(
        df,
        data_type=data_type,
    )

    assert len(df) == 2
