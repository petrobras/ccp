"""Forms for the back-to-back compressor page.

Each ``PointForm`` carries the parameters required by a single compressor
performance point, matching the Streamlit widgets from
``ccp/app/pages/2_back_to_back.py``. The full page uses three groups:

* :class:`GuaranteePointForm` — shared guarantee point per section.
* :class:`FirstSectionTestPointForm` — ×6 in a :class:`formset_factory`.
* :class:`SecondSectionTestPointForm` — ×6 in a :class:`formset_factory`.

All numeric fields are exposed as ``CharField`` so that the legacy decimal
separator check from the Streamlit version still triggers on commas, and so
empty strings survive the round-trip (the compute service treats blanks as
"no data" rather than zero).
"""

from __future__ import annotations

from django import forms
from django.forms import formset_factory

try:  # pragma: no cover - Unit 2 replaces these at merge time
    from apps.core.services.unit_helpers import (
        AREA_UNITS,
        DENSITY_UNITS,
        FLOW_UNITS,
        HEAD_UNITS,
        LENGTH_UNITS,
        OIL_FLOW_UNITS,
        POWER_UNITS,
        PRESSURE_UNITS,
        SPECIFIC_HEAT_UNITS,
        SPEED_UNITS,
        TEMPERATURE_UNITS,
    )
except Exception:  # noqa: BLE001
    FLOW_UNITS = ["kg/h", "kg/s", "m³/h"]
    PRESSURE_UNITS = ["bar", "Pa", "kPa", "MPa", "psi"]
    TEMPERATURE_UNITS = ["degK", "degC", "degF"]
    HEAD_UNITS = ["kJ/kg", "J/kg"]
    POWER_UNITS = ["kW", "W", "hp"]
    SPEED_UNITS = ["rpm", "Hz"]
    LENGTH_UNITS = ["m", "mm", "in"]
    OIL_FLOW_UNITS = ["l/min", "m³/h"]
    DENSITY_UNITS = ["kg/m³", "g/cm³"]
    SPECIFIC_HEAT_UNITS = ["kJ/kg/degK"]
    AREA_UNITS = ["m²", "mm²"]

try:
    from apps.core.services.polytropic_methods import POLYTROPIC_METHODS
except Exception:  # noqa: BLE001
    POLYTROPIC_METHODS = {
        "Sandberg-Colby": "sandberg_colby",
        "Huntington": "huntington",
        "Schultz": "schultz",
    }

try:
    from apps.core.services.gas_composition import FLUID_LIST
except Exception:  # noqa: BLE001
    FLUID_LIST = ["methane", "ethane", "propane", "nitrogen", "carbon dioxide"]


# Parameters shared by the guarantee / first / second section forms. Each
# entry is ``(field_name, label, unit_choices, help_text)``.
GUARANTEE_PARAMETERS = [
    ("flow", "Flow", FLOW_UNITS, "Mass or volumetric flow at the compressor flange."),
    ("suction_pressure", "Suction Pressure", PRESSURE_UNITS, ""),
    ("suction_temperature", "Suction Temperature", TEMPERATURE_UNITS, ""),
    ("discharge_pressure", "Discharge Pressure", PRESSURE_UNITS, ""),
    ("discharge_temperature", "Discharge Temperature", TEMPERATURE_UNITS, ""),
    ("power", "Power (gas)", POWER_UNITS, ""),
    ("power_shaft", "Power (shaft)", POWER_UNITS, ""),
    ("speed", "Speed", SPEED_UNITS, ""),
    ("head", "Head", HEAD_UNITS, ""),
    ("eff", "Efficiency", ["dimensionless"], ""),
    ("b", "Impeller outlet width b", LENGTH_UNITS, ""),
    ("D", "Impeller outer diameter D", LENGTH_UNITS, ""),
    ("surface_roughness", "Surface Roughness", LENGTH_UNITS, ""),
    ("casing_area", "Casing Area", AREA_UNITS, ""),
]

