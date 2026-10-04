"""Performance evaluation of plant data against the design curves.

Follows ``ccp/app/pages/4_performance_evaluation.py``. The heavy objects
(``ccp.Evaluation`` takes seconds to load) stay in the task worker: a run
produces the evaluation zip plus an *analysis* (figures, regressions,
statistics, the results table) that the web process renders without loading
the evaluation.
"""

import io
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy import stats

import ccp
from ccp import Q_

from . import gas, plant_data
from .units import InputError, flow_v_units

TREND_PLOTS = {
    "delta_eff": "Delta Efficiency (%)",
    "delta_head": "Delta Head (%)",
    "delta_power": "Delta Power (%)",
    "delta_p_disch": "Delta Discharge Pressure (%)",
}
TABLE_COLUMNS = [
    "flow_v",
    "flow_m",
    "eff",
    "expected_eff",
    "delta_eff",
    "head",
    "expected_head",
    "delta_head",
    "power",
    "expected_power",
    "delta_power",
    "p_disch",
    "expected_p_disch",
    "delta_p_disch",
    "valid",
    "cluster",
]
MONITOR_COLUMNS = [
    "eff",
    "expected_eff",
    "delta_eff",
    "head",
    "expected_head",
    "delta_head",
    "power",
    "expected_power",
    "delta_power",
    "valid",
]
PLOT_HEAD_UNITS = "kJ/kg"
PLOT_POWER_UNITS = "kW"
PLOT_P_UNITS = "bar"


def fig_json(fig):
    return json.loads(pio.to_json(fig, validate=False))


def fig_from_json(data):
    return pio.from_json(json.dumps(data), skip_invalid=True)


# --------------------------------------------------------------------------
# Building and running
# --------------------------------------------------------------------------


def operation_fluid(state):
    """Fixed operation fluid, or None when the composition comes from tags."""
    if state.get("fluid_source") == "Inform Component Tags":
        return None
    name = state.get("operation_fluid_gas")
    fluid = gas.composition(state, name)
    if not fluid:
        raise InputError({"operation_fluid_gas": f"Gas '{name}' has no composition"})
    return fluid


def orifice_geometry(state):
    if (state.get("flow_method") or "Direct") == "Direct":
        return {}
    errors = {}
    D = float(state.get("orifice_D") or 0)
    d = float(state.get("orifice_d") or 0)
    if D <= 0:
        errors["orifice_D"] = "Pipe diameter is required for the orifice flow method"
    if d <= 0:
        errors["orifice_d"] = "Orifice diameter is required for the orifice flow method"
    if errors:
        raise InputError(errors)
    return {
        "D": Q_(D, state.get("orifice_D_unit") or "m"),
        "d": Q_(d, state.get("orifice_d_unit") or "m"),
        "tappings": state.get("orifice_tappings") or "flange",
    }


def restore_orifice(evaluation, state):
    """``Evaluation.save`` drops D, d and tappings; put them back."""
    geometry = orifice_geometry(state)
    for key, value in geometry.items():
        setattr(evaluation, key, value)
    return evaluation


def evaluation_kwargs(state, tm, impellers, df, parallel=True):
    kwargs = {
        "data": df,
        "operation_fluid": operation_fluid(state),
        "data_units": plant_data.data_units(state, tm),
        "impellers": impellers,
        "n_clusters": len(impellers),
        "calculate_points": True,
        "parallel": parallel,
        "temperature_fluctuation": float(state.get("temperature_fluctuation") or 0.5),
        "pressure_fluctuation": float(state.get("pressure_fluctuation") or 2.0),
        "speed_fluctuation": float(state.get("speed_fluctuation") or 0.5),
    }
    kwargs.update(orifice_geometry(state))
    return kwargs


