"""Django forms for the straight-through compressor page.

Mirror the input widgets of ``ccp/app/pages/1_straight_through.py``. Field
sets are kept intentionally simple — views read ``request.POST`` directly and
hand a flat dict to :func:`apps.straight_through.services.run_straight_through`,
so these forms exist primarily for validation, defaults and the HTMX upload
endpoint.
"""

from __future__ import annotations

from django import forms

try:
    from apps.core.services.unit_helpers import (
        FLOW_UNITS,
        HEAD_UNITS,
        LENGTH_UNITS,
        POWER_UNITS,
        PRESSURE_UNITS,
        SPEED_UNITS,
        TEMPERATURE_UNITS,
    )
except Exception:  # pragma: no cover - fall back to literal defaults
    FLOW_UNITS = ["kg/h", "kg/s", "m³/h", "m³/s"]
    PRESSURE_UNITS = ["bar", "Pa", "kPa", "MPa", "psi"]
    TEMPERATURE_UNITS = ["degK", "degC", "degF", "degR"]
    SPEED_UNITS = ["rpm", "Hz"]
    HEAD_UNITS = ["kJ/kg", "J/kg"]
    POWER_UNITS = ["kW", "W", "hp"]
    LENGTH_UNITS = ["mm", "m", "in"]

try:
    from apps.core.services.gas_composition import FLUID_LIST  # type: ignore
except Exception:  # pragma: no cover
    from apps.straight_through._stubs.gas_composition import FLUID_LIST


GAS_COMPONENT_COUNT = 6


class GasCompositionForm(forms.Form):
    """Six-component gas composition form.

    Mirrors the Streamlit ``gas_selection_form`` widget: a gas name plus up to
    six (component, molar fraction) pairs.
    """

    gas_name = forms.CharField(required=False, initial="Gas 1")

    def composition(self) -> dict[str, float]:
        """Return a ``{component: fraction}`` dict from cleaned data."""
        out: dict[str, float] = {}
        for i in range(GAS_COMPONENT_COUNT):
            comp = self.cleaned_data.get(f"component_{i}")
            frac = self.cleaned_data.get(f"fraction_{i}")
            if comp and frac:
                out[comp] = float(frac)
        return out


for _i in range(GAS_COMPONENT_COUNT):
    GasCompositionForm.base_fields[f"component_{_i}"] = forms.ChoiceField(
        choices=[(f, f) for f in FLUID_LIST],
        required=False,
    )
    GasCompositionForm.base_fields[f"fraction_{_i}"] = forms.FloatField(
        required=False, min_value=0.0
    )
del _i


class SidebarOptionsForm(forms.Form):
    """Toggles shown in the Streamlit sidebar "Options" expander."""

    reynolds_correction = forms.BooleanField(required=False, initial=True)
    casing_heat_loss = forms.BooleanField(required=False, initial=True)
    bearing_mechanical_losses = forms.BooleanField(required=False, initial=True)
    calculate_leakages = forms.BooleanField(required=False, initial=True)
    seal_gas_flow = forms.BooleanField(required=False, initial=True)
    variable_speed = forms.BooleanField(required=False, initial=True)
    show_points = forms.BooleanField(required=False, initial=False)
    polytropic_method = forms.ChoiceField(
        required=False,
        choices=[
            ("Sandberg-Colby", "Sandberg-Colby"),
            ("Huntington", "Huntington"),
            ("Mallen-Saville", "Mallen-Saville"),
            ("Schultz", "Schultz"),
        ],
        initial="Sandberg-Colby",
    )
    ambient_pressure = forms.FloatField(required=False, initial=1.01325)
    ambient_pressure_unit = forms.ChoiceField(
        required=False,
        choices=[(u, u) for u in PRESSURE_UNITS],
        initial="bar",
    )


class GuaranteePointForm(forms.Form):
    """Data sheet (guarantee) point inputs."""

    flow = forms.CharField(required=False)
    flow_unit = forms.ChoiceField(choices=[(u, u) for u in FLOW_UNITS], required=False, initial="kg/h")
    suction_pressure = forms.CharField(required=False)
    suction_pressure_unit = forms.ChoiceField(choices=[(u, u) for u in PRESSURE_UNITS], required=False, initial="bar")
    suction_temperature = forms.CharField(required=False)
    suction_temperature_unit = forms.ChoiceField(choices=[(u, u) for u in TEMPERATURE_UNITS], required=False, initial="degK")
    discharge_pressure = forms.CharField(required=False)
    discharge_pressure_unit = forms.ChoiceField(choices=[(u, u) for u in PRESSURE_UNITS], required=False, initial="bar")
    discharge_temperature = forms.CharField(required=False)
    discharge_temperature_unit = forms.ChoiceField(choices=[(u, u) for u in TEMPERATURE_UNITS], required=False, initial="degK")
    speed = forms.CharField(required=False)
    speed_unit = forms.ChoiceField(choices=[(u, u) for u in SPEED_UNITS], required=False, initial="rpm")
    power = forms.CharField(required=False)
    power_unit = forms.ChoiceField(choices=[(u, u) for u in POWER_UNITS], required=False, initial="kW")
    power_shaft = forms.CharField(required=False)
    head = forms.CharField(required=False)
    head_unit = forms.ChoiceField(choices=[(u, u) for u in HEAD_UNITS], required=False, initial="kJ/kg")
    eff = forms.CharField(required=False)
    b = forms.CharField(required=False)
    b_unit = forms.ChoiceField(choices=[(u, u) for u in LENGTH_UNITS], required=False, initial="mm")
    D = forms.CharField(required=False)
    D_unit = forms.ChoiceField(choices=[(u, u) for u in LENGTH_UNITS], required=False, initial="mm")
    surface_roughness = forms.CharField(required=False)
    casing_area = forms.CharField(required=False)


class TestPointForm(forms.Form):
    """A single test point row (1..6).

    Fields mirror :data:`apps.straight_through.services.TEST_PARAMETERS`.
    """

    index = forms.IntegerField(min_value=1, max_value=6)
    flow = forms.CharField(required=False)
    suction_pressure = forms.CharField(required=False)
    suction_temperature = forms.CharField(required=False)
    discharge_pressure = forms.CharField(required=False)
    discharge_temperature = forms.CharField(required=False)
    casing_delta_T = forms.CharField(required=False)
    speed = forms.CharField(required=False)
    balance_line_flow_m = forms.CharField(required=False)
    seal_gas_flow_m = forms.CharField(required=False)
    seal_gas_temperature = forms.CharField(required=False)
    oil_flow_journal_bearing_de = forms.CharField(required=False)
    oil_flow_journal_bearing_nde = forms.CharField(required=False)
    oil_flow_thrust_bearing_nde = forms.CharField(required=False)
    oil_inlet_temperature = forms.CharField(required=False)
    oil_outlet_temperature_de = forms.CharField(required=False)
    oil_outlet_temperature_nde = forms.CharField(required=False)


class CurveUploadForm(forms.Form):
    """PNG curve upload with x/y range limits."""

    CURVE_CHOICES = [
        ("head", "Head"),
        ("eff", "Efficiency"),
        ("discharge_pressure", "Discharge Pressure"),
        ("power", "Power"),
    ]
    curve = forms.ChoiceField(choices=CURVE_CHOICES)
    image = forms.FileField()
    x_lower = forms.FloatField(required=False)
    x_upper = forms.FloatField(required=False)
    y_lower = forms.FloatField(required=False)
    y_upper = forms.FloatField(required=False)
    x_units = forms.CharField(required=False)
    y_units = forms.CharField(required=False)
