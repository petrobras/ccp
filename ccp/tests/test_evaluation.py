from pathlib import Path
from tempfile import tempdir

import pandas as pd
import pytest
from numpy.testing import assert_allclose

import ccp

Q_ = ccp.Q_

data_path = Path(ccp.__file__).parent / "tests/data"

# lp-sec1-caso-a design fluid
fluid_a = {
    "methane": 58.976,
    "ethane": 3.099,
    "propane": 0.6,
    "n-butane": 0.08,
    "i-butane": 0.05,
    "n-pentane": 0.01,
    "i-pentane": 0.01,
    "n2": 0.55,
    "h2s": 0.02,
    "co2": 36.605,
}

operation_fluid = {
    "methane": 44.04,
    "ethane": 3.18,
    "propane": 0.66,
    "n-butane": 0.15,
    "i-butane": 0.05,
    "n-pentane": 0.03,
    "i-pentane": 0.02,
    "n2": 0.25,
    "h2s": 0.06,
    "co2": 51.55,
}

data_units = {
    "ps": "bar",
    "Ts": "degC",
    "pd": "bar",
    "Td": "degC",
    "flow_v": "m³/s",
    "speed": "RPM",
}

delta_p_data_units = {
    "ps": "bar",
    "Ts": "degC",
    "pd": "bar",
    "Td": "degC",
    "delta_p": "mmH2O",
    "p_downstream": "bar",
    "speed": "RPM",
}


def _load_imp_a(**kwargs):
    suc_a = ccp.State(p=Q_(4, "bar"), T=Q_(40, "degC"), fluid=fluid_a)
    return ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
        **kwargs,
    )


@pytest.fixture(scope="module")
def imp_a_n4():
    return _load_imp_a(number_of_points=4)


@pytest.fixture(scope="module")
def imp_a():
    return _load_imp_a()


@pytest.fixture(scope="module")
def delta_p_evaluation(imp_a):
    """Evaluation of data_delta_p.parquet clustered on the full dataset.

    Points are not calculated at construction; tests call calculate_points
    on the slice they need. Constructed once and shared by tests that only
    read from it.
    """
    df = pd.read_parquet(data_path / "data_delta_p.parquet")
    return ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units=delta_p_data_units,
        impellers=[imp_a],
        D=Q_(0.590550, "m"),
        d=Q_(0.366130, "m"),
        tappings="flange",
        n_clusters=2,
        calculate_points=False,
    )


def test_evaluation(imp_a_n4):
    df = pd.read_parquet(data_path / "data.parquet")

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units=data_units,
        impellers=[imp_a_n4],
        n_clusters=2,
    )

    assert_allclose(evaluation.df["delta_eff"].mean(), 11.115457, rtol=1e-2)

    # save evaluation in temporary file
    file = Path(tempdir) / "evaluation.ccp_eval"
    evaluation.save(file)

    loaded_evaluation = ccp.Evaluation.load(file)
    assert_allclose(loaded_evaluation.df["delta_eff"].mean(), 11.115457, rtol=1e-2)
    assert loaded_evaluation.impellers_new[0] == evaluation.impellers_new[0]


def test_evaluation_fluid_columns(imp_a_n4):
    df = pd.read_parquet(data_path / "data.parquet")

    for comp, frac in operation_fluid.items():
        df[f"fluid_{comp}"] = frac

    evaluation = ccp.Evaluation(
        data=df,
        data_units=data_units,
        impellers=[imp_a_n4],
        n_clusters=2,
    )

    assert_allclose(evaluation.df["delta_eff"].mean(), 11.115457, rtol=1e-2)


def test_evaluation_fluid_columns_ppm(imp_a_n4):
    df = pd.read_parquet(data_path / "data.parquet")

    ppm_fluid = dict(operation_fluid)
    ppm_fluid["n-pentane"] = ppm_fluid["n-pentane"] * 1e6  # check with ppm

    for comp, frac in ppm_fluid.items():
        df[f"fluid_{comp}"] = frac

    evaluation = ccp.Evaluation(
        data=df,
        data_units={**data_units, "fluid_n-pentane": "ppm"},
        impellers=[imp_a_n4],
        n_clusters=2,
    )

    assert_allclose(evaluation.df["delta_eff"].mean(), 11.115457, rtol=1e-2)