def evaluation_window(state, existing=None):
    """Start and end of the evaluation window from the state.

    Defaults: the saved evaluation's data range, else the last 30 days.
    """

    def parse(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    start, end = parse(state.get("eval_start")), parse(state.get("eval_end"))
    if start is None or end is None:
        if (
            existing is not None
            and getattr(existing, "data", None) is not None
            and not existing.data.empty
        ):
            d_start = (
                pd.Timestamp(existing.data.index.min())
                .tz_localize(None)
                .to_pydatetime()
            )
            d_end = (
                pd.Timestamp(existing.data.index.max())
                .tz_localize(None)
                .to_pydatetime()
            )
        else:
            d_end = datetime.now().replace(microsecond=0)
            d_start = d_end - timedelta(days=30)
        start = start or d_start
        end = end or d_end
    return start, end


def _align(ts, reference):
    ts, reference = pd.Timestamp(ts), pd.Timestamp(reference)
    if reference.tz is None and ts.tz is not None:
        return ts.tz_localize(None)
    if reference.tz is not None and ts.tz is None:
        return ts.tz_localize(reference.tz)
    if reference.tz is not None and ts.tz is not None:
        return ts.tz_convert(reference.tz)
    return ts


def run(state, impellers, existing, mode, fetch, parallel=True, progress=None):
    """Run or update an evaluation.

    Parameters
    ----------
    impellers : list of ccp.Impeller
        Loaded design cases, in case order.
    existing : ccp.Evaluation or None
    mode : {"run", "full_rebuild"}
        ``run`` appends new data to an existing evaluation when the window
        only extends its end, as the Streamlit page does.
    fetch : callable(start, end) -> DataFrame

    Returns
    -------
    evaluation : ccp.Evaluation or None
        None when nothing changed.
    message : str
    """
    if not impellers:
        raise InputError(
            {
                "impeller_case_A": (
                    "No design cases loaded. Load curves for at least one case."
                )
            }
        )

    def step(f, msg):
        if progress:
            progress(f, msg)

    start, end = evaluation_window(state, existing)
    tm_state = state
    can_incremental = (
        mode != "full_rebuild"
        and existing is not None
        and getattr(existing, "data", None) is not None
        and not existing.data.empty
    )
    if can_incremental:
        existing_start = pd.Timestamp(existing.data.index.min())
        existing_end = pd.Timestamp(existing.data.index.max())
        start_ts = _align(start, existing_start)
        end_ts = _align(end, existing_end)
        if start_ts <= existing_start and end_ts > existing_end:
            step(0.1, "Fetching new data...")
            df_new = fetch(existing_end.to_pydatetime(), end_ts.to_pydatetime())
            restore_orifice(existing, tm_state)
            step(0.3, "Running incremental evaluation...")
            added = existing.append_new_data(df_new, drop_invalid_values=False)
            return (
                existing,
                f"Incremental update completed! Added {len(added)} new rows.",
            )
        if end_ts <= existing_end:
            return None, "No new data in selected end time. Evaluation kept unchanged."
        return None, (
            "Date range changed (not append-only). Use Full Rebuild for this selection."
        )

    step(0.05, "Fetching data...")
    df_raw = fetch(start, end)
    if df_raw is None or len(df_raw) == 0:
        raise plant_data.PlantDataError("No data returned for the selected window.")
    tm = plant_data.tag_mappings(state)
    kwargs = evaluation_kwargs(state, tm, impellers, df_raw, parallel=parallel)
    step(0.15, f"Running full evaluation on {len(df_raw)} rows...")
    evaluation = ccp.Evaluation(**kwargs)
    return evaluation, "Full evaluation completed!"


def save(evaluation):
    with tempfile.TemporaryDirectory(prefix="ccp-eval-") as tmp:
        path = Path(tmp) / "evaluation.zip"
        evaluation.save(path)
        return path.read_bytes()


def load(content, state=None):
    with tempfile.TemporaryDirectory(prefix="ccp-eval-") as tmp:
        path = Path(tmp) / "evaluation.zip"
        path.write_bytes(content)
        evaluation = ccp.Evaluation.load(path)
    if state is not None:
        try:
            restore_orifice(evaluation, state)
        except InputError:
            pass
    return evaluation


# --------------------------------------------------------------------------
# Analysis (figures and tables produced after each run)
# --------------------------------------------------------------------------


def valid_rows(df):
    mask = pd.Series(True, index=df.index)
    if "valid" in df.columns:
        mask &= df["valid"] == True  # noqa: E712
    if "head" in df.columns:
        mask &= df["head"] > 0
    return df[mask].copy()


def trend_figure(y, title):
    fig = go.Figure()
    fig.add_trace(
        go.Scattergl(x=y.index, y=y, mode="markers", marker=dict(size=6), name=title)
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
    regression = None
    if len(y) >= 3:
        x = y.index.astype("int64").values / 1e9
        slope, intercept, r, p, _se = stats.linregress(x, y)
        fit = slope * x + intercept
        n = len(x)
        x_mean = x.mean()
        ss_x = ((x - x_mean) ** 2).sum()
        s_err = np.sqrt(((y - fit) ** 2).sum() / (n - 2))
        ci = (
            stats.t.ppf(0.975, n - 2)
            * s_err
            * np.sqrt(1 / n + (x - x_mean) ** 2 / ss_x)
        )
        order = np.argsort(x)
        xs, fs, cs = y.index[order], fit[order], np.asarray(ci)[order]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=fs,
                mode="lines",
                line=dict(color="orange", width=2),
                name="Trend",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([xs, xs[::-1]]),
                y=np.concatenate([fs + cs, (fs - cs)[::-1]]),
                fill="toself",
                fillcolor="rgba(255,165,0,0.15)",
                line=dict(width=0),
                name="95% CI",
                hoverinfo="skip",
            )
        )
        slope_month = slope * 30.44 * 24 * 3600
        regression = {
            "slope_per_month": float(slope_month),
            "r_squared": float(r**2),
            "p_value": float(p),
            "n_points": int(n),
        }
        fig.add_annotation(
            text=f"slope: {slope_month:.3f} %/mo · R²={r**2:.3f} · p={p:.2e}",
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
        title=title, xaxis_title="Time", yaxis_title=title, showlegend=False
    )
    return fig, regression