FIRST_SECTION_TEST_PARAMETERS = [
    ("flow", "Flow", FLOW_UNITS),
    ("suction_pressure", "Suction Pressure", PRESSURE_UNITS),
    ("suction_temperature", "Suction Temperature", TEMPERATURE_UNITS),
    ("discharge_pressure", "Discharge Pressure", PRESSURE_UNITS),
    ("discharge_temperature", "Discharge Temperature", TEMPERATURE_UNITS),
    ("casing_delta_T", "Casing ΔT", TEMPERATURE_UNITS),
    ("speed", "Speed", SPEED_UNITS),
    ("balance_line_flow_m", "Balance line flow", FLOW_UNITS),
    ("end_seal_upstream_pressure", "End seal upstream pressure", PRESSURE_UNITS),
    ("end_seal_upstream_temperature", "End seal upstream temperature", TEMPERATURE_UNITS),
    ("div_wall_flow_m", "Division wall flow", FLOW_UNITS),
    ("div_wall_upstream_pressure", "Division wall upstream pressure", PRESSURE_UNITS),
    ("div_wall_upstream_temperature", "Division wall upstream temperature", TEMPERATURE_UNITS),
    ("first_section_discharge_flow_m", "First section discharge flow", FLOW_UNITS),
    ("seal_gas_flow_m", "Seal gas flow", FLOW_UNITS),
    ("seal_gas_temperature", "Seal gas temperature", TEMPERATURE_UNITS),
    ("oil_flow_journal_bearing_de", "Oil flow journal bearing DE", OIL_FLOW_UNITS),
    ("oil_flow_journal_bearing_nde", "Oil flow journal bearing NDE", OIL_FLOW_UNITS),
    ("oil_flow_thrust_bearing_nde", "Oil flow thrust bearing NDE", OIL_FLOW_UNITS),
    ("oil_inlet_temperature", "Oil inlet temperature", TEMPERATURE_UNITS),
    ("oil_outlet_temperature_de", "Oil outlet temperature DE", TEMPERATURE_UNITS),
    ("oil_outlet_temperature_nde", "Oil outlet temperature NDE", TEMPERATURE_UNITS),
]

SECOND_SECTION_TEST_PARAMETERS = [
    ("flow", "Flow", FLOW_UNITS),
    ("suction_pressure", "Suction Pressure", PRESSURE_UNITS),
    ("suction_temperature", "Suction Temperature", TEMPERATURE_UNITS),
    ("discharge_pressure", "Discharge Pressure", PRESSURE_UNITS),
    ("discharge_temperature", "Discharge Temperature", TEMPERATURE_UNITS),
    ("casing_delta_T", "Casing ΔT", TEMPERATURE_UNITS),
    ("speed", "Speed", SPEED_UNITS),
    ("balance_line_flow_m", "Balance line flow", FLOW_UNITS),
    ("seal_gas_flow_m", "Seal gas flow", FLOW_UNITS),
    ("oil_flow_journal_bearing_de", "Oil flow journal bearing DE", OIL_FLOW_UNITS),
    ("oil_flow_journal_bearing_nde", "Oil flow journal bearing NDE", OIL_FLOW_UNITS),
    ("oil_flow_thrust_bearing_nde", "Oil flow thrust bearing NDE", OIL_FLOW_UNITS),
    ("oil_inlet_temperature", "Oil inlet temperature", TEMPERATURE_UNITS),
    ("oil_outlet_temperature_de", "Oil outlet temperature DE", TEMPERATURE_UNITS),
    ("oil_outlet_temperature_nde", "Oil outlet temperature NDE", TEMPERATURE_UNITS),
]

LEAKAGE_FIELDS = {
    "balance_line_flow_m",
    "end_seal_upstream_pressure",
    "end_seal_upstream_temperature",
    "div_wall_flow_m",
    "div_wall_upstream_pressure",
    "div_wall_upstream_temperature",
    "first_section_discharge_flow_m",
}
SEAL_GAS_FIELDS = {"seal_gas_flow_m", "seal_gas_temperature"}