def test_evaluation_calculate_points(imp_a):
    df = pd.read_parquet(data_path / "data.parquet")

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units=data_units,
        impellers=[imp_a],
        calculate_points=False,
        n_clusters=2,
    )

    df_results = evaluation.calculate_points(df)
    assert_allclose(df_results["delta_eff"].mean(), 10.963751, rtol=1e-2)


def test_evaluation_delta_p(imp_a):
    """Points calculated during __init__ match an explicit calculate_points call.

    Runs on a contiguous slice of the dataset (the fluctuation-window filter
    removes rows of a non-contiguous sample); the regression value for the
    delta_p dataset is anchored by test_evaluation_calculate_points_delta_p.
    """
    df = pd.read_parquet(data_path / "data_delta_p.parquet")[:100]

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units=delta_p_data_units,
        impellers=[imp_a],
        D=Q_(0.590550, "m"),
        d=Q_(0.366130, "m"),
        tappings="flange",
        n_clusters=2,
    )

    df_results = evaluation.calculate_points(df)
    assert len(evaluation.df) > 0
    assert_allclose(
        evaluation.df["delta_eff"].mean(),
        df_results["delta_eff"].mean(),
        rtol=1e-6,
    )
    assert_allclose(evaluation.df["delta_eff"].mean(), 21.796171, rtol=1e-2)


def test_evaluation_calculate_points_delta_p(delta_p_evaluation):
    df = pd.read_parquet(data_path / "data_delta_p.parquet")

    df_results = delta_p_evaluation.calculate_points(df[:400])
    assert_allclose(df_results["delta_eff"].mean(), 21.205854, rtol=1e-2)


def test_evaluation_calculate_points_delta_p_flag(delta_p_evaluation):
    df = pd.read_parquet(data_path / "data_delta_p.parquet")

    df_results = delta_p_evaluation.calculate_points(
        df[:400], drop_invalid_values=False
    )
    # check mean with invalid values (-1)
    assert_allclose(df_results["delta_eff"].mean(), 2.570791, rtol=1e-2)

    # removing invalid values recovers the drop_invalid_values=True result
    df_results = df_results[df_results.valid]
    assert_allclose(df_results["delta_eff"].mean(), 21.205854, rtol=1e-2)


def test_evaluation_calculate_points_delta_p_3_values(delta_p_evaluation):
    df = pd.read_parquet(data_path / "data_delta_p.parquet")

    df_results = delta_p_evaluation.calculate_points(df[:3], drop_invalid_values=False)
    # check mean with invalid values (-1)
    assert_allclose(df_results["delta_eff"].mean(), -1, rtol=1e-2)


def test_wet_cluster_suction_warns_instead_of_raising():
    """A cluster centre at the dew line is converted with a PhaseWarning.

    Composition and conditions of the example_evaluation_pi.ccp cluster that
    sits at vapour quality 0.99; a stand-alone Point still refuses it.
    """
    import copy
    import pickle

    from ccp.evaluation import _allow_wet_cluster_suction
    from ccp.point import PhaseWarning, _check_single_phase_suction

    fluid = {
        "methane": 0.6367,
        "co2": 0.12112,
        "ethane": 0.10393,
        "propane": 0.06955,
        "n-butane": 0.02824,
        "i-butane": 0.01305,
        "n-hexane": 0.0085,
        "n-heptane": 0.0077,
        "i-pentane": 0.00627,
        "nitrogen": 0.00493,
    }
    suc = ccp.State(p=Q_(1589149.1, "Pa"), T=Q_(306.28, "K"), fluid=fluid)
    with pytest.raises(ValueError, match="phase envelope"):
        _check_single_phase_suction(suc)

    with pytest.warns(PhaseWarning, match="Cluster 0 suction"):
        _allow_wet_cluster_suction(suc, 0)
    _check_single_phase_suction(suc)
    # The permission travels with the state to the conversion workers.
    _check_single_phase_suction(pickle.loads(pickle.dumps(suc)))
    _check_single_phase_suction(copy.copy(suc))
