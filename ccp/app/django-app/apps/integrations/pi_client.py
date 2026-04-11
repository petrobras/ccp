"""Thin wrapper around ``pandaspi`` with a graceful offline fallback.

``pandaspi`` is a Petrobras-internal package. Outside the corporate
network it is typically not installed, so every entry point in this
module wraps the import in ``try/except ImportError`` and returns
empty-but-well-shaped results when the dependency is missing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Mapping

import pandas as pd

logger = logging.getLogger(__name__)

_TAG_KEY_TO_COLUMN: dict[str, str] = {
    "suc_p_tag": "ps",
    "suc_T_tag": "Ts",
    "disch_p_tag": "pd",
    "disch_T_tag": "Td",
    "speed_tag": "speed",
    "flow_tag": "flow_v",
    "delta_p_tag": "delta_p",
    "p_downstream_tag": "p_downstream",
}

EXPECTED_COLUMNS: tuple[str, ...] = tuple(_TAG_KEY_TO_COLUMN.values())


def is_pi_available() -> bool:
    """Return whether the ``pandaspi`` dependency can be imported.

    Returns
    -------
    bool
        ``True`` if ``import pandaspi`` succeeds, ``False`` otherwise.
    """
    try:
        import pandaspi  # noqa: F401
    except ImportError:
        return False
    return True


def _format_pi_time(value: datetime) -> str:
    """Format a ``datetime`` the way PI Web API expects it."""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _empty_dataframe(tag_map: Mapping[str, Any] | None = None) -> pd.DataFrame:
    """Return an empty DataFrame with the expected canonical columns."""
    columns = list(EXPECTED_COLUMNS)
    if tag_map:
        for key in tag_map:
            if key not in columns and not key.endswith("_unit"):
                columns.append(key)
    return pd.DataFrame(columns=columns)


def _build_tags_list(tag_map: Mapping[str, Any]) -> tuple[list[str], dict[str, str]]:
    """Build the ``tags_list`` and ``rename_map`` from a ``tag_map``.

    The public form of ``tag_map`` used by the Streamlit app is a flat
    dictionary with keys like ``suc_p_tag``/``suc_p_unit`` mapped to the
    canonical column names in :data:`EXPECTED_COLUMNS`.
    """
    tags_list: list[str] = []
    rename_map: dict[str, str] = {}
    for tag_key, column in _TAG_KEY_TO_COLUMN.items():
        tag = tag_map.get(tag_key)
        if tag:
            tags_list.append(tag)
            rename_map[tag] = column
    return tags_list, rename_map


def fetch_pi_data(
    tag_map: Mapping[str, Any],
    start: datetime | None = None,
    end: datetime | None = None,
    *,
    auth_method: str = "kerberos",
    server_name: str | None = None,
) -> pd.DataFrame:
    """Fetch a historical PI dataset for the given tag mapping.

    When ``pandaspi`` is not installed, this function logs a warning and
    returns an empty DataFrame with the canonical column layout so
    callers can proceed without branching on import availability.

    Parameters
    ----------
    tag_map : Mapping
        Dictionary describing the PI tags to fetch. See
        :func:`_build_tags_list` for the expected keys.
    start, end : datetime, optional
        Inclusive time range. Defaults to the last hour.
    auth_method : str, optional
        Authentication method forwarded to ``pandaspi.SessionWeb``.
        Defaults to ``"kerberos"``.
    server_name : str, optional
        PI server name forwarded to ``pandaspi.SessionWeb``.

    Returns
    -------
    pandas.DataFrame
        Data indexed by timestamp, or an empty DataFrame when PI is
        unavailable.
    """
    if not is_pi_available():
        logger.warning(
            "pandaspi unavailable; returning empty PI dataframe (offline mode)."
        )
        return _empty_dataframe(tag_map)

    tags_list, rename_map = _build_tags_list(tag_map)
    if not tags_list:
        logger.warning("fetch_pi_data called with no PI tags configured.")
        return _empty_dataframe(tag_map)

    if end is None:
        end = datetime.now()
    if start is None:
        start = end - timedelta(hours=1)

    from pandaspi import SessionWeb  # type: ignore[import-not-found]

    session = SessionWeb(
        server_name=server_name or tag_map.get("pi_server_name", ""),
        login=tag_map.get("pi_login"),
        tags=tags_list,
        time_range=(_format_pi_time(start), _format_pi_time(end)),
        time_span="450s",
        authentication=tag_map.get("pi_auth_method", auth_method),
    )
    df = session.df.rename(columns=rename_map)
    return clean_pi_data(df)


def clean_pi_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a raw PI DataFrame for downstream ``ccp.Evaluation`` use.

    - Drops rows where any column contains a PI system/error ``dict``.
    - Strips timezone information from the index.
    - Coerces every column to numeric (non-numeric become NaN).

    Parameters
    ----------
    df : pandas.DataFrame
        Raw DataFrame coming from ``pandaspi.SessionWeb`` (already
        column-renamed to canonical names).

    Returns
    -------
    pandas.DataFrame
        A cleaned copy safe to hand to ``ccp.Evaluation``.

    Raises
    ------
    ValueError
        If all rows for a column are PI system errors, indicating the
        instrument is down.
    """
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    error_columns: dict[str, dict[str, Any]] = {}
    for col in df.columns:
        if df[col].dtype == object:
            is_dict_mask = df[col].apply(lambda v: isinstance(v, dict))
            if is_dict_mask.any():
                n_dicts = int(is_dict_mask.sum())
                sample = df[col][is_dict_mask].iloc[0]
                error_columns[col] = {
                    "count": n_dicts,
                    "total": len(df),
                    "sample": sample,
                }
                if n_dicts == len(df):
                    raise ValueError(
                        f"Tag mapped to column '{col}' returned only PI system "
                        f"values (instrument error). Sample value: {sample}. "
                        f"Please check if the instrument is operational."
                    )

    if error_columns:
        dict_row_mask = pd.Series(False, index=df.index)
        for col in error_columns:
            logger.warning(
                "Column '%s': %d/%d rows contain PI system/error values; dropping.",
                col,
                error_columns[col]["count"],
                error_columns[col]["total"],
            )
            dict_row_mask |= df[col].apply(lambda v: isinstance(v, dict))
        df = df[~dict_row_mask].copy()

    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
