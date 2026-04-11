"""Unit choices and conversion helpers.

All unit lists are ported from ``ccp/app/common.py`` so forms in the Django
pages render exactly the same dropdowns as the Streamlit originals. Unit
conversions always flow through :func:`ccp.Q_` — never hand-rolled arithmetic.
"""

from __future__ import annotations

import ccp

FLOW_M_UNITS: list[str] = ["kg/h", "kg/min", "kg/s", "lbm/h", "lbm/min", "lbm/s"]
FLOW_V_UNITS: list[str] = ["m³/h", "m³/min", "m³/s"]
FLOW_UNITS: list[str] = FLOW_M_UNITS + FLOW_V_UNITS
PRESSURE_UNITS: list[str] = [
    "bar",
    "kgf/cm²",
    "barg",
    "Pa",
    "kPa",
    "MPa",
    "psi",
    "mmH2O",
]
TEMPERATURE_UNITS: list[str] = ["degK", "degC", "degF", "degR"]
HEAD_UNITS: list[str] = ["kJ/kg", "J/kg", "m*g0", "ft"]
POWER_UNITS: list[str] = ["kW", "hp", "W", "Btu/h", "MW"]
SPEED_UNITS: list[str] = ["rpm", "Hz"]
LENGTH_UNITS: list[str] = ["m", "mm", "ft", "in"]
SPECIFIC_HEAT_UNITS: list[str] = [
    "kJ/kg/degK",
    "J/kg/degK",
    "cal/g/degC",
    "Btu/lb/degF",
]
OIL_FLOW_UNITS: list[str] = ["l/min", "l/h", "gal/min", "m³/h", "m³/min", "m³/s"]
DENSITY_UNITS: list[str] = ["kg/m³", "g/cm³", "g/ml", "g/l"]
AREA_UNITS: list[str] = ["m²", "mm²", "ft²", "in²"]
OIL_ISO_OPTIONS: list[str] = ["VG 32", "VG 46"]


def convert(value: float, src: str, dst: str) -> float:
    """Convert a scalar magnitude from *src* units to *dst* units.

    Parameters
    ----------
    value : float
        Magnitude expressed in *src* units.
    src : str
        Source unit string understood by ``pint`` / ``ccp.Q_``.
    dst : str
        Destination unit string.

    Returns
    -------
    float
        ``value`` converted to *dst*, as a bare float.
    """
    return float(ccp.Q_(value, src).to(dst).magnitude)