def plot_flow_units(state):
    unit = state.get("loaded_curves_flow_units") or "m³/s"
    return unit if unit in flow_v_units else "m³/h"


def base_curves(impeller, speed, flow_units, similarity):
    common = dict(speed=speed, flow_v_units=flow_units, similarity=similarity)
    return {
        "head": impeller.head_plot(head_units=PLOT_HEAD_UNITS, **common),
        "power": impeller.power_plot(power_units=PLOT_POWER_UNITS, **common),
        "eff": impeller.eff_plot(**common),
        "disch_p": impeller.disch.p_plot(p_units=PLOT_P_UNITS, **common),
    }


def performance_figures(evaluation, df_valid, state, cluster, similarity):
    """Converted curves of one cluster with the historical points coloured by time."""
    impeller = evaluation.impellers_new[cluster]
    df = (
        df_valid[df_valid["cluster"] == cluster].copy()
        if "cluster" in df_valid
        else df_valid
    )
    if df.empty:
        return None
    flow_units = plot_flow_units(state)
    idx = pd.to_numeric(df.index.astype("int64"))
    timescale = (idx - idx.min()) / max(idx.max() - idx.min(), 1)
    flow = df["flow_v"].apply(lambda v: Q_(v, "m³/s").to(flow_units).m)
    values = {
        "head": df["head"].apply(lambda v: Q_(v, "J/kg").to(PLOT_HEAD_UNITS).m),
        "power": df["power"].apply(lambda v: Q_(v, "W").to(PLOT_POWER_UNITS).m),
        "eff": df["eff"],
    }
    if "p_disch" in df:
        values["disch_p"] = df["p_disch"].apply(
            lambda v: Q_(v, "bar").to(PLOT_P_UNITS).m
        )
    speed = Q_(df["speed"].median(), state.get("speed_unit") or "rpm")
    n_ticks = min(5, len(df))
    positions = [i / max(n_ticks - 1, 1) for i in range(n_ticks)]
    labels = [
        df.index[int(p * max(len(df) - 1, 0))].strftime("%Y-%m-%d") for p in positions
    ]
    colorbar = dict(
        title=dict(text="Date", side="right"),
        tickvals=positions,
        ticktext=labels,
        orientation="h",
        yanchor="top",
        y=-0.2,
        xanchor="center",
        x=0.5,
        thickness=12,
        len=0.8,
    )
    figs = base_curves(impeller, speed, flow_units, similarity)
    for name, fig in figs.items():
        if name not in values:
            continue
        marker = dict(color=timescale, colorscale="Viridis", size=6)
        if name == "head":
            marker["colorbar"] = colorbar
        fig.add_trace(
            go.Scatter(
                x=flow,
                y=values[name],
                mode="markers",
                marker=marker,
                name="Historical Points",
            )
        )
    return figs


