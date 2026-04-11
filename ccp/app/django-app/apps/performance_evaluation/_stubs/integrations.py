# STUB: replaced by Unit 11 at merge time
"""Offline fallbacks for :mod:`apps.integrations.pi_client` and
:mod:`apps.integrations.ai_analysis`.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def is_pi_available() -> bool:
    """Return ``False`` when :mod:`pandaspi` is not installed."""
    try:
        import pandaspi  # noqa: F401

        return True
    except ImportError:
        return False


def fetch_pi_data(
    tag_map: dict[str, Any],
    start: Any = None,
    end: Any = None,
    **opts: Any,
) -> pd.DataFrame:
    """Return an empty :class:`pandas.DataFrame` when PI is unreachable."""
    return pd.DataFrame()


def generate_ai_analysis(
    evaluation: Any = None,
    *,
    provider: str = "gemini",
    api_key: str | None = None,
    **_: Any,
) -> str:
    """Return an empty string when no AI provider is configured."""
    return ""
