"""AI-powered analysis for performance-evaluation reports.

Ported from ``ccp/app/ai_analysis.py`` with an added graceful fallback:
when ``google-generativeai`` is not installed, or no API key is supplied,
:func:`generate_ai_analysis` returns a short Portuguese message instead
of raising, so the Django app can still run offline.

Portuguese system prompts and template text are preserved verbatim from
the original Streamlit module.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = (
    "Análise por IA indisponível (provedor '{provider}' não configurado)."
)

SYSTEM_PROMPT = """\
Você é um engenheiro especialista em desempenho de compressores centrífugos.
Sua função é analisar dados de avaliação de desempenho de compressores e
fornecer uma opinião técnica concisa e objetiva.

Ao analisar os dados, considere:
- Tendências de degradação ou melhoria na eficiência, head, potência e pressão
  de descarga ao longo do tempo.
- Desvios significativos entre valores medidos e esperados.
- Possíveis causas operacionais ou mecânicas para os desvios observados
  (fouling, erosão, desgaste de selos, mudanças nas condições de processo, etc.).
- Recomendações práticas quando aplicável.

Responda sempre em português brasileiro. Seja direto e técnico, evitando
repetições. Use no máximo 3-4 parágrafos por seção de análise.
"""

_SECTION_SEPARATOR = "---SECTION---"

_COMBINED_PROMPT_TEMPLATE = """\
{session_context}Regressão linear das tendências (desvios percentuais ao longo do tempo):
{regression_text}

Estatísticas descritivas dos desvios:
{stats_text}

Com base nos dados acima, forneça três análises separadas. Separe cada análise \
exatamente com a linha "{separator}" (sem espaços extras). Não inclua títulos \
ou cabeçalhos nas seções.

1. **Análise de Tendência**: Analise as tendências usando os resultados da \
regressão linear (slope em %/mês, R² e p-value). Um slope negativo em \
eficiência ou head indica degradação; um slope positivo em potência indica \
aumento de consumo. Considere a significância estatística (p-value) e o \
ajuste (R²) para determinar se as tendências são confiáveis. Discuta \
possíveis causas operacionais ou mecânicas.

2. **Análise de Desempenho**: Com base nas estatísticas dos desvios (média, \
desvio padrão, min, max), analise o desempenho do compressor. Comente sobre \
a magnitude dos desvios entre valores medidos e esperados e o que isso indica \
sobre a condição do equipamento.

3. **Estatísticas**: Faça uma análise resumida das estatísticas descritivas \
dos desvios. Destaque valores que merecem atenção e dê uma avaliação geral \
do estado do compressor."""


class AIProvider(ABC):
    """Abstract base class for AI/LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate text from a prompt.

        Parameters
        ----------
        prompt : str
            The user prompt to send to the model.

        Returns
        -------
        str
            The generated text response.
        """


class GeminiProvider(AIProvider):
    """Google Gemini provider backed by ``google-generativeai``."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is required for Gemini provider. "
                "Install it with: uv add google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
        )

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text


def _is_provider_available(provider: str) -> bool:
    """Return True if the backing library for *provider* can be imported."""
    if provider == "gemini":
        try:
            import google.generativeai  # noqa: F401
        except ImportError:
            return False
        return True
    return False


def _format_stats_for_prompt(summary_stats_df: Any) -> str:
    """Format a summary-statistics DataFrame as text for the AI prompt."""
    if summary_stats_df is None:
        return "Nenhuma estatística disponível."
    if hasattr(summary_stats_df, "empty") and summary_stats_df.empty:
        return "Nenhuma estatística disponível."
    return summary_stats_df.to_string()


def _format_regression_for_prompt(trend_regression: dict | None) -> str:
    """Format trend-regression results as text for the AI prompt."""
    if not trend_regression:
        return "Nenhum dado de regressão disponível."

    labels = {
        "delta_eff": "Delta Eficiência (%)",
        "delta_head": "Delta Head (%)",
        "delta_power": "Delta Potência (%)",
        "delta_p_disch": "Delta Pressão de Descarga (%)",
    }

    lines = []
    for col, data in trend_regression.items():
        label = labels.get(col, col)
        lines.append(
            f"- {label}: slope = {data['slope_per_month']:.4f} %/mês, "
            f"R² = {data['r_squared']:.4f}, "
            f"p-value = {data['p_value']:.2e}, "
            f"n = {data['n_points']} pontos"
        )
    return "\n".join(lines)


def _build_prompt(evaluation: Any) -> str:
    """Assemble the combined prompt text from an evaluation-like object.

    The function accepts either a mapping or a ``ccp.Evaluation`` instance
    and pulls the attributes used by the original Streamlit code:
    ``trend_regression``, ``summary_stats_df``, ``session_name``.
    Missing fields degrade to empty sections.
    """
    if isinstance(evaluation, dict):
        getter = evaluation.get
    else:

        def getter(key, default=None):
            return getattr(evaluation, key, default)

    regression_text = _format_regression_for_prompt(getter("trend_regression"))
    stats_text = _format_stats_for_prompt(getter("summary_stats_df"))
    session_name = getter("session_name", "") or ""
    session_context = f"Sessão de avaliação: {session_name}\n" if session_name else ""

    return _COMBINED_PROMPT_TEMPLATE.format(
        session_context=session_context,
        regression_text=regression_text,
        stats_text=stats_text,
        separator=_SECTION_SEPARATOR,
    )


def generate_ai_analysis(
    evaluation: Any,
    *,
    provider: str = "gemini",
    api_key: str | None = None,
) -> str:
    """Generate an AI analysis string for a performance evaluation.

    Parameters
    ----------
    evaluation : object
        Either a ``ccp.Evaluation`` instance or a mapping exposing the
        attributes ``trend_regression``, ``summary_stats_df`` and
        ``session_name``.
    provider : str, optional
        Name of the AI provider to use. Currently only ``"gemini"`` is
        wired up.
    api_key : str or None, optional
        API key for the provider. If ``None`` or empty, the function
        short-circuits to the offline fallback message.

    Returns
    -------
    str
        The generated analysis text, or a Portuguese fallback message
        (``"Análise por IA indisponível..."``) when the provider cannot
        be used. Sections in a successful response are delimited by
        ``"---SECTION---"`` as in the original implementation.
    """
    if not api_key:
        return UNAVAILABLE_MESSAGE.format(provider=provider)

    if not _is_provider_available(provider):
        logger.info("AI provider %r unavailable; returning fallback.", provider)
        return UNAVAILABLE_MESSAGE.format(provider=provider)

    try:
        if provider == "gemini":
            client: AIProvider = GeminiProvider(api_key=api_key)
        else:
            logger.warning("Unknown AI provider %r; returning fallback.", provider)
            return UNAVAILABLE_MESSAGE.format(provider=provider)

        prompt = _build_prompt(evaluation)
        return client.generate(prompt)
    except Exception as exc:
        logger.exception("AI analysis generation failed: %s", exc)
        return UNAVAILABLE_MESSAGE.format(provider=provider)
