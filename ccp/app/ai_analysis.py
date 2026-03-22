"""AI-powered analysis for performance evaluation reports.

Provides a modular interface for generating AI analysis text using
different LLM providers (Google Gemini, Azure OpenAI, etc.).
"""

import logging
from abc import ABC, abstractmethod

import pandas as pd

logger = logging.getLogger(__name__)

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
    """Google Gemini AI provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai is required for Gemini provider. "
                "Install it with: uv add google-generativeai"
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=SYSTEM_PROMPT,
        )

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text


class AzureOpenAIProvider(AIProvider):
    """Azure OpenAI provider (placeholder)."""

    def __init__(self, api_key: str, endpoint: str, deployment: str):
        # TODO: Implement Azure OpenAI integration
        raise NotImplementedError(
            "Azure OpenAI provider is not yet implemented. "
            "This is a placeholder for future integration."
        )

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


def get_provider(
    provider_name: str,
    api_key: str = "",
    azure_endpoint: str = "",
    azure_deployment: str = "",
) -> AIProvider:
    """Factory function to create an AI provider.

    Parameters
    ----------
    provider_name : str
        Name of the provider ("gemini" or "azure").
    api_key : str
        API key for the provider.
    azure_endpoint : str
        Azure OpenAI endpoint URL (only for Azure provider).
    azure_deployment : str
        Azure OpenAI deployment name (only for Azure provider).

    Returns
    -------
    AIProvider
        An instance of the selected provider.
    """
    if provider_name == "gemini":
        return GeminiProvider(api_key=api_key)
    elif provider_name == "azure":
        return AzureOpenAIProvider(
            api_key=api_key,
            endpoint=azure_endpoint,
            deployment=azure_deployment,
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}")


def _format_stats_for_prompt(summary_stats_df: pd.DataFrame) -> str:
    """Format summary statistics DataFrame as text for the AI prompt."""
    if summary_stats_df is None or summary_stats_df.empty:
        return "Nenhuma estatística disponível."
    return summary_stats_df.to_string()


def _format_regression_for_prompt(trend_regression: dict) -> str:
    """Format trend regression results as text for the AI prompt."""
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


def generate_ai_analysis(
    provider: AIProvider,
    trend_regression: dict,
    summary_stats_df: pd.DataFrame,
    session_name: str = "",
) -> dict:
    """Generate AI analysis text for each report section.

    Uses a single API call with a combined prompt to minimize quota usage.

    Parameters
    ----------
    provider : AIProvider
        The AI provider to use for text generation.
    trend_regression : dict
        Regression results per delta column with keys slope_per_month,
        r_squared, p_value, n_points.
    summary_stats_df : pandas.DataFrame
        Summary statistics dataframe with delta values.
    session_name : str, optional
        Name of the evaluation session for context.

    Returns
    -------
    dict
        Dictionary with keys "trend", "performance", "stats" containing
        the generated analysis text for each section.
    """
    regression_text = _format_regression_for_prompt(trend_regression)
    stats_text = _format_stats_for_prompt(summary_stats_df)
    session_context = (
        f"Sessão de avaliação: {session_name}\n" if session_name else ""
    )

    prompt = _COMBINED_PROMPT_TEMPLATE.format(
        session_context=session_context,
        regression_text=regression_text,
        stats_text=stats_text,
        separator=_SECTION_SEPARATOR,
    )

    response = provider.generate(prompt)

    sections = response.split(_SECTION_SEPARATOR)
    keys = ["trend", "performance", "stats"]
    results = {}
    for i, key in enumerate(keys):
        results[key] = sections[i].strip() if i < len(sections) else ""

    return results
