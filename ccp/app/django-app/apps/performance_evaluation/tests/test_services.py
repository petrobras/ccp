"""Unit tests for the performance evaluation service layer."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from apps.performance_evaluation.services import figures, monitoring_state
from apps.performance_evaluation.services.run_evaluation import run_evaluation


class _FakeImpeller:
    """Minimal impeller stand-in exposing the plot methods used by figures."""

    def __init__(self) -> None:
        self.disch = self

    def _fig(self, title: str) -> go.Figure:
        return go.Figure(layout={"title": {"text": title}})

    def head_plot(self, **_: object) -> go.Figure:
        return self._fig("head")

    def power_plot(self, **_: object) -> go.Figure:
        return self._fig("power")

    def eff_plot(self, **_: object) -> go.Figure:
        return self._fig("eff")

    def p_plot(self, **_: object) -> go.Figure:
        return self._fig("p_disch")


class _FakeEvaluation:
    """Stand-in for ``ccp.Evaluation`` used by the service tests."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.impellers_new = [_FakeImpeller()]


def _sample_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=6, freq="D")
    return pd.DataFrame(
        {
            "flow_v": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
            "head": [1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0],
            "eff": [0.75, 0.76, 0.77, 0.78, 0.77, 0.76],
            "power": [100_000.0, 101_000.0, 102_000.0, 103_000.0, 104_000.0, 105_000.0],
            "p_disch": [10.0, 10.1, 10.2, 10.3, 10.4, 10.5],
            "speed": [9000.0, 9000.0, 9000.0, 9000.0, 9000.0, 9000.0],
            "delta_eff": [0.1, 0.2, -0.1, 0.0, 0.1, 0.2],
            "delta_head": [0.0, 0.1, 0.2, 0.0, 0.1, 0.2],
            "delta_power": [0.0, 0.1, 0.0, -0.1, 0.1, 0.0],
            "delta_p_disch": [0.0, 0.1, 0.0, 0.1, 0.0, 0.1],
            "cluster": [0, 0, 0, 0, 0, 0],
            "valid": [True, True, True, True, True, True],
        },
        index=idx,
    )


def test_build_trend_figures_returns_four_plots():
    evaluation = _FakeEvaluation(_sample_df())
    result = figures.build_trend_figures(evaluation)
    assert result["empty"] is False
    assert set(result["figures"]).issuperset(
        {"delta_eff", "delta_head", "delta_power", "delta_p_disch"}
    )
    for fig in result["figures"].values():
        assert isinstance(fig, go.Figure)
    assert "delta_eff" in result["regression"]


def test_build_trend_figures_empty_dataframe():
    result = figures.build_trend_figures(_FakeEvaluation(pd.DataFrame()))
    assert result["empty"] is True
    assert result["figures"] == {}


def test_build_performance_figures_produces_overlaid_curves():
    evaluation = _FakeEvaluation(_sample_df())
    result = figures.build_performance_figures(evaluation)
    assert result["empty"] is False
    assert set(result["figures"]) == {"head", "power", "eff", "p_disch"}
    head_fig = result["figures"]["head"]
    assert any("Historical" in (t.name or "") for t in head_fig.data)


def test_build_performance_figures_no_impellers():
    class _Empty:
        df = _sample_df()
        impellers_new: list[object] = []

    result = figures.build_performance_figures(_Empty())
    assert result["empty"] is True
    assert result["n_clusters"] == 0


def test_build_summary_stats_describes_delta_columns():
    df = figures.build_summary_stats(_FakeEvaluation(_sample_df()))
    assert df is not None
    assert {"delta_eff", "delta_head", "delta_power", "delta_p_disch"}.issubset(
        df.columns
    )


def test_monitoring_state_roundtrip():
    session = "unit-test"
    monitoring_state.clear(session)
    assert monitoring_state.is_active(session) is False

    monitoring_state.set_active(session, True)
    assert monitoring_state.is_active(session) is True

    df = _sample_df().head(3)
    monitoring_state.set_accumulated_results(session, df)
    restored = monitoring_state.get_accumulated_results(session)
    assert len(restored) == 3

    appended = monitoring_state.append_accumulated_results(
        session, _sample_df().tail(3), keep=5
    )
    assert len(appended) == 5

    snap = monitoring_state.snapshot(session)
    assert snap["active"] is True
    assert snap["accumulated_rows"] == 5

    monitoring_state.clear(session)
    assert monitoring_state.is_active(session) is False


def test_run_evaluation_with_prebuilt_evaluation():
    evaluation = _FakeEvaluation(_sample_df())
    result = run_evaluation(
        {"impellers": [_FakeImpeller()]},
        session_id="run-eval",
        evaluation=evaluation,
    )
    assert result["evaluation"] is evaluation
    assert result["error"] is None
    assert result["trend"]["empty"] is False
    assert result["performance"]["empty"] is False
    assert any(key.startswith("trend_") for key in result["figures"])
    assert any(key.startswith("perf_") for key in result["figures"])
    assert result["summary_df"] is not None
    assert result["ai_summary"] == ""
