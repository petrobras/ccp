# STUB: replaced by Unit 2 at merge time
"""Minimal ``ccp_service`` used when ``apps.core.services.ccp_service`` is absent.

Delegates to the ``ccp`` library. Keeps the same public signatures documented
in the migration plan so views can switch to the real implementation without
code changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ccp


def build_gas_state(composition: dict, p, T) -> ccp.State:
    """Build a :class:`ccp.State` from a composition mapping and ``pint`` quantities.

    Parameters
    ----------
    composition : dict
        Component-to-molar-fraction mapping.
    p : ccp.Q_
        Suction pressure.
    T : ccp.Q_
        Suction temperature.

    Returns
    -------
    ccp.State
        Thermodynamic state describing the suction conditions.
    """
    return ccp.State(p=p, T=T, fluid=composition)


def load_impeller_from_engauge_csv(
    suction_state: ccp.State,
    curve_name: str,
    curve_path: Path,
    **kwargs: Any,
) -> ccp.Impeller:
    """Load an :class:`ccp.Impeller` from Engauge-digitized CSVs.

    Parameters
    ----------
    suction_state : ccp.State
        Suction state for the original curves.
    curve_name : str
        Base name of the curve files (without the ``-head`` / ``-eff`` suffix).
    curve_path : pathlib.Path
        Directory containing the CSV files.
    **kwargs
        Forwarded to :meth:`ccp.Impeller.load_from_engauge_csv`.

    Returns
    -------
    ccp.Impeller
        The loaded impeller.
    """
    return ccp.Impeller.load_from_engauge_csv(
        suc=suction_state,
        curve_name=curve_name,
        curve_path=curve_path,
        **kwargs,
    )


def convert_impeller(
    original_impeller: ccp.Impeller,
    suction_state: ccp.State,
    find: str = "speed",
    speed: Any = "same",
) -> ccp.Impeller:
    """Convert an impeller to new suction conditions.

    Parameters
    ----------
    original_impeller : ccp.Impeller
        Impeller loaded from the original curves.
    suction_state : ccp.State
        Target suction state.
    find : str, optional
        Conversion strategy passed to :meth:`ccp.Impeller.convert_from`.
    speed : str or None, optional
        ``"same"`` to keep the original speed, ``None`` to recompute it.

    Returns
    -------
    ccp.Impeller
        The converted impeller.
    """
    return ccp.Impeller.convert_from(
        original_impeller=original_impeller,
        suc=suction_state,
        find=find,
        speed=speed,
    )
