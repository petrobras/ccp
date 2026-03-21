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

    assert_allclose(evaluation.df["delta_eff"].mean(), 10.985054, rtol=1e-2)

    # save evaluation in temporary file
    file = Path(tempdir) / "evaluation.ccp_eval"
    evaluation.save(file)

    loaded_evaluation = ccp.Evaluation.load(file)
    assert_allclose(loaded_evaluation.df["delta_eff"].mean(), 10.985054, rtol=1e-2)
    assert loaded_evaluation.impellers_new[0] == evaluation.impellers_new[0]


def test_evaluation_fluid_columns():
    data_path = Path(ccp.__file__).parent / "tests/data"
    df = pd.read_parquet(data_path / "data.parquet")

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
    suc_a = ccp.State(p=Q_(4, "bar"), T=Q_(40, "degC"), fluid=fluid_a)
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

    for comp, frac in operation_fluid.items():
        df[f"fluid_{comp}"] = frac

    evaluation = ccp.Evaluation(
        data=df,
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

    assert_allclose(evaluation.df["delta_eff"].mean(), 10.985054, rtol=1e-2)


def test_evaluation_fluid_columns_ppm():
    data_path = Path(ccp.__file__).parent / "tests/data"
    df = pd.read_parquet(data_path / "data.parquet")

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
    suc_a = ccp.State(p=Q_(4, "bar"), T=Q_(40, "degC"), fluid=fluid_a)
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
        "n-pentane": 0.03 * 1e6,  # check with ppm
        "i-pentane": 0.02,
        "n2": 0.25,
        "h2s": 0.06,
        "co2": 51.55,
    }

    for comp, frac in operation_fluid.items():
        df[f"fluid_{comp}"] = frac

    evaluation = ccp.Evaluation(
        data=df,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "flow_v": "m³/s",
            "speed": "RPM",
            "fluid_n-pentane": "ppm",
        },
        impellers=[imp_a],
        n_clusters=2,
    )

    assert_allclose(evaluation.df["delta_eff"].mean(), 10.985054, rtol=1e-2)


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
    assert_allclose(df_results["delta_eff"].mean(), 10.839487, rtol=1e-2)


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

    assert_allclose(evaluation.df["delta_eff"].mean(), 10.934482, rtol=1e-2)


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
    assert_allclose(df_results["delta_eff"].mean(), 10.934482, rtol=1e-2)


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
    assert_allclose(df_results["delta_eff"].mean(), -0.147423, rtol=1e-2)

    # remove invalid values
    df_results = df_results[df_results.valid]
    assert_allclose(df_results["delta_eff"].mean(), 10.934482, rtol=1e-2)


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


def test_evaluation_orifice_fluid_columns():
    """Test evaluation with orifice flow measurement and per-row fluid composition.

    This test uses mock data extracted from the example_evaluation_pi.ccp file,
    trimmed to 30 rows. It mirrors the real app usage with:
    - Orifice plate flow calculation (delta_p, p_downstream)
    - Per-row fluid composition from fluid_* columns (no operation_fluid)
    - Multiple impeller design curves (4 cases)
    """
    data_path = Path(ccp.__file__).parent / "tests/data"
    df = pd.read_parquet(data_path / "data_eval_pi.parquet")

    # Load 4 design impellers from TOML files
    impellers = [
        ccp.Impeller.load(data_path / f"impeller_case_{case}.toml")
        for case in ["A", "B", "C", "D"]
    ]

    evaluation = ccp.Evaluation(
        data=df,
        data_units={
            "ps": "bar",
            "Ts": "degC",
            "pd": "bar",
            "Td": "degC",
            "speed": "rpm",
            "delta_p": "mmH2O",
            "p_downstream": "bar",
        },
        impellers=impellers,
        D=Q_(0.438, "m"),
        d=Q_(0.263, "m"),
        tappings="corner",
        n_clusters=4,
        temperature_fluctuation=3.0,
        pressure_fluctuation=3.0,
        speed_fluctuation=3.0,
    )

    # Verify we got 4 converted impellers (one per cluster)
    assert len(evaluation.impellers_new) == 4

    # Verify clusters have different suction conditions
    suc_pressures = [
        imp.points[0].suc.p().m for imp in evaluation.impellers_new
    ]
    assert len(set(round(p, 2) for p in suc_pressures)) > 1

    # Verify valid results exist and check performance metrics
    df_valid = evaluation.df[evaluation.df["valid"]]
    assert len(df_valid) == 9
    assert_allclose(df_valid["delta_eff"].mean(), 7.825291, rtol=1e-2)
    assert_allclose(df_valid["delta_head"].mean(), 21.859519, rtol=1e-2)
