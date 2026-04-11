"""Static parameter metadata for compressor input forms.

Ported from the ``parameters_map`` dict in ``ccp/app/common.py``. Each entry
carries the UI label, the list of valid unit strings, an optional help text,
and an optional default magnitude. Defaults are left as ``None`` where the
Streamlit original did not specify one — views should supply values or prompt
the user.
"""

from __future__ import annotations

from apps.core.services.unit_helpers import (
    AREA_UNITS,
    DENSITY_UNITS,
    FLOW_M_UNITS,
    FLOW_UNITS,
    FLOW_V_UNITS,
    HEAD_UNITS,
    LENGTH_UNITS,
    OIL_FLOW_UNITS,
    POWER_UNITS,
    PRESSURE_UNITS,
    SPECIFIC_HEAT_UNITS,
    SPEED_UNITS,
    TEMPERATURE_UNITS,
)


def _entry(
    label: str,
    units: list[str],
    help_text: str | None = None,
    default: float | None = None,
) -> dict:
    """Build a parameter map entry with a uniform shape.

    Parameters
    ----------
    label : str
        UI label shown next to the input widget.
    units : list of str
        Valid pint-compatible unit strings.
    help_text : str, optional
        Tooltip / help text.
    default : float, optional
        Default magnitude expressed in ``units[0]``.

    Returns
    -------
    dict
        A dictionary with keys ``label``, ``units``, ``help``, ``default``.
    """
    return {
        "label": label,
        "units": list(units),
        "help": help_text,
        "default": default,
    }


PARAMETERS: dict[str, dict] = {
    "flow": _entry(
        "Flow",
        FLOW_UNITS,
        "Flow can be mass flow or volumetric flow depending on the selected unit.",
    ),
    "flow_v": _entry("Volumetric Flow", FLOW_V_UNITS, "Volumetric flow."),
    "suction_pressure": _entry("Suction Pressure", PRESSURE_UNITS),
    "suction_temperature": _entry("Suction Temperature", TEMPERATURE_UNITS),
    "discharge_pressure": _entry("Discharge Pressure", PRESSURE_UNITS),
    "discharge_temperature": _entry("Discharge Temperature", TEMPERATURE_UNITS),
    "casing_delta_T": _entry(
        "Casing ΔT",
        TEMPERATURE_UNITS,
        "Temperature difference between the casing and the ambient temperature.",
    ),
    "speed": _entry("Speed", SPEED_UNITS),
    "balance_line_flow_m": _entry("Balance Line Flow", FLOW_M_UNITS),
    "end_seal_upstream_pressure": _entry(
        "Pressure Upstream End Seal",
        PRESSURE_UNITS,
        "Second section suction pressure.",
    ),
    "end_seal_upstream_temperature": _entry(
        "Temperature Upstream End Seal",
        TEMPERATURE_UNITS,
        "Second section suction temperature.",
    ),
    "div_wall_flow_m": _entry(
        "Division Wall Flow",
        FLOW_M_UNITS,
        "Flow through the division wall if measured. Otherwise it is "
        "calculated from the First Section Discharge Flow.",
    ),
    "div_wall_upstream_pressure": _entry(
        "Pressure Upstream Division Wall",
        PRESSURE_UNITS,
        "Second section discharge pressure.",
    ),
    "div_wall_upstream_temperature": _entry(
        "Temperature Upstream Division Wall",
        TEMPERATURE_UNITS,
        "Second section discharge temperature.",
    ),
    "first_section_discharge_flow_m": _entry(
        "First Section Discharge Flow",
        FLOW_M_UNITS,
        "If the Division Wall Flow is not measured, we use this value to calculate it.",
    ),
    "seal_gas_flow_m": _entry("Seal Gas Flow", FLOW_M_UNITS),
    "seal_gas_temperature": _entry("Seal Gas Temperature", TEMPERATURE_UNITS),
    "oil_flow_journal_bearing_de": _entry(
        "Oil Flow Journal Bearing DE", OIL_FLOW_UNITS
    ),
    "oil_flow_journal_bearing_nde": _entry(
        "Oil Flow Journal Bearing NDE", OIL_FLOW_UNITS
    ),
    "oil_flow_thrust_bearing_nde": _entry(
        "Oil Flow Thrust Bearing NDE", OIL_FLOW_UNITS
    ),
    "oil_inlet_temperature": _entry("Oil Inlet Temperature", TEMPERATURE_UNITS),
    "oil_outlet_temperature_de": _entry("Oil Outlet Temperature DE", TEMPERATURE_UNITS),
    "oil_outlet_temperature_nde": _entry(
        "Oil Outlet Temperature NDE", TEMPERATURE_UNITS
    ),
    "head": _entry("Head", HEAD_UNITS),
    "eff": _entry("Efficiency", [""]),
    "power": _entry("Gas Power", POWER_UNITS),
    "power_shaft": _entry("Shaft Power", POWER_UNITS),
    "b": _entry("First Impeller Width", LENGTH_UNITS),
    "D": _entry("First Impeller Diameter", LENGTH_UNITS),
    "surface_roughness": _entry(
        "Surface Roughness",
        LENGTH_UNITS + ["microm"],
        "Mean surface roughness of the gas path.",
    ),
    "casing_area": _entry("Casing Area", AREA_UNITS),
    "outer_diameter_fo": _entry(
        "Outer Diameter",
        ["mm", "m", "ft", "in"],
        "Outer diameter of orifice plate.",
    ),
    "inner_diameter_fo": _entry(
        "Inner Diameter",
        ["mm", "m", "ft", "in"],
        "Inner diameter of orifice plate.",
    ),
    "upstream_pressure_fo": _entry(
        "Upstream Pressure", PRESSURE_UNITS, "Upstream pressure of orifice plate."
    ),
    "upstream_temperature_fo": _entry(
        "Upstream Temperature",
        TEMPERATURE_UNITS,
        "Upstream temperature of orifice plate.",
    ),
    "pressure_drop_fo": _entry(
        "Pressure Drop", PRESSURE_UNITS, "Pressure drop across orifice plate."
    ),
    "tappings_fo": _entry(
        "Tappings",
        ["flange", "corner", "D D/2"],
        "Pressure tappings type.",
    ),
    "mass_flow_fo": _entry("Mass Flow (Result)", ["kg/h", "lbm/h", "kg/s", "lbm/s"]),
    "oil_specific_heat": _entry("Oil Specific Heat", SPECIFIC_HEAT_UNITS),
    "oil_density": _entry("Oil Density", DENSITY_UNITS),
}


POINT_KEYS: tuple[str, ...] = (
    "guarantee_point",
    "test_point_1",
    "test_point_2",
    "test_point_3",
    "test_point_4",
    "test_point_5",
    "test_point_6",
)


def get_parameter(name: str) -> dict:
    """Look up a parameter definition by key.

    Parameters
    ----------
    name : str
        Parameter name (e.g. ``"suction_pressure"``).

    Returns
    -------
    dict
        The parameter entry. A ``KeyError`` is raised if *name* is unknown.
    """
    return PARAMETERS[name]
