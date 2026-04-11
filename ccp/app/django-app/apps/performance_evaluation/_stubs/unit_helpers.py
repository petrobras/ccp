# STUB: replaced by Unit 2 (apps.core.services.unit_helpers) at merge time.
"""Minimal unit choice lists used by Unit 8 forms."""

FLOW_UNITS = [
    "kg/s",
    "kg/h",
    "lbm/h",
    "lbm/min",
    "m**3/s",
    "m**3/h",
    "m³/h",
    "m³/s",
    "ft**3/s",
    "ft**3/min",
    "MMSCFD",
]

PRESSURE_UNITS = ["Pa", "kPa", "bar", "bar_g", "psi", "kgf/cm**2", "atm"]
TEMPERATURE_UNITS = ["K", "degC", "degF", "degR"]
HEAD_UNITS = ["J/kg", "kJ/kg", "m", "ft"]
POWER_UNITS = ["W", "kW", "MW", "hp"]
SPEED_UNITS = ["rpm", "Hz", "rad/s"]
LENGTH_UNITS = ["m", "mm", "cm", "in", "ft"]
OIL_FLOW_UNITS = ["l/min", "m**3/h", "gpm"]
DENSITY_UNITS = ["kg/m**3", "lbm/ft**3"]
SPECIFIC_HEAT_UNITS = ["J/(kg*K)", "kJ/(kg*K)"]


def convert(value, src, dst):
    """Convert ``value`` from ``src`` to ``dst`` using ``ccp.Q_``."""
    import ccp

    return ccp.Q_(value, src).to(dst).m
