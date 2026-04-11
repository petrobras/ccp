"""High-level orchestration for running a performance evaluation.

Ports the ``_trigger_evaluation`` branch of
``ccp/app/pages/4_performance_evaluation.py`` to a pure, request-free
callable that Django views can invoke synchronously.

The function:

1. Pulls impellers + tag mappings from the caller-provided ``form_data``
   (already validated by Unit 8's ``PerformanceEvaluationForm``).
2. Fetches measured data from PI via :mod:`apps.integrations.pi_client`
   with a graceful fallback to a CSV file on disk.
3. Builds a :class:`ccp.Evaluation` via
   :func:`apps.core.services.ccp_service.build_evaluation`.
4. Generates trend + performance figures.
5. Optionally calls the AI analysis service to produce a textual summary.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd

import ccp

from apps.performance_evaluation.services import figures as _figures
from apps.performance_evaluation.services import monitoring_state

try:  # pragma: no cover - exercised when Unit 2 is merged
    from apps.core.services.ccp_service import build_evaluation
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.ccp_service import build_evaluation

try:  # pragma: no cover
    from apps.integrations.pi_client import fetch_pi_data, is_pi_available
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.integrations import (
        fetch_pi_data,
        is_pi_available,
    )

try:  # pragma: no cover
    from apps.integrations.ai_analysis import generate_ai_analysis
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.integrations import generate_ai_analysis

try:  # pragma: no cover
    from apps.core.session_store import get_session, set_session
except Exception:  # pragma: no cover
    from apps.performance_evaluation._stubs.session_store import (
        get_session,
        set_session,
    )


logger = logging.getLogger(__name__)

Q_ = ccp.Q_


def _coerce_datetime(value: Any) -> datetime | None:
    """Coerce ``value`` to a naive :class:`datetime` if possible."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return pd.Timestamp(value).to_pydatetime()


def _load_measured_data(
    form_data: dict[str, Any],
    tag_mappings: dict[str, Any],
    start: datetime | None,
    end: datetime | None,
) -> pd.DataFrame:
    """Return the raw measured DataFrame.

    Pre-supplied ``measured_data`` (already a DataFrame) wins, otherwise
    the CSV path in ``measured_csv`` is read, otherwise the PI client is
    used when available.
    """
    measured = form_data.get("measured_data")
    if isinstance(measured, pd.DataFrame):
        return measured.copy()

    csv_path = form_data.get("measured_csv")
    if csv_path:
        return pd.read_csv(csv_path, index_col=0, parse_dates=True)

    if is_pi_available():
        return fetch_pi_data(
            tag_mappings,
            start=start,
            end=end,
            testing=bool(form_data.get("testing", False)),
        )
    return pd.DataFrame()


def _build_evaluation_kwargs(
    form_data: dict[str, Any],
    impellers: list[Any],
    df_raw: pd.DataFrame,
) -> dict[str, Any]:
    """Assemble the kwargs dict for ``ccp.Evaluation``."""
    data_units = form_data.get("data_units", {}) or {}

    kwargs: dict[str, Any] = {
        "data": df_raw,
        "operation_fluid": form_data.get("operation_fluid"),
        "data_units": data_units,
        "impellers": impellers,
        "n_clusters": len(impellers) or 1,
        "calculate_points": True,
        "parallel": not bool(form_data.get("testing", False)),
        "temperature_fluctuation": float(form_data.get("temperature_fluctuation", 0.5)),
        "pressure_fluctuation": float(form_data.get("pressure_fluctuation", 2.0)),
        "speed_fluctuation": float(form_data.get("speed_fluctuation", 0.5)),
    }

    flow_method = form_data.get("flow_method", "Direct")
    if flow_method != "Direct":
        kwargs["D"] = Q_(
            form_data.get("orifice_D", 0.5905),
            form_data.get("orifice_D_unit", "m"),
        )
        kwargs["d"] = Q_(
            form_data.get("orifice_d", 0.3661),
            form_data.get("orifice_d_unit", "m"),
        )
        kwargs["tappings"] = form_data.get("orifice_tappings", "flange")

    kwargs.update(form_data.get("evaluation_kwargs", {}) or {})
    return kwargs


