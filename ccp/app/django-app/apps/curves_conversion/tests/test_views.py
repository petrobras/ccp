"""Smoke tests for the curves conversion views."""

from __future__ import annotations

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_page_renders():
    client = Client()
    response = client.get("/curves-conversion/")
    assert response.status_code == 200
    assert b"Curves Conversion" in response.content


def test_upload_requires_file():
    client = Client()
    response = client.post("/curves-conversion/upload-csv/", {})
    assert response.status_code == 400


def test_convert_without_files_returns_error():
    client = Client()
    payload = {
        "original-pressure": "1.0",
        "original-pressure_unit": "bar",
        "original-temperature": "300",
        "original-temperature_unit": "degK",
        "converted-pressure": "1.2",
        "converted-pressure_unit": "bar",
        "converted-temperature": "305",
        "converted-temperature_unit": "degK",
        "params-find_method": "speed",
        "params-speed_option": "same",
        "params-loaded_flow_unit": "m³/h",
        "params-loaded_head_unit": "kJ/kg",
        "params-loaded_power_unit": "kW",
        "params-loaded_disch_p_unit": "bar",
        "params-loaded_disch_T_unit": "degK",
        "params-loaded_speed_unit": "rpm",
        "params-plot_flow_unit": "m³/h",
        "params-plot_head_unit": "kJ/kg",
        "params-plot_power_unit": "kW",
        "params-plot_disch_p_unit": "bar",
        "params-plot_disch_T_unit": "degK",
        "params-plot_speed_unit": "rpm",
    }
    response = client.post("/curves-conversion/convert/", payload)
    assert response.status_code == 400
