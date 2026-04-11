"""Plotly figure builders for the performance evaluation results page.

Two public entry points:

* :func:`build_trend_figures` — time-series Delta-* scatter plots with
  linear regression + 95% confidence band.
* :func:`build_performance_figures` — head / power / efficiency /
  discharge-pressure curves with historical point overlays coloured by
  acquisition time.

Every figure uses the ``ccp`` Plotly template registered by Unit 1.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import stats

import ccp

Q_ = ccp.Q_

_TREND_PLOTS: dict[str, str] = {
    "Delta Efficiency (%)": "delta_eff",
    "Delta Head (%)": "delta_head",
    "Delta Power (%)": "delta_power",
    "Delta Discharge Pressure (%)": "delta_p_disch",
}

# Internal ccp units for evaluation output.
_FLOW_V_INTERNAL = "m³/s"
_HEAD_INTERNAL = "J/kg"
_POWER_INTERNAL = "W"
_PRESSURE_INTERNAL = "bar"


def _valid_points(df: pd.DataFrame) -> pd.DataFrame:
    """Return the subset of rows flagged ``valid`` with a positive head."""
    if df is None or df.empty:
        return pd.DataFrame()
    valid = df.get("valid", pd.Series(True, index=df.index)) == True  # noqa: E712
    head_ok = df.get("head", pd.Series(0, index=df.index)) > 0
    return df[valid & head_ok].copy()


def _trend_plot(y_data: pd.Series, title: str) -> tuple[go.Figure, dict | None]:
    """Build a single trend scatter + regression for ``y_data``."""
    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(
            x=y_data.index,
            y=y_data,
            mode="markers",
            marker=dict(color="#1f77b4", size=6),
            name=title,
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)

    regression: dict | None = None
    if len(y_data) >= 3:
        x_num = y_data.index.astype("int64").values / 1e9
        slope, intercept, r, p, _se = stats.linregress(x_num, y_data)
        y_fit = slope * x_num + intercept

        n = len(x_num)
        x_mean = x_num.mean()
        ss_x = ((x_num - x_mean) ** 2).sum()
        residuals = y_data - y_fit
        s_err = np.sqrt((residuals**2).sum() / max(n - 2, 1))
        t_val = stats.t.ppf(0.975, max(n - 2, 1))
        ci = t_val * s_err * np.sqrt(1 / n + (x_num - x_mean) ** 2 / max(ss_x, 1e-12))

        order = np.argsort(x_num)
        x_sorted = y_data.index[order]
        y_sorted = y_fit[order]
        ci_sorted = ci[order]

        fig.add_trace(
            go.Scatter(
                x=x_sorted,
                y=y_sorted,
                mode="lines",
                line=dict(color="orange", width=2),
                name="Trend",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([x_sorted, x_sorted[::-1]]),
                y=np.concatenate([y_sorted + ci_sorted, (y_sorted - ci_sorted)[::-1]]),
                fill="toself",
                fillcolor="rgba(255,165,0,0.15)",
                line=dict(width=0),
                name="95% CI",
                hoverinfo="skip",
            )
        )

        slope_per_month = slope * 30.44 * 24 * 3600
        regression = {
            "slope_per_month": float(slope_per_month),
            "r_squared": float(r**2),
            "p_value": float(p),
            "n_points": int(n),
        }
        fig.add_annotation(
            text=(f"slope: {slope_per_month:.3f} %/mo · R²={r**2:.3f} · p={p:.2e}"),
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.98,
            showarrow=False,
            font=dict(size=11),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#ccc",
            borderwidth=1,
        )

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=title,
        showlegend=False,
        template="ccp",
    )
    return fig, regression


def build_trend_figures(evaluation: Any) -> dict[str, Any]:
    """Return the 4 trend figures plus the regression metadata.

    Parameters
    ----------
    evaluation : ccp.Evaluation
        Evaluation whose ``df`` attribute carries the historical points.

    Returns
    -------
    dict
        ``{"figures": {col: go.Figure}, "regression": {col: info},
        "valid": df, "empty": bool}``.
    """
    df_results = getattr(evaluation, "df", None)
    df_valid = _valid_points(df_results)
    figures: dict[str, go.Figure] = {}
    regression: dict[str, dict] = {}
    if df_valid.empty:
        return {
            "figures": figures,
            "regression": regression,
            "valid": df_valid,
            "empty": True,
        }

    for title, col in _TREND_PLOTS.items():
        if col not in df_valid.columns:
            continue
        y_data = df_valid[col].dropna()
        if y_data.empty:
            continue
        fig, info = _trend_plot(y_data, title)
        figures[col] = fig
        if info is not None:
            regression[col] = info

    return {
        "figures": figures,
        "regression": regression,
        "valid": df_valid,
        "empty": False,
    }


def _colorbar(df_cluster: pd.DataFrame) -> dict[str, Any]:
    """Build the date-aware colorbar used on performance plots."""
    n_ticks = min(5, max(len(df_cluster), 1))
    tick_positions = [i / max(n_ticks - 1, 1) for i in range(n_ticks)]
    tick_indices = [int(p * max(len(df_cluster) - 1, 0)) for p in tick_positions]
    tick_labels = [df_cluster.index[i].strftime("%Y-%m-%d") for i in tick_indices]
    return dict(
        title=dict(text="Date", side="right"),
        tickvals=tick_positions,
        ticktext=tick_labels,
        orientation="h",
        yanchor="top",
        y=-0.2,
        xanchor="center",
        x=0.5,
        thickness=12,
        len=0.8,
    )


def _base_curves(
    impeller: Any,
    speed: Any,
    *,
    flow_v_units: str,
    head_units: str,
    power_units: str,
    p_units: str,
    similarity: bool,
) -> dict[str, go.Figure]:
    """Build the 4 base plots from the converted impeller."""
    head = impeller.head_plot(
        speed=speed,
        flow_v_units=flow_v_units,
        head_units=head_units,
        similarity=similarity,
    )
    power = impeller.power_plot(
        speed=speed,
        flow_v_units=flow_v_units,
        power_units=power_units,
        similarity=similarity,
    )
    eff = impeller.eff_plot(
        speed=speed,
        flow_v_units=flow_v_units,
        similarity=similarity,
    )
    disch = impeller.disch.p_plot(
        speed=speed,
        flow_v_units=flow_v_units,
        p_units=p_units,
        similarity=similarity,
    )
    for fig in (head, power, eff, disch):
        if fig is not None:
            fig.update_layout(template="ccp")
    return {"head": head, "power": power, "eff": eff, "p_disch": disch}


def build_performance_figures(
    evaluation: Any,
    *,
    cluster_idx: int = 0,
    show_similarity: bool = False,
    flow_units: str = "m³/s",
    head_units: str = "kJ/kg",
    power_units: str = "kW",
    pressure_units: str = "bar",
    speed_units: str = "rpm",
) -> dict[str, Any]:
    """Return the 4 performance curves with historical overlays.

    Parameters
    ----------
    evaluation : ccp.Evaluation
        Evaluation object providing ``impellers_new`` and ``df``.
    cluster_idx : int, optional
        Index into ``evaluation.impellers_new``.
    show_similarity : bool, optional
        Forwarded to the impeller plot methods.
    flow_units, head_units, power_units, pressure_units, speed_units : str
        Plot display units.

    Returns
    -------
    dict
        ``{"figures": {...}, "empty": bool, "cluster_idx": int,
        "n_clusters": int}``.
    """
    impellers = list(getattr(evaluation, "impellers_new", []) or [])
    n_clusters = len(impellers)
    if n_clusters == 0:
        return {"figures": {}, "empty": True, "cluster_idx": 0, "n_clusters": 0}

    cluster_idx = max(0, min(cluster_idx, n_clusters - 1))
    impeller = impellers[cluster_idx]

    df_valid = _valid_points(getattr(evaluation, "df", None))
    if "cluster" in df_valid.columns:
        df_cluster = df_valid[df_valid["cluster"] == cluster_idx].copy()
    else:
        df_cluster = df_valid

    if df_cluster.empty:
        return {
            "figures": {},
            "empty": True,
            "cluster_idx": cluster_idx,
            "n_clusters": n_clusters,
        }

    if "timescale" not in df_cluster.columns:
        idx_num = pd.to_numeric(df_cluster.index.astype("int64"))
        span = max(idx_num.max() - idx_num.min(), 1)
        df_cluster["timescale"] = (idx_num - idx_num.min()) / span

    hist_flow = df_cluster["flow_v"].apply(
        lambda v: Q_(v, _FLOW_V_INTERNAL).to(flow_units).m
    )
    hist_head = df_cluster["head"].apply(
        lambda v: Q_(v, _HEAD_INTERNAL).to(head_units).m
    )
    hist_eff = df_cluster["eff"]
    hist_power = df_cluster["power"].apply(
        lambda v: Q_(v, _POWER_INTERNAL).to(power_units).m
    )
    hist_p_disch = None
    if "p_disch" in df_cluster.columns:
        hist_p_disch = df_cluster["p_disch"].apply(
            lambda v: Q_(v, _PRESSURE_INTERNAL).to(pressure_units).m
        )

    median_speed = Q_(float(df_cluster["speed"].median()), speed_units)

    figures = _base_curves(
        impeller,
        median_speed,
        flow_v_units=flow_units,
        head_units=head_units,
        power_units=power_units,
        p_units=pressure_units,
        similarity=show_similarity,
    )

    colorbar_cfg = _colorbar(df_cluster)
    timescale = df_cluster["timescale"]

    overlays = {
        "head": hist_head,
        "power": hist_power,
        "eff": hist_eff,
        "p_disch": hist_p_disch,
    }
    for key, y_series in overlays.items():
        fig = figures.get(key)
        if fig is None or y_series is None:
            continue
        marker: dict[str, Any] = dict(
            color=timescale,
            colorscale="Viridis",
            size=6,
        )
        if key == "head":
            marker["colorbar"] = colorbar_cfg
        fig.add_trace(
            go.Scatter(
                x=hist_flow,
                y=y_series,
                mode="markers",
                marker=marker,
                name="Historical Points",
                showlegend=True,
            )
        )

    return {
        "figures": figures,
        "empty": False,
        "cluster_idx": cluster_idx,
        "n_clusters": n_clusters,
    }


def build_summary_stats(evaluation: Any) -> pd.DataFrame | None:
    """Return ``describe()`` of the delta columns for valid points."""
    df_results = getattr(evaluation, "df", None)
    if df_results is None or df_results.empty:
        return None
    delta_cols = [
        c
        for c in ("delta_eff", "delta_head", "delta_power", "delta_p_disch")
        if c in df_results.columns
    ]
    if not delta_cols:
        return None
    df_valid = _valid_points(df_results)
    if df_valid.empty:
        return None
    return df_valid[delta_cols].describe()


__all__ = [
    "build_performance_figures",
    "build_summary_stats",
    "build_trend_figures",
]
