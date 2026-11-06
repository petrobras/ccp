from pathlib import Path
from tempfile import tempdir
from types import SimpleNamespace

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


def test_wet_cluster_suction_warns_naming_the_cluster():
    """A cluster centre at the dew line is converted with a PhaseWarning.

    Composition and conditions of the example_evaluation_pi.ccp cluster that
    sits at vapour quality 0.99.
    """
    import copy
    import pickle
    import warnings

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
    with pytest.warns(PhaseWarning, match="Cluster 0 suction"):
        _allow_wet_cluster_suction(suc, 0)
    # The mark travels with the state, so the conversion workers stay silent.
    with warnings.catch_warnings():
        warnings.simplefilter("error", PhaseWarning)
        _check_single_phase_suction(suc)
        _check_single_phase_suction(pickle.loads(pickle.dumps(suc)))
        _check_single_phase_suction(copy.copy(suc))


@pytest.mark.filterwarnings("ignore::ccp.state.IdealGasWarning")
def test_evaluation_ideal_gas(tmp_path):
    suc = ccp.State(p=Q_(4, "bar"), T=Q_(40, "degC"), fluid=fluid_a, EOS="ideal")
    imp = ccp.Impeller.load_from_engauge_csv(
        suc=suc,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
        number_of_points=4,
    )
    df = pd.read_parquet(data_path / "data.parquet")
    results = []
    for parallel in (True, False):
        ccp.config.PARALLEL = parallel
        results.append(
            ccp.Evaluation(
                data=df,
                operation_fluid=operation_fluid,
                data_units=data_units,
                impellers=[imp],
                n_clusters=2,
            )
        )
    pool, serial = results
    assert {p.suc.EOS for i in pool.impellers_new for p in i.points} == {"ideal"}
    assert {p.disch.EOS for i in pool.impellers_new for p in i.points} == {"ideal"}
    for column in ("eff", "head", "delta_eff", "expected_p_disch"):
        assert_allclose(pool.df[column], serial.df[column], rtol=1e-12)
    path = tmp_path / "evaluation.ccp_eval"
    pool.save(path)
    loaded = ccp.Evaluation.load(path)
    assert {p.suc.EOS for i in loaded.impellers_new for p in i.points} == {"ideal"}


def _ideal_gas_v(p, T, fluid):
    ref = ccp.State(p=Q_(1, "bar"), T=Q_(300, "K"), fluid=fluid, EOS="ideal")
    R = (ref.gas_constant() / ref.molar_mass()).to("J/kg/K").m
    return R * Q_(T, "degC").to("K").m / p.to("Pa").m


def _ideal_gas_impeller():
    suc = ccp.State(p=Q_(4, "bar"), T=Q_(40, "degC"), fluid=fluid_a, EOS="ideal")
    return ccp.Impeller.load_from_engauge_csv(
        suc=suc,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
        number_of_points=4,
    )


@pytest.mark.filterwarnings("ignore::ccp.state.IdealGasWarning")
@pytest.mark.parametrize(
    "data_file,tap",
    [
        ("data.parquet", None),
        ("data_delta_p.parquet", "p_downstream"),
        ("data_delta_p.parquet", "p_upstream"),
    ],
)
def test_evaluation_ideal_gas_values(data_file, tap):
    imp = _ideal_gas_impeller()
    df = pd.read_parquet(data_path / data_file)[:100]
    if tap is None:
        units, kwargs = data_units, {}
    else:
        df = df.rename(columns={"p_downstream": tap})
        units = {
            k.replace("p_downstream", tap): v for k, v in delta_p_data_units.items()
        }
        kwargs = dict(D=Q_(0.590550, "m"), d=Q_(0.366130, "m"), tappings="flange")
    res = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units=units,
        impellers=[imp],
        n_clusters=2,
        **kwargs,
    ).df
    if tap is None:
        p = Q_(res["ps"].array, "bar")
    elif tap == "p_upstream":
        p = Q_(res["p_upstream"].array, "bar")
    else:
        # FlowOrifice moves a downstream state to p + delta_p
        p = Q_(res["p_downstream"].array, "bar") + Q_(res["delta_p"].array, "mmH2O")
    v_s = _ideal_gas_v(p, res["Ts"].array, operation_fluid)
    assert_allclose(res["v_s"], v_s, rtol=1e-9)
    row = res.iloc[0]
    point = ccp.Point(
        suc=ccp.State(
            p=Q_(row.ps, "bar"),
            T=Q_(row.Ts, "degC"),
            fluid=operation_fluid,
            EOS="ideal",
        ),
        disch=ccp.State(
            p=Q_(row.pd, "bar"),
            T=Q_(row.Td, "degC"),
            fluid=operation_fluid,
            EOS="ideal",
        ),
        flow_v=Q_(row.flow_v, "m³/s"),
        speed=Q_(row.speed, "RPM"),
    )
    assert_allclose(row["eff"], point.eff.m, rtol=1e-9)
    assert_allclose(row["head"], point.head.m, rtol=1e-9)


@pytest.mark.filterwarnings("ignore::ccp.state.IdealGasWarning")
def test_evaluation_refuses_mixed_gas_models():
    imp = _ideal_gas_impeller()
    real = ccp.Impeller([copy_point_as_real(p) for p in imp.points])
    with pytest.raises(ValueError, match="different gas models"):
        ccp.Evaluation(
            data=pd.read_parquet(data_path / "data.parquet")[:10],
            operation_fluid=operation_fluid,
            data_units=data_units,
            impellers=[imp, real],
            n_clusters=2,
        )


def copy_point_as_real(point):
    suc = ccp.State(p=point.suc.p(), T=point.suc.T(), fluid=point.suc.fluid, EOS="HEOS")
    return ccp.Point(
        suc=suc,
        head=point.head,
        eff=point.eff,
        flow_v=point.flow_v,
        speed=point.speed,
        b=point.b,
        D=point.D,
    )


def test_evaluation_gas_model_of_operating_data():
    def evaluation(impellers=None, impellers_new=None):
        return SimpleNamespace(impellers=impellers, impellers_new=impellers_new)

    def impeller(EOS):
        fluid = {"Methane": 1.0}
        suc = ccp.State(p=1e5, T=300.0, fluid=fluid, EOS=EOS)
        return SimpleNamespace(points=[SimpleNamespace(suc=suc)])

    get_eos = ccp.Evaluation._EOS.fget
    # a real-gas impeller keeps the default model for the operating data
    ccp.config.EOS = "HEOS"
    assert get_eos(evaluation([impeller("PR")])) == "HEOS"
    # a loaded evaluation may only have the converted impellers
    with pytest.warns(ccp.state.IdealGasWarning):
        ideal = impeller("ideal:k=1.3")
    assert get_eos(evaluation([ideal])) == "ideal:k=1.3"
    assert get_eos(evaluation(None, [ideal])) == "ideal:k=1.3"
