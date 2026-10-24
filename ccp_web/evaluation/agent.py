"""Agent adapter of the performance evaluation page.

See ``ccp_web.agent.adapters`` for the interface. ``start`` is one of the
page's buttons (``params.action``): Run, Report, monitoring Start or Stop,
or a design case's Load button, through the same functions as the views
(``views.start_run``, ``curves.views.start_load`` ...).

The agent API never handles secrets, so anything that needs one is refused
with a 400 telling the agent the user must start it in the browser: a run or
monitoring on the PI data source (PI password) and a report with the AI
analysis (AI API key). Runs on an uploaded plant data file or on mock data
and reports without AI need no secret.

Results and figures come from what the jobs stored (the analysis JSON, the
results table, the monitoring job's result): ``Evaluation.load`` takes
seconds, so no request loads the evaluation itself.
"""

import re

from ccp_web.agent.adapters import json_safe
from ccp_web.core.models import Job
from ccp_web.curves.views import start_load
from ccp_web.services import evaluation as ev
from ccp_web.services import schemas, units

from .jobs import ANALYSIS_KEY, REPORT_KEY, TABLE_KEY
from .views import (
    NO_EVALUATION,
    ensure_analysis,
    load_analysis,
    run_errors,
    source_errors,
    start_monitoring,
    start_report,
    start_run,
    stop_monitoring,
)

APP_TYPES = ("performance_evaluation",)
ACTIONS = ("run", "report", "monitoring_start", "monitoring_stop", "load")
MODES = ("run", "full_rebuild")
PARAMS = {
    "action": (
        "run (default): the evaluation job; report: the HTML report; "
        "monitoring_start / monitoring_stop: online monitoring; load: load "
        "the Engauge curves of one design case (its Load button, needs "
        "'letter'). Runs and monitoring on the PI data source need the PI "
        "password and must be started by the user in the browser"
    ),
    "letter": f"action=load only: the design case, one of {schemas.CASES}",
    "mode": (
        "action=run only: 'run' (default; appends the new plant data to the "
        "saved evaluation) or 'full_rebuild' (re-evaluates everything; minutes)"
    ),
    "ai": (
        "action=report only, bool: must be false when ai_enabled is set; the "
        "AI analysis needs the AI API key, so a report with it must be started "
        "in the browser"
    ),
}
ACTION_PARAMS = {
    "run": {"action", "mode"},
    "report": {"action", "ai"},
    "monitoring_start": {"action"},
    "monitoring_stop": {"action"},
    "load": {"action", "letter"},
}
PI_MESSAGE = (
    "{what} on the PI data source needs the PI password, which the agent API "
    "never handles: ask the user to start it in the browser (or switch "
    "data_source to 'file' or 'mock')"
)
AI_MESSAGE = (
    "the report's AI analysis needs the AI API key, which the agent API never "
    "handles: ask the user to generate it in the browser, or pass "
    '{"action": "report", "ai": false} to build the report without it'
)
DELTA_COLUMNS = list(ev.TREND_PLOTS)
# Units of the evaluation table (``Evaluation.df``, SI as stored). The
# deltas are relative differences in percent, except delta_eff, which is the
# efficiency difference in percentage points.
TABLE_UNITS = {
    "flow_v": "m³/s",
    "flow_m": "kg/s",
    "eff": "fraction",
    "expected_eff": "fraction",
    "delta_eff": "percentage points",
    "head": "J/kg",
    "expected_head": "J/kg",
    "delta_head": "%",
    "power": "W",
    "expected_power": "W",
    "delta_power": "%",
    "p_disch": "bar",
    "expected_p_disch": "bar",
    "delta_p_disch": "%",
    "valid": "bool",
    "cluster": "index of the converted curve (0-based)",
}
TABLE_TAIL = 10
PERF_FIGURES = [
    ("head", "Head"),
    ("eff", "Efficiency"),
    ("power", "Power"),
    ("disch_p", "Discharge pressure"),
]
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}
_LABEL_UNITS = re.compile(r"^(?P<name>.*?)\s*\((?P<units>[^)]*)\)\s*$")


