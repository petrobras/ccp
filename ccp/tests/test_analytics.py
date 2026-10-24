"""Tests of ccp.analytics: trends, reconciliation and the fleet model."""

import warnings

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose

from ccp.analytics import (
    Reconciliation,
    analyse_trends,
    change_points,
    theil_sen,
)
from ccp.analytics.fleet import Fleet, pymc_available, simulate_fleet
from ccp.analytics.trends import robust_sigma


def test_change_points_find_steps():
    rng = np.random.default_rng(0)
    found = 0
    for _ in range(50):
        y = np.r_[np.zeros(60), 1.5 * np.ones(40), 0.2 * np.ones(50)]
        y = y + rng.normal(0, 0.5, len(y))
        cps = change_points(y)
        found += any(abs(c - 60) <= 1 for c in cps) and any(
            abs(c - 100) <= 1 for c in cps
        )
    assert found >= 45


def test_change_points_none_on_noise():
    rng = np.random.default_rng(1)
    false_alarms = sum(bool(change_points(rng.normal(0, 1, 200))) for _ in range(100))
    assert false_alarms <= 3


def test_theil_sen_interval_covers_slope():
    rng = np.random.default_rng(2)
    t = np.arange(100.0)
    y = 0.05 * t + rng.normal(0, 1, 100)
    y[10] += 30  # an outlier does not move the slope
    slope, intercept, low, high = theil_sen(t, y)
    assert low < 0.05 < high
    assert_allclose(slope, 0.05, atol=0.01)


def _kpi_frame(rng, days=200, wash_day=120):
    """Hourly evaluation results with a drift of -0.5 points per 1000 h and a wash."""
    index = pd.date_range("2025-01-01", periods=days * 24, freq="1h")
    hours = np.arange(len(index), dtype=float)
    delta_eff = -0.5 * hours / 1000 + rng.normal(0, 0.3, len(index))
    wash = hours >= wash_day * 24
    delta_eff[wash] += 2.0 + 0.5 * wash_day * 24 / 1000  # back to the start value
    return pd.DataFrame(
        {
            "delta_eff": delta_eff,
            "delta_head": rng.normal(0, 0.3, len(index)),
            "cluster": 0,
            "valid": True,
        },
        index=index,
    )


def test_analyse_trends_finds_wash_and_slope():
    rng = np.random.default_rng(3)
    df = _kpi_frame(rng)
    report = analyse_trends(df, kpis=["delta_eff", "delta_head"])
    eff = report["delta_eff"]
    assert len(eff.change_points) == 1
    change = eff.change_points[0]
    assert abs((change["time"] - pd.Timestamp("2025-05-01")).days) <= 1
    assert change["kind"] == "recovery"
    assert eff.slope_low < -0.5 < eff.slope_high
    # from about +2 at the end, -2 is crossed in about (2 + 2) / 0.5 * 1000 h
    assert 4000 < eff.time_to_threshold < 13000
    assert report["delta_head"].change_points == []
    frame = report.to_frame()
    assert set(frame.index) == {"delta_eff", "delta_head"}
    assert (
        report.to_dict()["trends"]["delta_eff"]["change_points"][0]["kind"]
        == "recovery"
    )
    report.plot("delta_eff")


def test_time_to_threshold_already_crossed():
    # the efficiency is already below its -2 threshold: the threshold is
    # reached (0 h), whether it keeps degrading or recovers slowly
    rng = np.random.default_rng(0)
    index = pd.date_range("2025-01-01", periods=60 * 24, freq="1h")
    for drift in (-1.0, 0.5):
        y = -3.0 + drift * np.linspace(0, 1, len(index))
        df = pd.DataFrame({"delta_eff": y + rng.normal(0, 0.05, len(index))}, index)
        eff = analyse_trends(df, kpis=["delta_eff"])["delta_eff"]
        assert eff.current < -2
        assert eff.time_to_threshold == 0.0
        assert eff.time_to_threshold_low == eff.time_to_threshold_high == 0.0
    # a lower-is-better KPI above its threshold, and one without direction
    df = pd.DataFrame({"delta_Td": 3 + rng.normal(0, 0.05, len(index))}, index)
    report = analyse_trends(
        df.assign(delta_eff=0.0, delta_power_balance=df["delta_Td"]),
        kpis=["delta_Td", "delta_power_balance"],
        thresholds={"delta_Td": 2.0, "delta_power_balance": 2.0},
    )
    assert report["delta_Td"].time_to_threshold == 0.0
    assert report["delta_power_balance"].time_to_threshold == 0.0


