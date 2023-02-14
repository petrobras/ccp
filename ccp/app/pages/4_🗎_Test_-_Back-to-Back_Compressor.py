import streamlit as st

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
parameters_map = {
    "flow": {
        "label": "Flow",
        "units": ["kg/h", "lbm/h", "kg/s", "lbm/s", "m3/h", "m3/s"],
    },
    "suction_pressure": {
        "label": "Suction Pressure",
        "units": ["bar", "psi", "Pa", "kPa", "MPa"],
    },
    "suction_temperature": {
        "label": "Suction Temperature",
        "units": ["degK", "degC", "degF", "degR"],
    },
    "discharge_pressure": {
        "label": "Discharge Pressure",
        "units": ["bar", "psi", "Pa", "kPa", "MPa"],
    },
    "discharge_temperature": {
        "label": "Discharge Temperature",
        "units": ["degK", "degC", "degF", "degR"],
    },
    "casing_delta_T": {
        "label": "Casing ΔT",
        "units": ["degK", "degC", "degF", "degR"],
    },
    "balance_line_flow_m": {
        "label": "Balance Line Flow",
        "units": ["kg/h", "lbm/h", "kg/s", "lbm/s", "m3/h", "m3/s"],
    },
    "seal_gas_flow_m": {
        "label": "Seal Gas Flow",
        "units": ["kg/h", "lbm/h", "kg/s", "lbm/s", "m3/h", "m3/s"],
    },
    "seal_gas_temperature": {
        "label": "Seal Gas Temperature",
        "units": ["degK", "degC", "degF", "degR"],
    },
    "speed": {
        "label": "Speed",
        "units": ["rpm", "Hz"],
    },
}

# add container with 11 columns
title_container = st.container()
title_columns = title_container.columns(11, gap="small")
for col, parameter in zip(title_columns, parameters_map.values()):
    col.markdown(f"{parameter['label']}")

# add container with 11 columns of the units
units_container = st.container()
units_columns = units_container.columns(11, gap="small")
parameters_units_selected = {}
for col, parameter in zip(
    units_columns,
    parameters_map.keys(),
):
    parameters_units_selected[parameter] = col.selectbox(
        f"{parameter} units.",
        options=parameters_map[parameter]["units"],
        key=parameter,
        label_visibility="collapsed",
    )

# add container with 11 columns for the inputs
test_data_container = st.container()
test_data_columns = test_data_container.columns(11, gap="small")
test_data_values = {}
points = range(8)
for point in points:
    for col, parameter in zip(test_data_columns, parameters_map.keys()):
        test_data_values[parameter] = col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_{point}",
            label_visibility="collapsed",
        )