def _flag(name, value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in _TRUE | _FALSE:
        return value.strip().lower() in _TRUE
    raise ValueError(f"{name}: expected true or false, got {value!r}")


def _source(case):
    return case.state.get("data_source") or "pi"


def _refuse_pi(case, what, errors):
    """400 for a PI run: field errors first (they block the browser too)."""
    if _source(case) != "pi":
        return
    errors = errors(case)
    if errors:
        raise units.InputError(errors)
    raise ValueError(PI_MESSAGE.format(what=what))


def _latest(case, kind):
    return Job.objects.filter(case=case, kind=kind).order_by("-created").first()


def start(case, params):
    """Start the button ``params["action"]`` (default ``run``); see ``PARAMS``."""
    params = dict(params or {})
    unknown = sorted(set(params) - set(PARAMS))
    if unknown:
        raise ValueError(f"unknown params {unknown}; expected {sorted(PARAMS)}")
    action = params.get("action") or "run"
    if action not in ACTIONS:
        raise ValueError(f"action: expected one of {list(ACTIONS)}, got {action!r}")
    misplaced = sorted(set(params) - ACTION_PARAMS[action])
    if misplaced:
        raise ValueError(f"params {misplaced} do not apply to action {action!r}")

    if action == "run":
        mode = params.get("mode") or "run"
        if mode not in MODES:
            raise ValueError(f"mode: expected one of {list(MODES)}, got {mode!r}")
        _refuse_pi(case, "an evaluation run", run_errors)
        return start_run(case, mode)

    if action == "report":
        ai = _flag("ai", params.get("ai"))
        if ai or (case.state.get("ai_enabled") and ai is None):
            raise ValueError(AI_MESSAGE)
        if case.artifact(ANALYSIS_KEY) is None:
            raise units.InputError(
                {"eval_start": "Run an evaluation first to generate a report."}
            )
        return start_report(case)

    if action == "load":
        letter = params.get("letter")
        if not isinstance(letter, str) or letter.strip().upper() not in schemas.CASES:
            raise ValueError(
                f"action 'load' needs 'letter', one of {schemas.CASES}; got {letter!r}"
            )
        return start_load(case, letter.strip().upper())

    if action == "monitoring_start":
        # Checked before ``start_monitoring`` stops the running monitor, so a
        # refused request changes nothing.
        if case.artifact("evaluation") is None:
            raise units.InputError({}, NO_EVALUATION)
        _refuse_pi(case, "online monitoring", source_errors)
        return start_monitoring(case)

    stop_monitoring(case)
    job = _latest(case, "monitoring")
    if job is None:
        raise ValueError("online monitoring was never started for this case")
    job.refresh_from_db()
    return job


def has_results(case):
    return case.artifact("evaluation") is not None


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


def _job_info(job):
    if job is None:
        return None
    return {
        "id": job.pk,
        "kind": job.kind,
        "status": job.status,
        "active": job.is_active,
        "message": job.message,
        "error": job.error,
        "warnings": list(job.warnings or []),
        "params": job.params,
        "created": job.created,
        "finished": job.finished,
    }


def _metric(item):
    """A monitoring tile as a number with its units (the label carries them)."""
    match = _LABEL_UNITS.match(item.get("label") or "")
    name, unit = (match["name"], match["units"]) if match else (item.get("label"), None)
    value = item.get("value")
    try:
        value = None if value is None else float(value)
    except (TypeError, ValueError):
        pass
    return {
        "name": name,
        "value": value,
        "units": unit,
        # (operational - expected) / expected in %; for the efficiency, the
        # difference in percentage points.
        "delta": item.get("delta_value"),
        "delta_units": "percentage points" if name == "Efficiency" else "%",
    }


def _monitoring(case):
    job = _latest(case, "monitoring")
    out = {"available": False, "job": _job_info(job)}
    if job is None:
        out["reason"] = "not started: run calculate with action=monitoring_start"
        return out
    result = job.result or {}
    view = result.get("view")
    out.update(
        {
            "running": job.is_active,
            "ticks": result.get("ticks"),
            "last_fetch": result.get("last_fetch"),
            "interval_s": result.get("interval"),
            "fetch_error": result.get("error"),
            "errors": result.get("errors") or {},
        }
    )
    if not view:
        out["reason"] = "no point calculated yet"
        return out
    table = view.get("table") or {}
    columns = table.get("columns") or []
    out.update(
        {
            "available": True,
            "latest_time": view.get("latest_time"),
            "cluster": view.get("cluster"),
            "metrics": [_metric(m) for m in view.get("metrics") or []],
            "recent_points": {
                "units": {c: TABLE_UNITS.get(c) for c in columns},
                "rows": [
                    {"time": row.get("time"), **dict(zip(columns, row["values"]))}
                    for row in table.get("rows") or []
                ],
            },
            "figures": [f"monitoring_{name}" for name in view.get("figures") or {}],
        }
    )
    return out


def _report(case):
    artifact = case.artifact(REPORT_KEY)
    return {
        "available": artifact is not None,
        "artifact": artifact.key if artifact is not None else None,
        "created": artifact.created if artifact is not None else None,
        "job": _job_info(_latest(case, "report")),
    }


def _table(case):
    """The results table: per-cluster counts and its last rows, with units."""
    artifact = case.artifact(TABLE_KEY)
    if artifact is None:
        return None, []
    df = ev.table_from_parquet(artifact.read())
    clusters = []
    if "cluster" in df:
        valid = df["valid"] == True if "valid" in df else None  # noqa: E712
        for k, rows in df.groupby("cluster"):
            item = {
                "index": int(k),
                "name": f"Converted Curve {int(k) + 1}",
                "n_rows": len(rows),
                "start": rows.index.min(),
                "end": rows.index.max(),
            }
            if valid is not None:
                item["n_valid"] = int(valid.loc[rows.index].sum())
            clusters.append(item)
    tail = df.tail(TABLE_TAIL)
    table = {
        "n_rows": len(df),
        "columns": list(df.columns),
        "units": {c: TABLE_UNITS.get(c) for c in df.columns},
        "last_rows": [{"time": idx, **row.to_dict()} for idx, row in tail.iterrows()],
        "excel": "the full table is the page's Excel download",
    }
    return table, clusters


def _summary(analysis):
    summary = ev.summary_frame(analysis)
    if summary is None:
        return None
    return {
        **ev.frame_to_records(summary),
        "units": {c: TABLE_UNITS.get(c) for c in summary.columns},
        "note": "describe() of the deltas over the valid rows; 'count' is a number "
        "of rows",
    }


def _design_cases(case):
    """Which design cases have their curves loaded (the run needs one)."""
    state = case.state
    return [
        {
            "letter": letter,
            "loaded": case.artifact(f"impeller_case_{letter}") is not None,
            "curve_name": state.get(f"curve_name_case_{letter}") or None,
            "load_job": _job_info(_latest_load(case, letter)),
        }
        for letter in schemas.CASES
    ]


def _latest_load(case, letter):
    return (
        Job.objects.filter(case=case, kind="load_curves", params__case=letter)
        .order_by("-created")
        .first()
    )


def results(case):
    """Summary statistics, trends, clusters, report and monitoring status.

    Units are explicit in the ``units`` maps (the table is SI, as stored).
    """
    job = _latest(case, "evaluation")
    analysis = load_analysis(case)
    if analysis is None and case.artifact("evaluation") is not None:
        # An imported evaluation: build its plots as opening the page does.
        ensure_analysis(case)
        analysis = load_analysis(case)
    if analysis is None:
        build = _latest(case, "analysis")
        if case.artifact("evaluation") is not None:
            reason = "the plots and tables of the evaluation are being built"
            if build is not None and build.status == Job.FAILED:
                reason = f"building the plots failed: {build.error}"
            elif build is not None:
                reason += f": wait for job {build.pk} (GET jobs/{build.pk}?wait=60)"
        elif job is not None and job.status == Job.FAILED:
            reason = f"the last evaluation run failed: {job.error}"
        elif job is not None and job.is_active:
            reason = f"the evaluation is running: wait for job {job.pk}"
        else:
            reason = "not evaluated yet: run calculate (action=run)"
        out = {
            "available": False,
            "reason": reason,
            "job": _job_info(job),
            "analysis_job": _job_info(build),
            "monitoring": _monitoring(case),
            "design_cases": _design_cases(case),
        }
        if job is not None and job.status == Job.FAILED:
            out["errors"] = (job.result or {}).get("errors") or {}
        return json_safe(out)

    table, clusters = _table(case)
    state = case.state
    evaluation = case.artifact("evaluation")
    # The run, and the plot build after it, save state after the artifact
    # (the default window): compare with when the last of them finished.
    done = evaluation.created if evaluation is not None else None
    if done is not None:
        for kind in ("evaluation", "analysis"):
            last = (
                Job.objects.filter(case=case, kind=kind, status=Job.SUCCEEDED)
                .exclude(finished=None)
                .order_by("-finished")
                .first()
            )
            if last is not None:
                done = max(done, last.finished)
    out = {
        "available": True,
        "app_type": case.app_type,
        "data_source": _source(case),
        "evaluated": {
            "start": analysis.get("start") or None,
            "end": analysis.get("end") or None,
            "n_rows": analysis.get("n_rows"),
            "n_valid": analysis.get("n_valid"),
        },
        "window": {"start": state.get("eval_start"), "end": state.get("eval_end")},
        "summary": _summary(analysis),
        "trend_regression": analysis.get("regression") or {},
        "trend_regression_units": {
            "slope_per_month": "unit of the delta per month (30.44 days)",
            "r_squared": "",
            "p_value": "",
            "n_points": "count",
        },
        "clusters": {
            "n_clusters": analysis.get("n_clusters", 0),
            "selected": int(float(state.get("eval_cluster_idx") or 0)),
            "show_similarity": bool(state.get("eval_show_similarity")),
            "items": clusters,
        },
        "table": table,
        "report": _report(case),
        "monitoring": _monitoring(case),
        "calculated": evaluation.created if evaluation is not None else None,
        "inputs_saved_after_calculation": done is not None and case.updated > done,
        "design_cases": _design_cases(case),
        "job": _job_info(job),
    }
    return json_safe(out)


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------


def _perf_id(cluster, name, similarity):
    return f"perf_{cluster}_{name}" + ("_similarity" if similarity else "")


def _figure_index(case):
    """``{id: (title, section, plotly JSON getter)}`` of the stored figures."""
    items = {}
    analysis = load_analysis(case)
    if analysis is not None:
        for t in analysis.get("trend", []):
            items[f"trend_{t['key']}"] = (
                f"Trend: {t['title']}",
                "trend",
                lambda t=t: t["figure"],
            )
        for key, figs in sorted(analysis.get("perf", {}).items()):
            cluster, similarity = (int(p) for p in key.split(":"))
            for name, title in PERF_FIGURES:
                if name not in figs:
                    continue
                label = f"{title} · Converted Curve {cluster + 1}"
                if similarity:
                    label += " (similarity)"
                items[_perf_id(cluster, name, similarity)] = (
                    label,
                    "performance",
                    lambda f=figs, n=name: f[n],
                )
    monitor = _latest(case, "monitoring")
    view = (monitor.result or {}).get("view") if monitor is not None else None
    if view:
        titles = dict(PERF_FIGURES)
        for name, fig in (view.get("figures") or {}).items():
            items[f"monitoring_{name}"] = (
                f"Monitoring: {titles.get(name, name)}",
                "monitoring",
                lambda f=fig: f,
            )
    return items


def figures(case):
    return [
        {"id": fid, "title": title, "section": section}
        for fid, (title, section, _) in _figure_index(case).items()
    ]


def figure(case, figure_id):
    """One stored figure (rebuilt from its JSON; never a new evaluation load)."""
    item = _figure_index(case).get(figure_id)
    if item is None:
        raise KeyError(figure_id)
    return ev.fig_from_json(item[2]())
