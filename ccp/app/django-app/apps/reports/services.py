"""HTML report rendering for CCP performance evaluations.

This module is the Django port of ``ccp/app/report.py``. It builds a
self-contained HTML document with interactive Plotly figures that can be
served inline or downloaded as an attachment.
"""

from __future__ import annotations

import base64
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import plotly.io as pio
from django.template.loader import render_to_string

try:  # pragma: no cover - optional dependency
    import markdown as _markdown
except ImportError:  # pragma: no cover - offline fallback
    _markdown = None

try:  # type-hint only import - kept to satisfy the cross-unit contract.
    from apps.core.services import ccp_service  # noqa: F401
except ImportError:  # pragma: no cover - stub fallback
    from apps.reports._stubs import ccp_service  # noqa: F401


LOGO_PATH = Path(__file__).resolve().parents[3] / "ccp" / "app" / "assets" / "ccp.png"

TREND_SECTION_TITLE = "Análise de Tendência"
PERFORMANCE_SECTION_TITLE = "Curvas de Desempenho com Pontos Históricos"
STATS_SECTION_TITLE = "Estatísticas Resumidas"

TREND_SECTION_DESCRIPTION = (
    "Os gráficos abaixo apresentam a evolução temporal dos desvios percentuais "
    "entre os valores medidos e os valores esperados para eficiência, head, "
    "potência e pressão de descarga. A linha tracejada vermelha indica o valor "
    "de referência (desvio zero). Uma regressão linear com banda de confiança "
    "de 95% é incluída para identificar tendências de degradação ou melhoria "
    "ao longo do tempo."
)
PERFORMANCE_SECTION_DESCRIPTION = (
    "Esta seção apresenta as curvas de desempenho do compressor (head, "
    "potência, eficiência e pressão de descarga) em função da vazão volumétrica "
    "de sucção. Os pontos operacionais medidos são sobrepostos às curvas "
    "esperadas, permitindo a comparação direta entre o desempenho real e o "
    "desempenho de projeto/garantia."
)
STATS_SECTION_DESCRIPTION = (
    "A tabela a seguir apresenta as estatísticas descritivas dos desvios "
    "calculados, incluindo média, desvio padrão, valores mínimo e máximo, e "
    "quartis. Estes valores auxiliam na avaliação quantitativa do desempenho "
    "do compressor ao longo do período analisado."
)


@lru_cache(maxsize=1)
def _encode_logo() -> str:
    """Return the CCP logo as a ``data:image/png;base64`` URI, or ``""``."""
    try:
        raw = LOGO_PATH.read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def _figure_to_div(fig: Any, *, include_plotlyjs: bool) -> str:
    """Render a single Plotly figure to an HTML ``<div>`` string."""
    return pio.to_html(fig, full_html=False, include_plotlyjs=include_plotlyjs)


def _ai_html(ai_summary: Any, key: str) -> str:
    """Return the rendered ``<div class="ai-analysis">`` block or ``""``."""
    if isinstance(ai_summary, Mapping):
        text = ai_summary.get(key, "")
    elif key == "trend" and isinstance(ai_summary, str):
        text = ai_summary
    else:
        text = ""
    if not text:
        return ""
    if _markdown is not None:
        body = _markdown.markdown(text)
    else:
        body = "<p>" + str(text).replace("\n", "<br>") + "</p>"
    return (
        f'<div class="ai-analysis"><div class="ai-label">Análise IA</div>{body}</div>'
    )


def _stats_table_html(stats: Any) -> str:
    """Render ``stats`` to an HTML table, tolerating ``None``/empty frames."""
    if stats is None:
        return "<p>Estatísticas resumidas não disponíveis.</p>"
    to_html = getattr(stats, "to_html", None)
    empty = getattr(stats, "empty", False)
    if to_html is None or empty:
        return "<p>Estatísticas resumidas não disponíveis.</p>"
    return to_html(
        classes="stats-table",
        float_format=lambda x: f"{x:.4f}",
    )


def render_html_report(
    evaluation: Any,
    figures: Mapping[str, Any],
    ai_summary: Any = "",
) -> str:
    """Render a standalone HTML performance report.

    Parameters
    ----------
    evaluation : apps.core.services.ccp_service.Evaluation or None
        Source evaluation. Only ``evaluation.name`` and
        ``evaluation.summary_stats`` are read, both optionally; the figures
        themselves come from ``figures``.
    figures : mapping
        Mapping with keys ``"trend"`` and ``"performance"`` each holding an
        iterable of Plotly figures. Optional key ``"stats"`` may hold a
        pandas DataFrame (otherwise read from ``evaluation.summary_stats``).
    ai_summary : str or mapping, optional
        Either a plain string (used for the trend section) or a mapping with
        keys ``"trend"``, ``"performance"`` and ``"stats"`` as produced by
        :mod:`apps.integrations.ai_analysis`.

    Returns
    -------
    str
        A complete HTML document (``<!DOCTYPE html>`` ... ``</html>``).
    """
    trend_figs = list(figures.get("trend") or [])
    perf_figs = list(figures.get("performance") or [])
    all_divs = [
        _figure_to_div(fig, include_plotlyjs=(i == 0))
        for i, fig in enumerate(trend_figs + perf_figs)
    ]
    trend_divs = all_divs[: len(trend_figs)]
    perf_divs = all_divs[len(trend_figs) :]

    stats_df = figures.get("stats")
    if stats_df is None and evaluation is not None:
        stats_df = getattr(evaluation, "summary_stats", None)

    session_name = ""
    if evaluation is not None:
        session_name = getattr(evaluation, "name", "") or ""

    context = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "logo_data_uri": _encode_logo(),
        "session_name": session_name,
        "trend_title": TREND_SECTION_TITLE,
        "trend_description": TREND_SECTION_DESCRIPTION,
        "trend_divs": trend_divs,
        "trend_ai_html": _ai_html(ai_summary, "trend"),
        "performance_title": PERFORMANCE_SECTION_TITLE,
        "performance_description": PERFORMANCE_SECTION_DESCRIPTION,
        "perf_divs": perf_divs,
        "performance_ai_html": _ai_html(ai_summary, "performance"),
        "stats_title": STATS_SECTION_TITLE,
        "stats_description": STATS_SECTION_DESCRIPTION,
        "stats_table_html": _stats_table_html(stats_df),
        "stats_ai_html": _ai_html(ai_summary, "stats"),
    }
    return render_to_string("reports/report.html", context)