def test_change_points_on_quantised_series():
    # most differences are zero (MAD 0): the noise scale is the quantisation
    # error, not the standard deviation of the series, which the step inflates
    y = np.r_[np.zeros(30), -np.ones(30)]
    assert_allclose(robust_sigma(y), 1 / np.sqrt(12))
    assert change_points(y) == [30]
    assert robust_sigma(np.ones(20)) == 0.0
    assert change_points(np.ones(20)) == []


def test_analyse_trends_baseline_per_cluster():
    rng = np.random.default_rng(4)
    df = _kpi_frame(rng, days=60, wash_day=1000)
    # a second operating region where the curve is 5 points off
    df["cluster"] = (np.arange(len(df)) // 24) % 2
    df.loc[df["cluster"] == 1, "delta_eff"] += 5
    plain = analyse_trends(df, kpis=["delta_eff"])
    corrected = analyse_trends(df, kpis=["delta_eff"], baseline_days=7)
    assert corrected["delta_eff"].sigma < plain["delta_eff"].sigma / 3
    assert set(corrected["delta_eff"].baseline) == {0, 1}


def _reconciliation_data(n=3000, seed=1):
    rng = np.random.default_rng(seed)
    index = pd.date_range("2025-01-01", periods=n, freq="1h")
    p_true = 10 + np.cumsum(rng.normal(0, 0.002, n))
    flow_a = 50 + rng.normal(0, 1, n)
    flow_b = 40 + rng.normal(0, 1, n)
    df = pd.DataFrame(
        {
            "ps_A": p_true + rng.normal(0, 0.02, n),
            "ps_B": p_true + rng.normal(0, 0.02, n),
            "ps_C": p_true + rng.normal(0, 0.02, n),
            "flow_A": flow_a * (1 + rng.normal(0, 0.01, n)),
            "flow_B": flow_b * (1 + rng.normal(0, 0.01, n)),
            "flow_H": (flow_a + flow_b) * (1 + rng.normal(0, 0.01, n)),
        },
        index=index,
    )
    return df, flow_b


SIGMAS = {
    "ps_A": 0.02,
    "ps_B": 0.02,
    "ps_C": 0.02,
    "flow_A": "1%",
    "flow_B": "1%",
    "flow_H": "1%",
}


def _reconciliation(**kwargs):
    return Reconciliation(
        SIGMAS,
        redundancy={"ps": ["ps_A", "ps_B", "ps_C"]},
        balances=[{"flow_H": 1, "flow_A": -1, "flow_B": -1}],
        **kwargs,
    )


def test_reconciliation_global_test_is_calibrated():
    df, _ = _reconciliation_data()
    result = _reconciliation(max_eliminations=0).reconcile(df)
    assert_allclose(result.global_test["dof"].median(), 3.0)
    rejected = (result.global_test["p_value"] < 0.05).mean()
    assert 0.03 < rejected < 0.07


def test_reconciliation_bias_gross_error_and_missing_tag():
    df, flow_b = _reconciliation_data()
    df["ps_B"] += 0.08  # persistent bias of four standard deviations
    df.iloc[100, df.columns.get_loc("ps_C")] += 0.5  # one gross error
    df.iloc[200:210, df.columns.get_loc("flow_B")] = np.nan
    result = _reconciliation().reconcile(df)
    assert result.gross_errors.iloc[100]["ps_C"]
    assert_allclose(result.adjustments["ps_B"].median(), 0.08, atol=0.01)
    assert_allclose(result.biases["ps_B"].iloc[-1], 0.08, atol=0.015)
    # the missing flow is recovered from the balance
    assert_allclose(result.variables["flow_B"].iloc[205], flow_b[205], rtol=0.05)
    assert np.isnan(result.adjustments["flow_B"].iloc[205])
    summary = result.summary()
    assert summary.loc["ps_B", "gross_error_rate"] > 0.5


def test_reconciliation_zero_reading_with_relative_sigma():
    # a dead transmitter reads 0: with a relative sigma its weight would be
    # infinite; it is treated as missing and the other rows are unaffected
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame(
        {
            "ps_A": 10 + rng.normal(0, 0.02, n),
            "ps_B": 10 + rng.normal(0, 0.02, n),
            "Ts_A": 300 + rng.normal(0, 0.3, n),
            "Ts_B": 300 + rng.normal(0, 0.3, n),
        }
    )
    df.iloc[50, 0] = 0.0
    rec = Reconciliation(
        {"ps_A": "0.25%", "ps_B": "0.25%", "Ts_A": 0.3, "Ts_B": 0.3},
        redundancy={"ps": ["ps_A", "ps_B"], "Ts": ["Ts_A", "Ts_B"]},
    )
    result = rec.reconcile(df)
    assert result.variables.notna().all().all()
    assert_allclose(result.variables["ps"].iloc[50], df["ps_B"].iloc[50])
    assert np.isnan(result.adjustments["ps_A"].iloc[50])


def test_reconciliation_tied_tests_remove_nothing():
    # two tags of one variable: their measurement tests are equal, so the
    # biased one cannot be located and neither is removed
    rng = np.random.default_rng(1)
    n = 200
    rec = Reconciliation(
        {"ps_A": 0.01, "ps_B": 0.01}, redundancy={"ps": ["ps_A", "ps_B"]}
    )
    df = pd.DataFrame(
        {"ps_A": 10.08 + rng.normal(0, 0.01, n), "ps_B": 10 + rng.normal(0, 0.01, n)}
    )
    for columns in (["ps_A", "ps_B"], ["ps_B", "ps_A"]):
        result = rec.reconcile(df[columns])
        assert not result.gross_errors.any().any()
        assert_allclose(result.variables["ps"].median(), 10.04, atol=0.005)
        assert_allclose(result.adjustments["ps_A"].median(), 0.04, atol=0.005)
    # one balance h = A + B: the three tests are equal as well
    rec = Reconciliation(
        {"h": 1.0, "A": 1.0, "B": 1.0}, balances=[{"h": 1, "A": -1, "B": -1}]
    )
    result = rec.reconcile(pd.DataFrame({"h": [100.0], "A": [40.0], "B": [50.0]}))
    assert not result.gross_errors.any().any()
    assert result.global_test["p_value"].iloc[0] < 1e-6
    assert_allclose(result.variables.iloc[0], [100 - 10 / 3, 40 + 10 / 3, 50 + 10 / 3])


def test_reconciliation_unobservable_variables_are_nan():
    rec = Reconciliation(
        {"h": 1.0, "A": 1.0, "B": 1.0}, balances=[{"h": 1, "A": -1, "B": -1}]
    )
    df = pd.DataFrame({"h": [100.0, 100.0], "A": [np.nan, 40.0], "B": [np.nan] * 2})
    variables = rec.reconcile(df).variables
    assert_allclose(variables["h"], 100.0)
    assert np.isnan(variables["A"].iloc[0]) and np.isnan(variables["B"].iloc[0])
    # with A measured, B follows from the balance
    assert_allclose(variables[["A", "B"]].iloc[1], [40.0, 60.0])


def test_reconciliation_rejects_unknown_tags():
    with pytest.raises(ValueError):
        Reconciliation({"a": 1.0}, redundancy={"x": ["a", "b"]})
    with pytest.raises(ValueError):
        Reconciliation({"a": 1.0}, balances=[{"a": 1, "z": -1}])


def test_fleet_setup_from_observations():
    field, shop, truth = simulate_fleet(n_units=3, n_sites=2, days=120, seed=5)
    fleet = Fleet.from_observations(field, shop, rows_per_bin=5)
    assert set(fleet.units) == {"U1", "U2", "U3"}
    assert fleet.freq == "1D"  # 120 days fit in max_bins=120 daily periods
    assert Fleet.from_observations(field, shop, max_bins=40).freq == "7D"
    assert fleet.field.groupby(["unit", "bin"]).size().max() <= 5
    assert fleet.has_power
    with pytest.raises(RuntimeError):
        fleet.summary()


def _fake_posterior(fleet, chains=2, draws=200, seed=0):
    """Independent normal draws with the shapes of the fleet posterior."""
    import xarray as xr

    rng = np.random.default_rng(seed)
    n_u, n_t = len(fleet.units), fleet.n_bins
    shapes = {
        "mu": (3,),
        "tau_unit": (3,),
        "theta": (n_u, 3),
        "tau_install": (2,),
        "field_offset": (n_u, 2),
        "mu_rate": (2,),
        "tau_rate": (2,),
        "rate": (n_u, 2),
        "sigma_walk": (2,),
        "sigma_period": (2,),
        "health": (n_u, 2, n_t),
        "bias_T": (n_u,),
        "bias_pr": (n_u,),
        "bias_flow": (n_u,),
        "bias_driver": (n_u,),
        "tau_site": (2,),
        "sigma": (n_u, 3),
    }
    data = {}
    for name, shape in shapes.items():
        values = 0.01 * rng.normal(size=(chains, draws, *shape))
        if name.startswith(("tau", "sigma")):
            values = np.abs(values)
        if name == "health":
            values[..., 0] = 0.0  # anchored levels are constant
        dims = ["chain", "draw"] + [f"{name}_{k}" for k in range(len(shape))]
        data[name] = (dims, values)
    return xr.Dataset(data)


def test_fleet_diagnostics_rank_rhat_and_warning():
    field, shop, _ = simulate_fleet(n_units=3, n_sites=2, days=30, seed=5)
    fleet = Fleet.from_observations(field, shop)
    fleet._posterior = _fake_posterior(fleet, chains=4, draws=1000)
    fleet._divergences = 0
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        diagnostics = fleet.diagnostics()
    assert diagnostics["max_rhat"] < 1.01
    table = diagnostics["table"]
    # the health levels and the period scale are checked, the anchored
    # (constant) levels are left out
    assert any(p.startswith("health[") for p in table.index)
    assert "sigma_period[0]" in table.index
    assert table["rhat"].notna().all()
    # one chain of the health stuck elsewhere: R-hat flags it, with a warning
    posterior = fleet._posterior.copy(deep=True)
    posterior["health"][1, :, 0, 1, 3] += 0.05
    fleet._posterior = posterior
    with pytest.warns(RuntimeWarning, match="R-hat"):
        diagnostics = fleet.diagnostics()
    assert diagnostics["max_rhat"] > 1.5
    fleet._divergences = 3
    with pytest.warns(RuntimeWarning, match="3 divergent"):
        fleet.diagnostics()


def test_split_rhat_matches_rank_normalised_definition():
    from ccp.analytics.fleet import _ess, _split_rhat

    rng = np.random.default_rng(0)
    x = rng.normal(size=(4, 500))
    assert_allclose(_split_rhat(x), 1.0, atol=0.005)
    assert 1500 < _ess(x) < 2500
    # a chain with twice the scale: the bulk R-hat misses it, the folded
    # (tail) R-hat does not; reference value from arviz 1.3 (az.rhat)
    x[3] *= 2
    assert_allclose(_split_rhat(x), 1.0811, atol=1e-4)
    assert np.isnan(_split_rhat(np.ones((2, 100))))


def test_fleet_unit_without_field_rows():
    field, shop, _ = simulate_fleet(n_units=3, n_sites=2, days=30, seed=5)
    # every field row of U3 is near choke and left out
    field.loc[field["unit"] == "U3", "head_slope"] = -3.0
    with pytest.warns(RuntimeWarning, match="U3"):
        fleet = Fleet.from_observations(field, shop)
    assert "U3" in fleet.units
    fleet._posterior = _fake_posterior(fleet)
    fleet._divergences = 0
    summary = fleet.summary()
    assert summary.loc["U3", "field_rows"] == 0
    assert summary.loc["U1", "field_rows"] > 0
    assert np.isnan(summary.loc["U3", "current_eff"])
    assert np.isnan(summary.loc["U3", "p_worst_eff"])
    assert np.isfinite(summary.loc["U3", "asbuilt_eff"])
    assert_allclose(summary["p_worst_eff"].sum(), 1.0)
    ranking = fleet.ranking()
    assert ranking.loc["U3"].isna().all()
    assert_allclose(ranking.loc[["U1", "U2"]].sum(axis=1), 1.0)
    assert fleet.time_to_threshold().loc["U3"].isna().all()
    assert not (fleet.events()["unit"] == "U3").any()


def test_fleet_time_to_threshold_quantiles_not_nan():
    field, shop, _ = simulate_fleet(n_units=3, n_sites=2, days=30, seed=5)
    fleet = Fleet.from_observations(field, shop)
    fleet._posterior = _fake_posterior(fleet)
    fleet._divergences = 0
    # about half the draws improve and never reach the threshold
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ttt = fleet.time_to_threshold(threshold=-0.05)
    assert not ttt.isna().any().any()
    assert np.isinf(ttt["q95_h"]).all()
    assert (ttt["q05_h"] < np.inf).all()


def test_fleet_power_rows_and_save_load(tmp_path):
    import types

    rng = np.random.default_rng(0)
    n = 6
    df = pd.DataFrame(
        {
            "delta_eff": 0.0,
            "valid": True,
            "head": 50e3 * (1 + rng.normal(0, 0.01, n)),
            "expected_head": 50e3,
            "eff": 0.8 + rng.normal(0, 0.005, n),
            "expected_eff": 0.8,
            "head_slope": -0.5,
            "eff_slope": -0.1,
            "ps": 4e5,
            "pd": 1.2e6,
            "Ts": 300.0,
            "Td": 420.0,
            "power": 1.0e6,
            "power_shaft": 1.02e6,
            "power_coupling": 1.03e6,
        },
        index=pd.date_range("2025-01-01", periods=n, freq="1h"),
    )
    df.iloc[0, df.columns.get_loc("power_coupling")] = 0.0  # dead transmitter
    df.iloc[1, df.columns.get_loc("power_coupling")] = -5.0
    from ccp.analytics.fleet import field_observations

    obs = field_observations(types.SimpleNamespace(df=df, data_units={}))
    assert len(obs) == n
    assert obs["r_power"].iloc[:2].isna().all() and obs["w"].iloc[:2].isna().all()
    assert np.isfinite(obs["r_power"].iloc[2:]).all()
    # max_head_slope survives a save and load
    field, shop, _ = simulate_fleet(n_units=2, n_sites=1, days=10, seed=1)
    fleet = Fleet.from_observations(field, shop, max_head_slope=1.2)
    fleet.save(tmp_path / "fleet.zip")
    loaded = Fleet.load(tmp_path / "fleet.zip")
    assert loaded.max_head_slope == 1.2
    loaded.save(tmp_path / "again.zip")
    assert Fleet.load(tmp_path / "again.zip").max_head_slope == 1.2


@pytest.mark.slow
@pytest.mark.skipif(not pymc_available(), reason="needs the bayes extra (PyMC)")
def test_fleet_recovers_simulated_truth(tmp_path):
    field, shop, truth = simulate_fleet(
        n_units=3, n_sites=2, days=180, wash_day=100, seed=7
    )
    # weekly periods: the 2-day default mixes worse at a test's draw count
    fleet = Fleet.from_observations(field, shop, freq="7D")
    with warnings.catch_warnings():
        # this fit does not reach R-hat 1.01 (SPEC F07 decision D22)
        warnings.simplefilter("ignore", RuntimeWarning)
        fleet.fit(draws=1000, tune=1500, chains=2, random_seed=3)
        diagnostics = fleet.diagnostics(warn=False)
    # rank-normalised R-hat over the parameters and the health levels;
    # measured 1.037 (tau_site) and 10 divergences of 2000 draws
    assert diagnostics["max_rhat"] < 1.06
    assert diagnostics["divergences"] < 40
    summary = fleet.summary()
    for i, unit in enumerate(truth["units"]):
        row = summary.loc[unit]
        for j, name in enumerate(["flow", "head", "eff"]):
            value = truth["theta"][i, j] * 100
            assert (
                row[f"asbuilt_{name}_low"] - 0.3
                < value
                < row[f"asbuilt_{name}_high"] + 0.3
            )
    events = fleet.events()
    wash = events[(events["unit"] == "U1") & (events["field"] == "eff")]
    assert len(wash) == 1 and wash["step"].iloc[0] > 1
    # saved and loaded fleets give the same results
    path = tmp_path / "fleet.zip"
    fleet.save(path)
    loaded = Fleet.load(path)
    pd.testing.assert_frame_equal(loaded.summary(), summary)
    results = fleet.to_dict()
    assert set(results["summary"]["index"]) == set(truth["units"])
    fleet.plot_units()
    fleet.plot_health()
