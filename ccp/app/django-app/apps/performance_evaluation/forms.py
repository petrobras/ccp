"""Django forms for the Performance Evaluation config page.

Ports the input widgets from ``ccp/app/pages/4_performance_evaluation.py``
and ``ccp/app/common.py`` helpers (``design_cases_section``,
``tags_config_section``) to plain Django ``Form`` classes. Unit conversions
use ``pint`` via ``ccp.Q_`` - never manual arithmetic.
"""

from __future__ import annotations

from django import forms
from django.forms import formset_factory

from ._compat import gas_composition, unit_helpers

CASES = ["A", "B", "C", "D", "E"]
AUTH_CHOICES = [("kerberos", "Kerberos"), ("basic", "Basic")]
FLOW_METHOD_CHOICES = [("Direct", "Direct"), ("Orifice", "Orifice")]
FLUID_SOURCE_CHOICES = [
    ("Fixed Operation Fluid", "Fixed Operation Fluid"),
    ("Inform Component Tags", "Inform Component Tags"),
]
AI_PROVIDER_CHOICES = [("gemini", "Google Gemini"), ("azure", "Azure OpenAI")]
TAPPING_CHOICES = [("flange", "flange"), ("corner", "corner"), ("D D/2", "D D/2")]
FLUID_UNIT_CHOICES = [("mol_frac", "mol_frac"), ("percent", "percent"), ("ppm", "ppm")]


def _unit_choices(units: list[str]) -> list[tuple[str, str]]:
    return [(u, u) for u in units]


class DesignCaseForm(forms.Form):
    """Design suction conditions for a single case (A-E).

    Used inside a formset of length five. Validates that ``suc_p`` and
    ``suc_T`` are positive when the case is populated, and converts them to
    SI through ``pint`` in :meth:`clean`.
    """

    case = forms.ChoiceField(
        choices=[(c, c) for c in CASES], widget=forms.HiddenInput, required=True
    )
    gas = forms.CharField(required=False, label="Gas")
    suc_p = forms.FloatField(required=False, label="Suction Pressure", min_value=0)
    suc_p_unit = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.PRESSURE_UNITS),
        initial="bar",
        required=False,
    )
    suc_T = forms.FloatField(required=False, label="Suction Temperature")
    suc_T_unit = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.TEMPERATURE_UNITS),
        initial="degC",
        required=False,
    )

    def clean(self):
        """Validate positivity and attach pint-converted SI values."""
        cleaned = super().clean()
        suc_p = cleaned.get("suc_p")
        suc_T = cleaned.get("suc_T")
        gas = cleaned.get("gas") or ""

        has_any = any(v not in (None, "", 0, 0.0) for v in (suc_p, suc_T, gas))
        if not has_any:
            cleaned["_populated"] = False
            return cleaned
        cleaned["_populated"] = True

        if suc_p is None or suc_p <= 0:
            self.add_error("suc_p", "Suction pressure must be > 0.")
        if suc_T in (None, 0, 0.0):
            self.add_error("suc_T", "Suction temperature is required.")

        if suc_p and suc_T:
            try:
                cleaned["suc_p_Pa"] = unit_helpers.convert(
                    suc_p, cleaned["suc_p_unit"], "Pa"
                )
                cleaned["suc_T_K"] = unit_helpers.convert(
                    suc_T, cleaned["suc_T_unit"], "K"
                )
            except Exception as exc:  # pragma: no cover - pint edge cases
                raise forms.ValidationError(f"Unit conversion failed: {exc}")

        return cleaned


DesignCaseFormSet = formset_factory(DesignCaseForm, extra=0, min_num=5, max_num=5)


class PIServerConfigForm(forms.Form):
    """PI server connection settings."""

    pi_server_name = forms.CharField(required=False, label="PI Server Name")
    pi_auth_method = forms.ChoiceField(
        choices=AUTH_CHOICES, initial="kerberos", label="Authentication"
    )
    pi_username = forms.CharField(required=False, label="Username")
    pi_password = forms.CharField(
        required=False, label="Password", widget=forms.PasswordInput(render_value=False)
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("pi_auth_method") == "basic":
            if not cleaned.get("pi_username"):
                self.add_error("pi_username", "Username required for basic auth.")
        return cleaned


class TagMappingForm(forms.Form):
    """Single-parameter dual-tag + dual-unit row.

    Mirrors ``dual_tag_input_row`` in ``common.tags_config_section``.
    """

    parameter = forms.CharField(widget=forms.HiddenInput)
    tag_1 = forms.CharField(required=False)
    unit_1 = forms.CharField(required=False)
    tag_2 = forms.CharField(required=False)
    unit_2 = forms.CharField(required=False)


class FlowMethodForm(forms.Form):
    """Flow measurement method selector + orifice geometry."""

    flow_method = forms.ChoiceField(
        choices=FLOW_METHOD_CHOICES, initial="Direct", label="Flow Measurement Method"
    )
    orifice_tappings = forms.ChoiceField(
        choices=TAPPING_CHOICES, initial="flange", required=False
    )
    orifice_D = forms.FloatField(required=False, min_value=0, label="Pipe Diameter D")
    orifice_D_unit = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.LENGTH_UNITS), initial="m", required=False
    )
    orifice_d = forms.FloatField(
        required=False, min_value=0, label="Orifice Diameter d"
    )
    orifice_d_unit = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.LENGTH_UNITS), initial="m", required=False
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("flow_method") == "Orifice":
            for key in ("orifice_D", "orifice_d"):
                val = cleaned.get(key)
                if val is None or val <= 0:
                    self.add_error(key, "Required when method is Orifice.")
        return cleaned


