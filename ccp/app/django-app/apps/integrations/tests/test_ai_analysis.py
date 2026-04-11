"""Tests for :mod:`apps.integrations.ai_analysis`."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from apps.integrations import ai_analysis


def test_imports_without_google_generativeai(monkeypatch):
    """Module must remain importable when google.generativeai is absent."""
    monkeypatch.setitem(sys.modules, "google.generativeai", None)
    import importlib

    reloaded = importlib.reload(ai_analysis)
    assert hasattr(reloaded, "generate_ai_analysis")


def test_generate_ai_analysis_returns_string_when_no_api_key():
    """Without an API key the function returns the fallback string."""
    result = ai_analysis.generate_ai_analysis(SimpleNamespace(), api_key=None)
    assert isinstance(result, str)
    assert "indispon" in result.lower()


def test_generate_ai_analysis_returns_string_when_provider_missing(monkeypatch):
    """If the backing lib is unavailable, a Portuguese fallback is returned."""
    monkeypatch.setattr(ai_analysis, "_is_provider_available", lambda _: False)
    result = ai_analysis.generate_ai_analysis(
        SimpleNamespace(), provider="gemini", api_key="dummy"
    )
    assert isinstance(result, str)
    assert "gemini" in result


def test_generate_ai_analysis_unknown_provider(monkeypatch):
    monkeypatch.setattr(ai_analysis, "_is_provider_available", lambda _: True)
    result = ai_analysis.generate_ai_analysis(
        SimpleNamespace(), provider="does-not-exist", api_key="dummy"
    )
    assert isinstance(result, str)


def test_format_regression_empty():
    assert "Nenhum dado" in ai_analysis._format_regression_for_prompt({})
    assert "Nenhum dado" in ai_analysis._format_regression_for_prompt(None)


def test_format_regression_nonempty():
    data = {
        "delta_eff": {
            "slope_per_month": -0.123,
            "r_squared": 0.85,
            "p_value": 1.2e-4,
            "n_points": 30,
        }
    }
    text = ai_analysis._format_regression_for_prompt(data)
    assert "Delta Eficiência" in text
    assert "slope" in text


def test_format_stats_empty_dataframe():
    assert ai_analysis._format_stats_for_prompt(pd.DataFrame()) == (
        "Nenhuma estatística disponível."
    )
    assert ai_analysis._format_stats_for_prompt(None) == (
        "Nenhuma estatística disponível."
    )


def test_build_prompt_with_namespace():
    evaluation = SimpleNamespace(
        trend_regression={},
        summary_stats_df=pd.DataFrame(),
        session_name="Teste",
    )
    prompt = ai_analysis._build_prompt(evaluation)
    assert "Sessão de avaliação: Teste" in prompt
    assert ai_analysis._SECTION_SEPARATOR in prompt


def test_build_prompt_with_dict():
    prompt = ai_analysis._build_prompt({"trend_regression": None})
    assert ai_analysis._SECTION_SEPARATOR in prompt


def test_gemini_provider_raises_when_library_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "google.generativeai", None)
    with pytest.raises(ImportError):
        ai_analysis.GeminiProvider(api_key="dummy")