def run_evaluation(
    form_data: dict[str, Any],
    session_id: str,
    *,
    evaluation: Any | None = None,
) -> dict[str, Any]:
    """Run one performance evaluation cycle.

    Parameters
    ----------
    form_data : dict
        Validated form payload from Unit 8's form.
    session_id : str
        Redis-backed session identifier. Used for state lookups and
        monitoring bookkeeping.
    evaluation : ccp.Evaluation, optional
        Pre-built evaluation object. When given the heavy
        ``build_evaluation`` call is skipped (used by tests and by the
        incremental refresh path).

    Returns
    -------
    dict
        ``{"evaluation", "figures", "summary_df", "ai_summary",
        "error", "trend", "performance"}``.
    """
    impellers = list(form_data.get("impellers") or [])
    tag_mappings = form_data.get("tag_mappings") or {}
    start = _coerce_datetime(form_data.get("start_datetime"))
    end = _coerce_datetime(form_data.get("end_datetime"))

    error: str | None = None

    if evaluation is None:
        try:
            df_raw = _load_measured_data(form_data, tag_mappings, start, end)
            kwargs = _build_evaluation_kwargs(form_data, impellers, df_raw)
            evaluation = build_evaluation(**kwargs)
        except Exception as exc:  # pragma: no cover - surfaced to the UI
            logger.exception("Failed to build ccp.Evaluation")
            error = str(exc)
            evaluation = None

    trend_result = (
        _figures.build_trend_figures(evaluation)
        if evaluation is not None
        else {"figures": {}, "regression": {}, "empty": True}
    )
    perf_result = (
        _figures.build_performance_figures(
            evaluation,
            cluster_idx=int(form_data.get("cluster_idx", 0)),
            show_similarity=bool(form_data.get("show_similarity", False)),
            flow_units=form_data.get("flow_units", "m³/s"),
            head_units=form_data.get("head_units", "kJ/kg"),
            power_units=form_data.get("power_units", "kW"),
            pressure_units=form_data.get("pressure_units", "bar"),
            speed_units=form_data.get("speed_units", "rpm"),
        )
        if evaluation is not None
        else {"figures": {}, "empty": True, "cluster_idx": 0, "n_clusters": 0}
    )
    summary_df = (
        _figures.build_summary_stats(evaluation) if evaluation is not None else None
    )

    ai_summary = ""
    if (
        evaluation is not None
        and form_data.get("ai_enabled")
        and form_data.get("ai_api_key")
    ):
        try:
            ai_summary = generate_ai_analysis(
                evaluation,
                provider=form_data.get("ai_provider", "gemini"),
                api_key=form_data.get("ai_api_key"),
                azure_endpoint=form_data.get("ai_azure_endpoint"),
                azure_deployment=form_data.get("ai_azure_deployment"),
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("AI analysis failed: %s", exc)
            ai_summary = ""

    # Persist a lightweight pointer in the Redis session for subsequent
    # HTMX polls. The heavy Evaluation object itself is stored by the view
    # (either directly, or via GridFS when larger than 16 MB).
    state = get_session(session_id) or {}
    state["has_evaluation"] = evaluation is not None
    state["last_run"] = pd.Timestamp.utcnow().isoformat()
    set_session(session_id, state)

    figures_bundle: dict[str, Any] = {}
    figures_bundle.update(
        {f"trend_{k}": v for k, v in trend_result.get("figures", {}).items()}
    )
    figures_bundle.update(
        {f"perf_{k}": v for k, v in perf_result.get("figures", {}).items()}
    )

    return {
        "evaluation": evaluation,
        "figures": figures_bundle,
        "trend": trend_result,
        "performance": perf_result,
        "summary_df": summary_df,
        "ai_summary": ai_summary,
        "monitoring": monitoring_state.snapshot(session_id),
        "error": error,
    }


__all__ = ["run_evaluation"]