def _add_parameter_fields(form, parameters):
    for name, label, unit_choices, *rest in parameters:
        help_text = rest[0] if rest else ""
        form.fields[f"{name}_value"] = forms.CharField(
            required=False,
            label=label,
            help_text=help_text,
            widget=forms.TextInput(attrs={"class": "ccp-value"}),
        )
        form.fields[f"{name}_units"] = forms.ChoiceField(
            required=False,
            choices=[(u, u) for u in unit_choices],
            label=f"{label} units",
            widget=forms.Select(attrs={"class": "ccp-units"}),
        )


class GasCompositionForm(forms.Form):
    """Placeholder gas-composition selector.

    The real form lives in Unit 4; this version keeps the public API
    compatible so the page can render a sensible dropdown in isolation.
    """

    gas_name = forms.CharField(
        required=False, initial="gas_0", label="Gas Selection"
    )


class GuaranteePointForm(forms.Form):
    """Guarantee point for a single section (first or second)."""

    section = forms.ChoiceField(
        choices=[("section_1", "First Section"), ("section_2", "Second Section")],
        widget=forms.HiddenInput,
    )
    gas_name = forms.CharField(required=False, initial="gas_0")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_parameter_fields(self, GUARANTEE_PARAMETERS)


class FirstSectionTestPointForm(forms.Form):
    """A single first-section test point."""

    gas_name = forms.CharField(required=False, initial="gas_0")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_parameter_fields(self, FIRST_SECTION_TEST_PARAMETERS)


class SecondSectionTestPointForm(forms.Form):
    """A single second-section test point."""

    gas_name = forms.CharField(required=False, initial="gas_0")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _add_parameter_fields(self, SECOND_SECTION_TEST_PARAMETERS)


FirstSectionTestPointFormSet = formset_factory(
    FirstSectionTestPointForm, extra=6, max_num=6
)
SecondSectionTestPointFormSet = formset_factory(
    SecondSectionTestPointForm, extra=6, max_num=6
)


class SidebarOptionsForm(forms.Form):
    """Options checkboxes + ambient pressure + polytropic method."""

    reynolds_correction = forms.BooleanField(required=False, initial=True)
    casing_heat_loss = forms.BooleanField(required=False, initial=True)
    bearing_mechanical_losses = forms.BooleanField(required=False, initial=True)
    calculate_leakages = forms.BooleanField(required=False, initial=True)
    seal_gas_flow = forms.BooleanField(required=False, initial=True)
    variable_speed = forms.BooleanField(required=False, initial=True)
    show_points = forms.BooleanField(required=False, initial=True)

    ambient_pressure_magnitude = forms.CharField(required=False, initial="1.01325")
    ambient_pressure_unit = forms.ChoiceField(
        required=False,
        choices=[(u, u) for u in PRESSURE_UNITS],
        initial="bar",
    )
    polytropic_method = forms.ChoiceField(
        required=False,
        choices=[(k, k) for k in POLYTROPIC_METHODS],
        initial="Sandberg-Colby",
    )

    oil_specific_heat = forms.BooleanField(required=False, initial=False)
    oil_specific_heat_value = forms.CharField(required=False, initial="2.0")
    oil_density_value = forms.CharField(required=False, initial="860")
    oil_iso = forms.BooleanField(required=False, initial=False)
    oil_iso_classification = forms.ChoiceField(
        required=False,
        choices=[("VG 32", "VG 32"), ("VG 46", "VG 46")],
        initial="VG 32",
    )

    def clean_ambient_pressure_magnitude(self):
        value = self.cleaned_data.get("ambient_pressure_magnitude") or "1.01325"
        if "," in value:
            raise forms.ValidationError("Please use '.' as decimal separator")
        return value


class CurveUploadForm(forms.Form):
    """Background curve upload for a single section / curve type."""

    section = forms.ChoiceField(choices=[("sec1", "sec1"), ("sec2", "sec2")])
    curve = forms.ChoiceField(
        choices=[
            ("head", "head"),
            ("eff", "eff"),
            ("discharge_pressure", "discharge_pressure"),
            ("power", "power"),
        ]
    )
    image = forms.FileField(required=False)
    x_lower = forms.CharField(required=False)
    x_upper = forms.CharField(required=False)
    y_lower = forms.CharField(required=False)
    y_upper = forms.CharField(required=False)
    x_units = forms.CharField(required=False)
    y_units = forms.CharField(required=False)
