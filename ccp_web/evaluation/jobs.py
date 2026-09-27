import json
import traceback
import warnings
from datetime import datetime

import pandas as pd

from ccp.point import PhaseWarning
from ccp_web.core import storage
from ccp_web.core.jobs import register
from ccp_web.curves.jobs import loaded_impellers
from ccp_web.services import evaluation as ev
from ccp_web.services import plant_data, units
from ccp_web.services.units import InputError

ANALYSIS_KEY = "evaluation_analysis"
TABLE_KEY = "evaluation_table"
REPORT_KEY = "report"
MONITOR_HISTORY = 5


def plant_file(case):
    f = case.file("plant_data")
    return (f.name, f.read()) if f is not None else None


def fetcher(case, state, pi_password):
    """``fetch(start, end)`` for the case's data source."""
    tm = plant_data.tag_mappings(state, pi_password=pi_password)
    source = state.get("data_source") or "pi"
    file = plant_file(case) if source == "file" else None

    def fetch(start, end):
        return plant_data.fetch(source, tm, start, end, file=file)

    return fetch


def store_analysis(ctx, evaluation, state):
    ctx.progress(0.85, "Building plots and tables...")
    analysis, table = ev.analyse(evaluation, state, progress=ctx.progress)
    ctx.save_artifact(ANALYSIS_KEY, "evaluation_analysis.json", json.dumps(analysis))
    ctx.save_artifact(TABLE_KEY, "evaluation_table.parquet", ev.table_to_parquet(table))
    # As in Streamlit, the window defaults to the evaluated data range.
    if analysis["start"] and not (state.get("eval_start") and state.get("eval_end")):
        fmt = lambda s: pd.Timestamp(s).tz_localize(None).isoformat(timespec="minutes")  # noqa: E731
        ctx.update_state(
            eval_start=fmt(analysis["start"]), eval_end=fmt(analysis["end"])
        )
    return analysis


@register("evaluation")
def run_evaluation(ctx):
    case = ctx.case
    state = case.state
    mode = ctx.params.get("mode", "run")
    with units.state_context(state):
        ctx.progress(0.02, "Loading design curves...")
        impellers = [imp for _, imp in sorted(loaded_impellers(case).items())]
        existing = None
        if mode != "full_rebuild" and case.artifact("evaluation") is not None:
            ctx.progress(0.04, "Loading the saved evaluation...")
            existing = ev.load(case.artifact("evaluation").read(), state)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", PhaseWarning)
            evaluation, message = ev.run(
                state,
                impellers,
                existing,
                mode,
                fetcher(case, state, ctx.secret("pi_password")),
                parallel=True,
                progress=ctx.progress,
            )
        for w in caught:
            if issubclass(w.category, PhaseWarning):
                ctx.warn(str(w.message))
        if evaluation is None:
            ctx.job.message = message
            return
        ctx.progress(0.8, "Saving the evaluation...")
        ctx.save_artifact("evaluation", "evaluation.zip", ev.save(evaluation))
        analysis = store_analysis(ctx, evaluation, state)
    # The report must be recreated for the new results.
    storage.delete_artifacts(case, [REPORT_KEY])
    ctx.job.message = message
    ctx.set_result(n_rows=analysis["n_rows"], n_valid=analysis["n_valid"])


@register("analysis")
def rebuild_analysis(ctx):
    """Figures and tables for an evaluation imported from a .ccp file."""
    case = ctx.case
    state = case.state
    with units.state_context(state):
        ctx.progress(0.05, "Loading the saved evaluation...")
        evaluation = ev.load(case.artifact("evaluation").read(), state)
        analysis = store_analysis(ctx, evaluation, state)
    ctx.job.message = f"{analysis['n_valid']} valid of {analysis['n_rows']} rows"


@register("report")
def build_report(ctx):
    case = ctx.case
    artifact = case.artifact(ANALYSIS_KEY)
    if artifact is None:
        raise InputError(
            {"eval_start": "Run an evaluation first to generate a report."}
        )
    ctx.progress(0.1, "Generating the report...")
    analysis = json.loads(artifact.read())
    api_key = ctx.secret("ai_api_key")
    if case.state.get("ai_enabled") and api_key:
        ctx.progress(0.2, "Generating AI analysis...")
    html, ai_error = ev.report_html(analysis, case.state, case.name, ai_api_key=api_key)
    ctx.save_artifact(REPORT_KEY, "ccp_performance_report.html", html)
    if ai_error:
        ctx.warn(f"AI analysis failed (report generated without AI): {ai_error}")
    ctx.job.message = "Report ready"


@register("monitoring", queue="monitoring")
def monitoring(ctx):
    """Online monitoring loop: runs until the job is cancelled (Stop)."""
    case = ctx.case
    state = case.state
    interval = max(5, min(60, int(float(state.get("refresh_interval") or 30))))
    source = state.get("data_source") or "pi"
    file = plant_file(case) if source == "file" else None
    tm = plant_data.tag_mappings(state, pi_password=ctx.secret("pi_password"))
    with units.state_context(state):
        ctx.progress(0.1, "Loading the evaluation...")
        evaluation = ev.load(case.artifact("evaluation").read(), state)
        ctx.progress(0.3, "Calculating the latest points...")
        first = evaluation.calculate_points(
            evaluation.data.tail(5), drop_invalid_values=False, parallel=False
        )
        calculated = ev.calculated_rows(first)
        if calculated.empty:
            raise InputError(
                {
                    "temperature_fluctuation": (
                        "No points could be calculated. Check data quality thresholds."
                    )
                }
            )
        history = calculated.tail(MONITOR_HISTORY)
        latest = calculated
        ticks = 0
        max_ticks = ctx.params.get("max_ticks")  # tests stop the loop
        while max_ticks is None or ticks <= max_ticks:
            view = ev.monitoring_view(evaluation, latest, history, state)
            ctx.progress(0.5, f"Monitoring · last point {view['latest_time']}")
            ctx.set_result(
                view=view,
                ticks=ticks,
                last_fetch=datetime.now().isoformat(timespec="seconds"),
                interval=interval,
                error=None,
            )
            ticks += 1
            if max_ticks is not None and ticks > max_ticks:
                break
            ctx.sleep(0 if max_ticks is not None else interval)
            try:
                df_new = plant_data.fetch_online(source, tm, file=file)
                results = evaluation.calculate_points(
                    df_new, drop_invalid_values=False, parallel=False
                )
                new = ev.calculated_rows(results)
                if not new.empty:
                    history = pd.concat([history, new]).tail(MONITOR_HISTORY)
                    latest = new
            except Exception as exc:  # keep monitoring through PI hiccups
                ctx.set_result(
                    error=f"{type(exc).__name__}: {exc}",
                    error_trace=traceback.format_exc()[-2000:],
                )
                ctx.sleep(1)
