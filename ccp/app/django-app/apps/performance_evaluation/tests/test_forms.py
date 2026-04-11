"""Form-level validation tests for the performance_evaluation app."""

from __future__ import annotations

from datetime import date, time

import pytest

from apps.performance_evaluation import forms


def _formset_data(cases):
    data = {
        "design-TOTAL_FORMS": "5",
        "design-INITIAL_FORMS": "5",
        "design-MIN_NUM_FORMS": "5",
        "design-MAX_NUM_FORMS": "5",
    }
    for idx, cd in enumerate(cases):
        for key, value in cd.items():
            data[f"design-{idx}-{key}"] = value
    return data


def test_design_case_form_valid():
    form = forms.DesignCaseForm(
        data={
            "case": "A",
            "gas": "ng",
            "suc_p": 10.0,
            "suc_p_unit": "bar",
            "suc_T": 25.0,
            "suc_T_unit": "degC",
        }
    )
    assert form.is_valid(), form.errors
    cd = form.cleaned_data
    assert cd["_populated"] is True
    assert cd["suc_p_Pa"] == pytest.approx(1e6)
    assert cd["suc_T_K"] == pytest.approx(298.15)


def test_design_case_form_empty_is_unpopulated():
    form = forms.DesignCaseForm(
        data={
            "case": "B",
            "gas": "",
            "suc_p": "",
            "suc_p_unit": "bar",
            "suc_T": "",
            "suc_T_unit": "degC",
        }
    )
    assert form.is_valid()
    assert form.cleaned_data["_populated"] is False


def test_design_case_form_rejects_negative_pressure():
    form = forms.DesignCaseForm(
        data={
            "case": "A",
            "gas": "ng",
            "suc_p": -1.0,
            "suc_p_unit": "bar",
            "suc_T": 25.0,
            "suc_T_unit": "degC",
        }
    )
    assert not form.is_valid()
    assert "suc_p" in form.errors


def test_design_formset_requires_five_cases():
    data = _formset_data(
        [
            {
                "case": c,
                "gas": "",
                "suc_p": "",
                "suc_p_unit": "bar",
                "suc_T": "",
                "suc_T_unit": "degC",
            }
            for c in forms.CASES
        ]
    )
    fs = forms.DesignCaseFormSet(data=data, prefix="design")
    assert fs.is_valid(), fs.errors


def test_pi_form_basic_requires_username():
    form = forms.PIServerConfigForm(
        data={"pi_server_name": "srv", "pi_auth_method": "basic", "pi_username": ""}
    )
    assert not form.is_valid()
    assert "pi_username" in form.errors


def test_flow_method_orifice_requires_diameters():
    form = forms.FlowMethodForm(
        data={
            "flow_method": "Orifice",
            "orifice_tappings": "flange",
            "orifice_D": "",
            "orifice_D_unit": "m",
            "orifice_d": "",
            "orifice_d_unit": "m",
        }
    )
    assert not form.is_valid()
    assert "orifice_D" in form.errors
    assert "orifice_d" in form.errors


def test_flow_method_direct_is_ok_without_diameters():
    form = forms.FlowMethodForm(
        data={
            "flow_method": "Direct",
            "orifice_tappings": "flange",
            "orifice_D_unit": "m",
            "orifice_d_unit": "m",
        }
    )
    assert form.is_valid(), form.errors


def test_date_range_form_rejects_reversed_interval():
    form = forms.DateRangeForm(
        data={
            "start_date": date(2024, 1, 10),
            "start_time": time(12, 0),
            "end_date": date(2024, 1, 1),
            "end_time": time(0, 0),
        }
    )
    assert not form.is_valid()


def test_ai_options_requires_key_when_enabled():
    form = forms.AIOptionsForm(
        data={
            "ai_enabled": "on",
            "ai_provider": "gemini",
            "ai_api_key": "",
        }
    )
    assert not form.is_valid()
    assert "ai_api_key" in form.errors


def test_ai_options_disabled_needs_nothing():
    form = forms.AIOptionsForm(data={"ai_provider": "gemini"})
    assert form.is_valid(), form.errors


def test_tag_parameters_direct_vs_orifice():
    direct = {k for k, _, _ in forms.tag_parameters_for("Direct")}
    orifice = {k for k, _, _ in forms.tag_parameters_for("Orifice")}
    assert "flow" in direct
    assert "flow" not in orifice
    assert "delta_p" in orifice
    assert "p_downstream" in orifice
