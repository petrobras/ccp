import pandas as pd
import ccp
from numpy.testing import assert_allclose
from tempfile import tempdir
from pathlib import Path

Q_ = ccp.Q_


def test_evaluation():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data.parquet")
    # load lp-sec1-caso-a
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
    suc_a = ccp.State(
        p=Q_(4, "bar"),
        T=Q_(40, "degC"),
        fluid=fluid_a,
    )

    imp_a = ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
        number_of_points=4,
    )

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

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "flow_v": "m³/s",
            "speed": "RPM",
        },
        impellers=[imp_a],
        n_clusters=2,
    )

    assert_allclose(evaluation.df["delta_eff"].mean(), 0.112725, rtol=1e-2)

    # save evaluation in temporary file
    file = Path(tempdir) / "evaluation.ccp_eval"
    evaluation.save(file)

    loaded_evaluation = ccp.Evaluation.load(file)
    assert_allclose(loaded_evaluation.df["delta_eff"].mean(), 0.112725, rtol=1e-2)
    assert loaded_evaluation.impellers_new[0] == evaluation.impellers_new[0]


def test_evaluation_calculate_points():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data.parquet")
    # load lp-sec1-caso-a
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
    suc_a = ccp.State(
        p=Q_(4, "bar"),
        T=Q_(40, "degC"),
        fluid=fluid_a,
    )

    imp_a = ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
    )

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

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "flow_v": "m³/s",
            "speed": "RPM",
        },
        impellers=[imp_a],
        calculate_points=False,
        n_clusters=2,
    )

    df_results = evaluation.calculate_points(df)
    assert_allclose(df_results["delta_eff"].mean(), 0.111267, rtol=1e-2)


def test_evaluation_delta_p():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data_delta_p.parquet")
    # load lp-sec1-caso-a
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
    suc_a = ccp.State(
        p=Q_(4, "bar"),
        T=Q_(40, "degC"),
        fluid=fluid_a,
    )

    imp_a = ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
    )

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

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "delta_p": "mmH2O",
            "p_downstream": "bar",
            "speed": "RPM",
        },
        impellers=[imp_a],
        D=Q_(0.590550, "m"),
        d=Q_(0.366130, "m"),
        tappings="flange",
        n_clusters=2,
    )

    assert_allclose(evaluation.df["delta_eff"].mean(), 0.111338, rtol=1e-2)


def test_evaluation_calculate_points_delta_p():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data_delta_p.parquet")
    # load lp-sec1-caso-a
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
    suc_a = ccp.State(
        p=Q_(4, "bar"),
        T=Q_(40, "degC"),
        fluid=fluid_a,
    )

    imp_a = ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
    )

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

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "delta_p": "mmH2O",
            "p_downstream": "bar",
            "speed": "RPM",
        },
        impellers=[imp_a],
        D=Q_(0.590550, "m"),
        d=Q_(0.366130, "m"),
        tappings="flange",
        n_clusters=2,
        calculate_points=False,
    )

    df_results = evaluation.calculate_points(df)
    assert_allclose(df_results["delta_eff"].mean(), 0.111338, rtol=1e-2)


def test_evaluation_calculate_points_delta_p_flag():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data_delta_p.parquet")
    # load lp-sec1-caso-a
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
    suc_a = ccp.State(
        p=Q_(4, "bar"),
        T=Q_(40, "degC"),
        fluid=fluid_a,
    )

    imp_a = ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
    )

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

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "delta_p": "mmH2O",
            "p_downstream": "bar",
            "speed": "RPM",
        },
        impellers=[imp_a],
        D=Q_(0.590550, "m"),
        d=Q_(0.366130, "m"),
        tappings="flange",
        n_clusters=2,
        calculate_points=False,
    )

    df_results = evaluation.calculate_points(df, drop_invalid_values=False)
    # check mean with invalid values (-1)
    assert_allclose(df_results["delta_eff"].mean(), -0.9206450982953476, rtol=1e-2)

    # remove invalid values
    df_results = df_results[df_results.valid]
    assert_allclose(df_results["delta_eff"].mean(), 0.111338, rtol=1e-2)

def test_evaluation_calculate_points_delta_p_3_values():
    data_path = Path(ccp.__file__).parent / "tests/data"
    # load data.parquet
    df = pd.read_parquet(data_path / "data_delta_p.parquet")
    # load lp-sec1-caso-a
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
    suc_a = ccp.State(
        p=Q_(4, "bar"),
        T=Q_(40, "degC"),
        fluid=fluid_a,
    )

    imp_a = ccp.Impeller.load_from_engauge_csv(
        suc=suc_a,
        curve_name="eval-lp-sec1-caso-a",
        curve_path=data_path,
        flow_units="m³/h",
        head_units="kJ/kg",
    )

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

    evaluation = ccp.Evaluation(
        data=df,
        operation_fluid=operation_fluid,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "delta_p": "mmH2O",
            "p_downstream": "bar",
            "speed": "RPM",
        },
        impellers=[imp_a],
        D=Q_(0.590550, "m"),
        d=Q_(0.366130, "m"),
        tappings="flange",
        n_clusters=2,
        calculate_points=False,
    )

    df_results = evaluation.calculate_points(df[:3], drop_invalid_values=False)
    # check mean with invalid values (-1)
    assert_allclose(df_results["delta_eff"].mean(), -1, rtol=1e-2)
