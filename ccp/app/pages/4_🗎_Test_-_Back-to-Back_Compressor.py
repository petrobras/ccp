import streamlit as st
from ccp import ureg

from pathlib import Path


assets = Path(__file__).parent / "assets"
ccp_ico = assets / "favicon.ico"
ccp_logo = assets / "ccp.png"

st.markdown(
    """
Test Data for Back-to-Back Compressor
"""
)

# add container with 4 columns and 2 rows
with st.expander("Options"):
    col1, col2, col3 = st.columns(3)
    with col1:
        reynolds_correction = st.checkbox("Reynolds Correction", value=True)
        casing_heat_loss = st.checkbox("Casing Heat Loss", value=True)
    with col2:
        balance_line_leakage = st.checkbox("Balance Line Leakage", value=True)
        seal_gas_flow = st.checkbox("Seal Gas Flow", value=True)
    with col3:
        variable_speed = st.checkbox("Variable Speed", value=True)

# parameters with name and label
parameters_labels = {
    "flow": "Flow",
    "suction_pressure": "Suction Pressure",
    "suction_temperature": "Suction Temperature",
    "discharge_pressure": "Discharge Pressure",
    "discharge_temperature": "Discharge Temperature",
    "casing_delta_T": "Casing ΔT",
    "balance_line_flow_m": "Balance Line Flow",
    "seal_gas_flow_m": "Seal Gas Flow",
    "seal_gas_temperature": "Seal Gas Temperature",
    "speed": "Speed",
}

parameters_units = {
    "flow": ["kg/h", "lbm/h", "kg/s", "lbm/s", "m3/h", "m3/s"],
    "suction_pressure": ["bar", "psi", "Pa", "kPa", "MPa"],
    "suction_temperature": ["degK", "degC", "degF", "degR"],
    "discharge_pressure": ["bar", "psi", "Pa", "kPa", "MPa"],
    "discharge_temperature": ["degK", "degC", "degF", "degR"],
    "casing_delta_T": ["degK", "degC", "degF", "degR"],
    "balance_line_flow_m": ["kg/h", "lbm/h", "kg/s", "lbm/s"],
    "seal_gas_flow_m": ["kg/h", "lbm/h", "kg/s", "lbm/s"],
    "seal_gas_temperature": ["degK", "degC", "degF", "degR"],
    "speed": ["rpm", "Hz"],
}

# add container with 11 columns
title_container = st.container()
title_columns = title_container.columns(11, gap="small")
for col, label in zip(title_columns, parameters_labels.values()):
    col.markdown(f"{label}")

# add container with 11 columns of the units
units_container = st.container()
units_columns = units_container.columns(11, gap="small")
parameters_units_selected = {}
for col, parameter, units in zip(
    units_columns, parameters_units.keys(), parameters_units.values()
):
    parameters_units_selected[parameter] = col.selectbox(
        f"{parameter} units.",
        options=units,
        key=parameter,
        label_visibility="collapsed",
    )

# add container with 11 columns for the inputs
test_data_container = st.container()
test_data_columns = test_data_container.columns(11, gap="small")
test_data_values = {}
points = range(8)
for point in points:
    for col, parameter in zip(test_data_columns, parameters_units.keys()):
        test_data_values[parameter] = col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_{point}",
            label_visibility="collapsed",
        )