def analyse(evaluation, state, progress=None):
    """Everything the results tabs and the report need, JSON-serialisable.

    Returns
    -------
    analysis : dict
    table : pandas.DataFrame
        ``evaluation.df`` restricted to the display columns.
    """
    df = evaluation.df
    df_valid = valid_rows(df)
    trend = []
    regression = {}
    for col, title in TREND_PLOTS.items():
        if col not in df_valid.columns:
            continue
        y = df_valid[col].dropna()
        if y.empty:
            continue
        fig, reg = trend_figure(y, title)
        if reg is not None:
            regression[col] = reg
        trend.append({"key": col, "title": title, "figure": fig_json(fig)})

    perf = {}
    n_clusters = len(getattr(evaluation, "impellers_new", []) or [])
    for k in range(n_clusters):
        for similarity in (False, True):
            if progress:
                progress(
                    0.85 + 0.1 * k / max(n_clusters, 1),
                    f"Plotting converted curve {k + 1}...",
                )
            figs = performance_figures(evaluation, df_valid, state, k, similarity)
            if figs is None:
                continue
            perf[f"{k}:{int(similarity)}"] = {
                name: fig_json(f) for name, f in figs.items()
            }

    delta_cols = [c for c in TREND_PLOTS if c in df.columns]
    summary = None
    if delta_cols and not df_valid.empty:
        summary = df_valid[delta_cols].describe()
    table = df[[c for c in TABLE_COLUMNS if c in df.columns]]
    analysis = {
        "n_rows": int(len(df)),
        "n_valid": int(len(df_valid)),
        "start": str(df.index.min()) if len(df) else "",
        "end": str(df.index.max()) if len(df) else "",
        "n_clusters": n_clusters,
        "trend": trend,
        "regression": regression,
        "perf": perf,
        "summary": None
        if summary is None
        else json.loads(summary.to_json(orient="split")),
    }
    return analysis, table


def summary_frame(analysis):
    s = analysis.get("summary")
    if not s:
        return None
    return pd.DataFrame(s["data"], index=s["index"], columns=s["columns"])


def table_to_excel(df):
    buffer = io.BytesIO()
    frame = df.copy()
    if isinstance(frame.index, pd.DatetimeIndex) and frame.index.tz is not None:
        frame.index = frame.index.tz_localize(None)
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        frame.to_excel(writer, sheet_name="Sheet1")
    return buffer.getvalue()


def table_to_parquet(df):
    buffer = io.BytesIO()
    df.to_parquet(buffer)
    return buffer.getvalue()


def table_from_parquet(content):
    return pd.read_parquet(io.BytesIO(content))


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def report_html(analysis, state, session_name, ai_api_key=None):
    """Self-contained HTML report (``ccp/app/report.py``), optional AI text.

    Returns ``(html, ai_error)``.
    """
    from ccp.app.report import generate_html_report

    cluster = int(state.get("eval_cluster_idx") or 0)
    similarity = int(bool(state.get("eval_show_similarity")))
    trend_figs = [fig_from_json(t["figure"]) for t in analysis.get("trend", [])]
    perf = analysis.get("perf", {}).get(f"{cluster}:{similarity}") or next(
        iter(analysis.get("perf", {}).values()), {}
    )
    perf_figs = [
        fig_from_json(perf[k]) for k in ("head", "power", "eff", "disch_p") if k in perf
    ]
    summary = summary_frame(analysis)
    ai_text, ai_error = None, None
    if state.get("ai_enabled") and ai_api_key and summary is not None:
        try:
            from ccp.app.ai_analysis import generate_ai_analysis, get_provider

            provider = get_provider(
                provider_name=state.get("ai_provider") or "gemini",
                api_key=ai_api_key,
                azure_endpoint=state.get("ai_azure_endpoint", ""),
                azure_deployment=state.get("ai_azure_deployment", ""),
            )
            ai_text = generate_ai_analysis(
                provider=provider,
                trend_regression=analysis.get("regression", {}),
                summary_stats_df=summary,
                session_name=session_name,
            )
        except Exception as exc:  # the report is still produced without AI
            ai_error = str(exc)
    html = generate_html_report(
        trend_figs=trend_figs,
        perf_figs=perf_figs,
        summary_stats_df=summary,
        session_name=session_name,
        ai_analysis=ai_text,
    )
    return html, ai_error


# --------------------------------------------------------------------------
# Online monitoring
# --------------------------------------------------------------------------


def calculated_rows(df):
    return df[df["head"] > 0]


