# STUB: replaced by Unit 11 (apps.integrations.pi_client) at merge time.
"""Offline PI client fallback - returns empty DataFrame."""

import pandas as pd


def is_pi_available() -> bool:
    """Return True when pandaspi is importable."""
    try:
        import pandaspi  # noqa: F401

        return True
    except ImportError:
        return False


def fetch_pi_data(tag_map: dict, start, end, **opts) -> pd.DataFrame:
    """Offline fallback that returns an empty DataFrame."""
    return pd.DataFrame()
