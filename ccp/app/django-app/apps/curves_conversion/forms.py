"""Django forms for the curves conversion page.

Forms mirror the Streamlit widgets from ``ccp/app/pages/3_curves_conversion.py``.
They are deliberately thin — validation delegates to the ``ccp`` library inside
:mod:`apps.curves_conversion.services`.
"""

from __future__ import annotations

from django import forms

try:
    from apps.core.services.unit_helpers import (
        FLOW_UNITS,
        HEAD_UNITS,
        POWER_UNITS,
        PRESSURE_UNITS,
        SPEED_UNITS,
        TEMPERATURE_UNITS,
    )
except ImportError:  # pragma: no cover - fallback when Unit 2 not merged
    FLOW_UNITS = ["m³/h", "m³/min", "m³/s", "kg/h", "kg/s"]
    HEAD_UNITS = ["kJ/kg", "J/kg", "m*g0", "ft"]
    POWER_UNITS = ["kW", "hp", "W", "MW"]
    PRESSURE_UNITS = ["bar", "kgf/cm²", "Pa", "kPa", "MPa", "psi"]
    SPEED_UNITS = ["rpm", "Hz"]
    TEMPERATURE_UNITS = ["degK", "degC", "degF", "degR"]


def _pairs(values):
    """Return a list of ``(value, value)`` tuples for use in ``ChoiceField``."""
    return [(value, value) for value in values]


class SuctionConditionsForm(forms.Form):
    """Shared fields for a suction state: gas name, pressure, temperature."""

    gas = forms.CharField(max_length=64, required=False)
    pressure = forms.FloatField(min_value=0.0)
    pressure_unit = forms.ChoiceField(choices=_pairs(PRESSURE_UNITS))
    temperature = forms.FloatField(min_value=0.0)
    temperature_unit = forms.ChoiceField(choices=_pairs(TEMPERATURE_UNITS))


class OriginalSuctionForm(SuctionConditionsForm):
    """Suction conditions for the original (as-tested) curves."""


class ConvertedSuctionForm(SuctionConditionsForm):
    """Target suction conditions for the converted curves."""


class ConversionParamsForm(forms.Form):
    """Conversion strategy + unit selections for loaded and plot curves."""

    find_method = forms.ChoiceField(
        choices=[("speed", "speed"), ("volume_ratio", "volume_ratio")],
        initial="speed",
    )
    speed_option = forms.ChoiceField(
        choices=[("same", "same"), ("calculate", "calculate")],
        initial="same",
    )

    loaded_flow_unit = forms.ChoiceField(choices=_pairs(FLOW_UNITS), initial="m³/h")
    loaded_head_unit = forms.ChoiceField(choices=_pairs(HEAD_UNITS), initial="kJ/kg")
    loaded_power_unit = forms.ChoiceField(choices=_pairs(POWER_UNITS), initial="kW")
    loaded_disch_p_unit = forms.ChoiceField(
        choices=_pairs(PRESSURE_UNITS), initial="bar"
    )
    loaded_disch_T_unit = forms.ChoiceField(
        choices=_pairs(TEMPERATURE_UNITS), initial="degK"
    )
    loaded_speed_unit = forms.ChoiceField(choices=_pairs(SPEED_UNITS), initial="rpm")

    plot_flow_unit = forms.ChoiceField(choices=_pairs(FLOW_UNITS), initial="m³/h")
    plot_head_unit = forms.ChoiceField(choices=_pairs(HEAD_UNITS), initial="kJ/kg")
    plot_power_unit = forms.ChoiceField(choices=_pairs(POWER_UNITS), initial="kW")
    plot_disch_p_unit = forms.ChoiceField(choices=_pairs(PRESSURE_UNITS), initial="bar")
    plot_disch_T_unit = forms.ChoiceField(
        choices=_pairs(TEMPERATURE_UNITS), initial="degK"
    )
    plot_speed_unit = forms.ChoiceField(choices=_pairs(SPEED_UNITS), initial="rpm")

    operational_flow = forms.FloatField(min_value=0.0, required=False)
    operational_speed = forms.FloatField(min_value=0.0, required=False)


class CurvesCSVUploadForm(forms.Form):
    """Upload up to two Engauge-digitized CSV curve files."""

    curves_file_1 = forms.FileField(required=False)
    curves_file_2 = forms.FileField(required=False)

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("curves_file_1") and not cleaned.get("curves_file_2"):
            raise forms.ValidationError(
                "Envie pelo menos um arquivo CSV digitalizado (Engauge)."
            )
        return cleaned