def monitoring_view(evaluation, results, history, state):
    """Figures, metric tiles and history table for the monitoring panel.

    Parameters
    ----------
    results : DataFrame
        The latest calculated rows.
    history : DataFrame
        The accumulated last five calculated rows (oldest first).
    """
    valid = results[results["valid"] == True] if "valid" in results else results  # noqa: E712
    latest = valid.iloc[-1] if len(valid) else results.iloc[-1]
    cluster = (
        int(latest["cluster"]) if not pd.isna(latest.get("cluster", np.nan)) else 0
    )
    impeller = evaluation.impellers_new[cluster]
    flow_units = plot_flow_units(state)
    speed = Q_(latest["speed"], state.get("speed_unit") or "rpm")
    similarity = bool(state.get("show_similarity"))
    figs = base_curves(impeller, speed, flow_units, similarity)

    expected_flow = Q_(latest["flow_v"], "m³/s").to(flow_units).m
    expected = {
        "head": Q_(latest["expected_head"], "J/kg").to(PLOT_HEAD_UNITS).m,
        "power": Q_(latest["expected_power"], "W").to(PLOT_POWER_UNITS).m,
        "eff": latest["expected_eff"],
        "disch_p": Q_(latest["expected_p_disch"], "bar").to(PLOT_P_UNITS).m,
    }
    hist = history.tail(5)
    n = len(hist)
    ops = []
    for i, (_, row) in enumerate(hist.iterrows()):
        ops.append(
            {
                "flow": Q_(row["flow_v"], "m³/s").to(flow_units).m,
                "head": Q_(row["head"], "J/kg").to(PLOT_HEAD_UNITS).m
                if row["head"] > 0
                else None,
                "eff": row["eff"] if row["eff"] > 0 else None,
                "power": Q_(row["power"], "W").to(PLOT_POWER_UNITS).m
                if row["power"] > 0
                else None,
                "disch_p": Q_(row["p_disch"], "bar").to(PLOT_P_UNITS).m
                if row["p_disch"] > 0
                else None,
                "opacity": 0.3 + 0.7 * i / max(n - 1, 1),
                "latest": i == n - 1,
            }
        )
    for name, fig in figs.items():
        if expected[name] > 0:
            fig.add_trace(
                go.Scatter(
                    x=[expected_flow],
                    y=[expected[name]],
                    mode="markers",
                    marker=dict(color="green", size=10, symbol="diamond"),
                    name="Expected Point",
                )
            )
        for op in ops:
            if op[name] is None:
                continue
            fig.add_trace(
                go.Scatter(
                    x=[op["flow"]],
                    y=[op[name]],
                    mode="markers",
                    marker=dict(color="black", size=8, symbol="circle"),
                    opacity=op["opacity"],
                    name="Operational Point" if op["latest"] else None,
                    showlegend=op["latest"],
                )
            )

    def metric(label, value, unit_value, delta):
        return {
            "label": label,
            "value": None if value is None else f"{value:.2f}",
            "delta": None if delta == -1 or pd.isna(delta) else f"{delta:.2f} %",
            "delta_value": None if delta == -1 or pd.isna(delta) else float(delta),
        }

    metrics = [
        metric(
            "Efficiency (%)",
            latest["eff"] * 100 if latest["eff"] > 0 else None,
            None,
            latest["delta_eff"],
        ),
        metric(
            "Head (kJ/kg)",
            Q_(latest["head"], "J/kg").to("kJ/kg").m if latest["head"] > 0 else None,
            None,
            latest["delta_head"],
        ),
        metric(
            "Power (kW)",
            Q_(latest["power"], "W").to("kW").m if latest["power"] > 0 else None,
            None,
            latest["delta_power"],
        ),
        metric(
            "Disch. Pressure (bar)",
            latest["p_disch"] if latest["p_disch"] > 0 else None,
            None,
            latest["delta_p_disch"],
        ),
    ]
    cols = [c for c in MONITOR_COLUMNS if c in hist.columns]
    table = {
        "columns": cols,
        "rows": [
            {
                "time": str(idx),
                "opacity": 0.4 + 0.6 * i / max(n - 1, 1),
                "values": [
                    (
                        bool(row[c])
                        if c == "valid"
                        else (None if pd.isna(row[c]) else round(float(row[c]), 2))
                    )
                    for c in cols
                ],
            }
            for i, (idx, row) in enumerate(hist.iterrows())
        ],
    }
    return {
        "figures": {name: fig_json(fig) for name, fig in figs.items()},
        "metrics": metrics,
        "table": table,
        "latest_time": str(latest.name),
        "cluster": cluster,
    }


def frame_to_records(df):
    return json.loads(df.to_json(orient="split", date_format="iso"))


def frame_from_records(data):
    df = pd.DataFrame(
        data["data"], index=pd.to_datetime(data["index"]), columns=data["columns"]
    )
    return df