class FluidSourceForm(forms.Form):
    """Select whether the process fluid is fixed or read from PI component tags."""

    fluid_source = forms.ChoiceField(
        choices=FLUID_SOURCE_CHOICES, initial="Fixed Operation Fluid"
    )
    operation_fluid_gas = forms.CharField(required=False)


class DateRangeForm(forms.Form):
    """Data time range selection."""

    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    def clean(self):
        cleaned = super().clean()
        sd, st_ = cleaned.get("start_date"), cleaned.get("start_time")
        ed, et_ = cleaned.get("end_date"), cleaned.get("end_time")
        if sd and st_ and ed and et_:
            from datetime import datetime

            start = datetime.combine(sd, st_)
            end = datetime.combine(ed, et_)
            if end <= start:
                raise forms.ValidationError("End must be after start.")
            cleaned["start_datetime"] = start
            cleaned["end_datetime"] = end
        return cleaned


class AIOptionsForm(forms.Form):
    """AI report analysis toggle + provider settings."""

    ai_enabled = forms.BooleanField(
        required=False, label="AI Analysis in Report", initial=False
    )
    ai_provider = forms.ChoiceField(
        choices=AI_PROVIDER_CHOICES, initial="gemini", required=False
    )
    ai_api_key = forms.CharField(
        required=False, widget=forms.PasswordInput(render_value=True), label="API Key"
    )
    ai_azure_endpoint = forms.CharField(required=False, label="Azure Endpoint")
    ai_azure_deployment = forms.CharField(required=False, label="Azure Deployment")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("ai_enabled"):
            if not cleaned.get("ai_api_key"):
                self.add_error("ai_api_key", "API key required when AI is enabled.")
            if cleaned.get("ai_provider") == "azure":
                if not cleaned.get("ai_azure_endpoint"):
                    self.add_error("ai_azure_endpoint", "Azure endpoint required.")
                if not cleaned.get("ai_azure_deployment"):
                    self.add_error("ai_azure_deployment", "Azure deployment required.")
        return cleaned


class SessionMetaForm(forms.Form):
    """Session name + loaded .ccp file upload (sidebar form)."""

    session_name = forms.CharField(required=False, label="Session name")
    ccp_file = forms.FileField(required=False, label="Open File")


class CurvesUnitsForm(forms.Form):
    """Units for the Engauge-digitised performance curves."""

    loaded_curves_speed_units = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.SPEED_UNITS), initial="rpm"
    )
    loaded_curves_flow_units = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.FLOW_UNITS), initial="m³/h"
    )
    loaded_curves_head_units = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.HEAD_UNITS), initial="J/kg"
    )
    loaded_curves_power_units = forms.ChoiceField(
        choices=_unit_choices(unit_helpers.POWER_UNITS), initial="kW"
    )


TAG_PARAMETERS_DIRECT = [
    ("suc_p", "Suction Pressure", unit_helpers.PRESSURE_UNITS),
    ("suc_T", "Suction Temperature", unit_helpers.TEMPERATURE_UNITS),
    ("disch_p", "Discharge Pressure", unit_helpers.PRESSURE_UNITS),
    ("disch_T", "Discharge Temperature", unit_helpers.TEMPERATURE_UNITS),
    ("speed", "Speed", unit_helpers.SPEED_UNITS),
    ("flow", "Flow", unit_helpers.FLOW_UNITS),
]

TAG_PARAMETERS_ORIFICE = [
    ("suc_p", "Suction Pressure", unit_helpers.PRESSURE_UNITS),
    ("suc_T", "Suction Temperature", unit_helpers.TEMPERATURE_UNITS),
    ("disch_p", "Discharge Pressure", unit_helpers.PRESSURE_UNITS),
    ("disch_T", "Discharge Temperature", unit_helpers.TEMPERATURE_UNITS),
    ("speed", "Speed", unit_helpers.SPEED_UNITS),
    ("delta_p", "Delta P", unit_helpers.PRESSURE_UNITS),
    ("p_downstream", "Downstream P", unit_helpers.PRESSURE_UNITS),
]


def tag_parameters_for(flow_method: str):
    """Return the tag parameter list matching the flow measurement method."""
    if flow_method == "Orifice":
        return TAG_PARAMETERS_ORIFICE
    return TAG_PARAMETERS_DIRECT


def default_fluid_components():
    """Return the default fluid component list for the component-tags form."""
    return gas_composition.FLUID_LIST
