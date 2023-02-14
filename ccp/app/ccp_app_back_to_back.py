import streamlit as st
import ccp
import json
from ccp.compressor import PointFirstSection, PointSecondSection
from pathlib import Path

Q_ = ccp.Q_


assets = Path(__file__).parent / "assets"
ccp_ico = assets / "favicon.ico"
ccp_logo = assets / "ccp.png"

st.set_page_config(
    page_title="Hello",
    page_icon=str(ccp_ico),
    layout="wide",
)

assets = Path(__file__).parent / "assets"
ccp_ico = assets / "favicon.ico"
ccp_logo = assets / "ccp.png"

st.markdown(
    """
# Test Data for Back-to-Back Compressor
"""
)


def get_session():
    # if file is being loaded, session_name is set with the file name
    if "session_name" not in st.session_state:
        st.session_state.session_name = ""


get_session()

st.session_state.session_name = st.sidebar.text_input(
    "Session name", value=st.session_state.session_name
)

# Create a Streamlit sidebar with a file uploader to load a session state file
with st.sidebar.form("my-form", clear_on_submit=True):
    file = st.file_uploader("Load Data")
    submitted = st.form_submit_button("Load Data")

if submitted and file is not None:
    st.sidebar.write("Loaded!")
    session_state_data = json.load(file)
    st.session_state.update(session_state_data)
    st.session_state.session_name = file.name.replace(".json", "")
    st.experimental_rerun()

if st.sidebar.button("Save session state"):
    session_state_dict = dict(st.session_state)
    session_state_json = json.dumps(session_state_dict)
    file_name = f"{st.session_state.session_name}.json" or "session_state.json"
    with open(file_name, "w") as f:
        f.write(session_state_json)
    st.sidebar.download_button(
        label="Download session state",
        data=session_state_json,
        file_name=file_name,
        mime="application/json",
    )


# add container with 4 columns and 2 rows
with st.expander("Options"):
    col1, col2, col3 = st.columns(3)
    with col1:
        reynolds_correction = st.checkbox("Reynolds Correction", value=True)
        casing_heat_loss = st.checkbox("Casing Heat Loss", value=True)
    with col2:
        calculate_leakages = st.checkbox("Calculate Leakages", value=True)
        seal_gas_flow = st.checkbox("Seal Gas Flow", value=True)
    with col3:
        variable_speed = st.checkbox("Variable Speed", value=True)

# parameters with name and label
flow_m_units = ["kg/h", "lbm/h", "kg/s", "lbm/s"]
pressure_units = ["bar", "psi", "Pa", "kPa", "MPa"]
temperature_units = ["degK", "degC", "degF", "degR"]
speed_units = ["rpm", "Hz"]
length_units = ["m", "mm", "ft", "in"]

parameters_map = {
    "flow": {
        "label": "Flow",
        "units": ["kg/h", "lbm/h", "kg/s", "lbm/s", "m3/h", "m3/s"],
    },
    "suction_pressure": {
        "label": "Suction Pressure",
        "units": pressure_units,
    },
    "suction_temperature": {
        "label": "Suction Temperature",
        "units": temperature_units,
    },
    "discharge_pressure": {
        "label": "Discharge Pressure",
        "units": pressure_units,
    },
    "discharge_temperature": {
        "label": "Discharge Temperature",
        "units": temperature_units,
    },
    "casing_delta_T": {
        "label": "Casing ΔT",
        "units": temperature_units,
    },
    "speed": {
        "label": "Speed",
        "units": speed_units,
    },
    "balance_line_flow_m": {
        "label": "Balance Line Flow",
        "units": flow_m_units,
    },
    "end_seal_upstream_pressure": {
        "label": "Pressure Upstream End Seal",
        "units": pressure_units,
    },
    "end_seal_upstream_temperature": {
        "label": "Temperature Upstream End Seal",
        "units": temperature_units,
    },
    "div_wall_flow_m": {
        "label": "Division Wall Flow",
        "units": flow_m_units,
    },
    "div_wall_upstream_pressure": {
        "label": "Pressure Upstream Division Wall",
        "units": pressure_units,
    },
    "div_wall_upstream_temperature": {
        "label": "Temperature Upstream Division Wall",
        "units": temperature_units,
    },
    "first_section_discharge_flow_m": {
        "label": "First Section Discharge Flow",
        "units": flow_m_units,
    },
    "seal_gas_flow_m": {
        "label": "Seal Gas Flow",
        "units": flow_m_units,
    },
    "seal_gas_temperature": {
        "label": "Seal Gas Temperature",
        "units": temperature_units,
    },
    "head": {
        "label": "Head",
        "units": ["kJ/kg", "J/kg", "m", "ft"],
    },
    "efficiency": {
        "label": "Efficiency",
        "units": ["%", "decimal"],
    },
    "power": {
        "label": "Power",
        "units": ["kW", "hp", "W", "Btu/h", "MW"],
    },
    "b": {
        "label": "First Impeller Width",
        "units": ["mm", "m", "ft", "in"],
    },
    "D": {
        "label": "First Impeller Diameter",
        "units": ["mm", "m", "ft", "in"],
    },
    "casing_area": {
        "label": "Casing Area",
        "units": ["m²", "mm²", "ft²", "in²"],
    },
}


with st.expander("Data Sheet"):
    # build container with 8 columns
    points_title = st.container()
    points_title_columns = points_title.columns(4, gap="small")
    points_title_columns[0].markdown("")
    points_title_columns[1].markdown("Units")
    points_title_columns[2].markdown("First Section")
    points_title_columns[3].markdown("Second Section")

    # build one container with 8 columns for each parameter
    for parameter in [
        "flow",
        "suction_pressure",
        "suction_temperature",
        "discharge_pressure",
        "discharge_temperature",
        "head",
        "efficiency",
        "speed",
        "power",
        "b",
        "D",
        "casing_area",
    ]:
        parameter_container = st.container()
        (
            parameters_col,
            units_col,
            first_section_col,
            second_section_col,
        ) = parameter_container.columns(4, gap="small")
        parameters_map[parameter]["section_1"] = {}
        parameters_map[parameter]["section_1"]["values"] = {}
        parameters_map[parameter]["section_2"] = {}
        parameters_map[parameter]["section_2"]["values"] = {}

        parameters_col.markdown(f"{parameters_map[parameter]['label']}")
        parameters_map[parameter]["selected_units"] = units_col.selectbox(
            f"{parameter} units",
            options=parameters_map[parameter]["units"],
            key=f"{parameter}_units_section_1_guarantee",
            label_visibility="collapsed",
        )
        parameters_map[parameter]["section_1"]["values"][
            f"point_guarantee"
        ] = first_section_col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_section_1_point_guarantee",
            label_visibility="collapsed",
        )
        parameters_map[parameter]["section_2"]["values"][
            f"point_guarantee"
        ] = second_section_col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_section_2_point_guarantee",
            label_visibility="collapsed",
        )

number_of_points = 6
number_of_columns = number_of_points + 2

with st.expander("Test Data"):
    tab_section_1, tab_section_2 = st.tabs(["First Section", "Second Section"])
    # build container with 8 columns
    with tab_section_1:
        points_title = st.container()
        points_title_columns = points_title.columns(number_of_columns, gap="small")
        for i, col in enumerate(points_title_columns):
            if i == 0:
                col.markdown("")
            elif i == 1:
                col.markdown("Units")
            else:
                col.markdown(f"Point {i - 1}")

        # build one container with 8 columns for each parameter
        for parameter in [
            "flow",
            "suction_pressure",
            "suction_temperature",
            "discharge_pressure",
            "discharge_temperature",
            "casing_delta_T",
            "speed",
            "balance_line_flow_m",
            "end_seal_upstream_pressure",
            "end_seal_upstream_temperature",
            "div_wall_flow_m",
            "div_wall_upstream_pressure",
            "div_wall_upstream_temperature",
            "first_section_discharge_flow_m",
            "seal_gas_flow_m",
            "seal_gas_temperature",
        ]:
            parameter_container = st.container()
            parameter_columns = parameter_container.columns(
                number_of_columns, gap="small"
            )
            parameters_map[parameter]["section_1"] = {}
            parameters_map[parameter]["section_1"]["values"] = {}

            for i, col in enumerate(parameter_columns):
                if i == 0:
                    col.markdown(f"{parameters_map[parameter]['label']}")
                elif i == 1:
                    parameters_map[parameter]["selected_units"] = col.selectbox(
                        f"{parameter} units",
                        options=parameters_map[parameter]["units"],
                        key=f"{parameter}_units_section_1",
                        label_visibility="collapsed",
                    )
                else:
                    parameters_map[parameter]["section_1"]["values"][
                        f"point_{i - 1}"
                    ] = col.text_input(
                        f"{parameter} value.",
                        key=f"{parameter}_section_1_point_{i - 1}",
                        label_visibility="collapsed",
                    )

    with tab_section_2:

        # add title
        number_of_points = 6
        number_of_columns = number_of_points + 2
        # build container with 8 columns
        points_title = st.container()
        points_title_columns = points_title.columns(number_of_columns, gap="small")
        for i, col in enumerate(points_title_columns):
            if i == 0:
                col.markdown("")
            elif i == 1:
                col.markdown("Units")
            else:
                col.markdown(f"Point {i - 1}")

        # build one container with 8 columns for each parameter
        for parameter in [
            "flow",
            "suction_pressure",
            "suction_temperature",
            "discharge_pressure",
            "discharge_temperature",
            "casing_delta_T",
            "speed",
            "balance_line_flow_m",
            "seal_gas_flow_m",
        ]:
            parameter_container = st.container()
            parameter_columns = parameter_container.columns(
                number_of_columns, gap="small"
            )
            parameters_map[parameter]["section_2"] = {}
            parameters_map[parameter]["section_2"]["values"] = {}
            for i, col in enumerate(parameter_columns):
                if i == 0:
                    col.markdown(f"{parameters_map[parameter]['label']}")
                elif i == 1:
                    parameters_map[parameter]["selected_units"] = col.selectbox(
                        f"{parameter} units",
                        options=parameters_map[parameter]["units"],
                        key=f"{parameter}_units_section_2",
                        label_visibility="collapsed",
                    )
                else:
                    parameters_map[parameter]["section_2"]["values"][
                        f"point_{i - 1}"
                    ] = col.text_input(
                        f"{parameter} value.",
                        key=f"{parameter}_section_2_point_{i - 1}",
                        label_visibility="collapsed",
                    )

# add calculate button
calculate_button = st.button("Calculate", type="primary", use_container_width=True)

# create test points for first section
first_section_test_points = []
kwargs = {}

if calculate_button:
    print("calculating")
    for i in range(1, number_of_points + 1):
        # check if at least flow, suction pressure and suction temperature are filled
        if (
            st.session_state[f"flow_section_1_point_{i}"] == ""
            or st.session_state[f"suction_pressure_section_1_point_{i}"] == ""
            or st.session_state[f"suction_temperature_section_1_point_{i}"] == ""
        ):
            print("continue", i)
            continue
        else:
            print("ok", i)
            st.warning(
                f"Please fill at least flow, suction pressure and suction temperature for point {i}"
            )
            calculate_button = False
            if (
                Q_(0, parameters_map["flow"]["selected_units"]).dimensionality
                == "[mass] / [time]"
            ):
                if st.session_state[f"flow_section_1_point_{i}"]:
                    kwargs["flow_m"] = Q_(
                        st.session_state[f"flow_section_1_point_{i}"],
                        parameters_map["flow"]["selected_units"],
                    )
                else:
                    kwargs["flow_m"] = None
            else:
                if st.session_state[f"flow_section_1_point_{i}"]:
                    kwargs["flow_v"] = Q_(
                        st.session_state[f"flow_section_1_point_{i}"],
                        parameters_map["flow"]["selected_units"],
                    )
                else:
                    kwargs["flow_v"] = None
            kwargs["suc"] = ccp.State(
                p=Q_(
                    st.session_state[f"suction_pressure_section_1_point_{i}"],
                    parameters_map["suction_pressure"]["selected_units"],
                ),
                T=Q_(
                    st.session_state[f"suction_temperature_section_1_point_{i}"],
                    parameters_map["suction_temperature"]["selected_units"],
                ),
                fluid={"CO2": 1},
            )
            kwargs["disch"] = ccp.State(
                p=Q_(
                    st.session_state[f"discharge_pressure_section_1_point_{i}"],
                    parameters_map["discharge_pressure"]["selected_units"],
                ),
                T=Q_(
                    st.session_state[f"discharge_temperature_section_1_point_{i}"],
                    parameters_map["discharge_temperature"]["selected_units"],
                ),
                fluid={"CO2": 1},
            )
            if (
                st.session_state[f"casing_delta_T_section_1_point_{i}"]
                and casing_heat_loss
            ):
                kwargs["casing_temperature"] = Q_(
                    st.session_state[f"casing_delta_T_section_1_point_{i}"],
                    parameters_map["casing_delta_T"]["selected_units"],
                )
                kwargs["ambient_temperature"] = 0
            else:
                kwargs["casing_temperature"] = 0
                kwargs["ambient_temperature"] = 0

            if (
                st.session_state[f"balance_line_flow_m_section_1_point_{i}"]
                and calculate_leakages
            ):
                kwargs["balance_line_flow_m"] = Q_(
                    st.session_state[f"balance_line_flow_m_section_1_point_{i}"],
                    parameters_map["balance_line_flow_m"]["selected_units"],
                )
            else:
                kwargs["balance_line_flow_m"] = None

            if (
                st.session_state[f"seal_gas_flow_m_section_1_point_{i}"]
                and calculate_leakages
            ):
                kwargs["seal_gas_flow_m"] = Q_(
                    st.session_state[f"seal_gas_flow_m_section_1_point_{i}"],
                    parameters_map["seal_gas_flow_m"]["selected_units"],
                )
                kwargs["seal_gas_temperature"] = Q_(
                    st.session_state[f"seal_gas_temperature_section_1_point_{i}"],
                    parameters_map["seal_gas_temperature"]["selected_units"],
                )
            else:
                kwargs["seal_gas_flow_m"] = None
                kwargs["seal_gas_temperature"] = None

            if (
                st.session_state[f"div_wall_flow_m_section_1_point_{i}"]
                and calculate_leakages
            ):
                kwargs["div_wall_flow_m"] = Q_(
                    st.session_state[f"div_wall_flow_m_section_1_point_{i}"],
                    parameters_map["div_wall_flow_m"]["selected_units"],
                )
                kwargs["div_wall_upstream_pressure"] = Q_(
                    st.session_state[f"div_wall_upstream_pressure_section_1_point_{i}"],
                    parameters_map["div_wall_upstream_pressure"]["selected_units"],
                )
                kwargs["div_wall_upstream_temperature"] = Q_(
                    st.session_state[
                        f"div_wall_upstream_temperature_section_1_point_{i}"
                    ],
                    parameters_map["div_wall_upstream_temperature"]["selected_units"],
                )
            else:
                kwargs["div_wall_flow_m"] = None
                kwargs["div_wall_upstream_pressure"] = None
                kwargs["div_wall_upstream_temperature"] = None

            if (
                st.session_state[f"first_section_discharge_flow_m_section_1_point_{i}"]
                and calculate_leakages
            ):
                kwargs["first_section_discharge_flow_m"] = Q_(
                    st.session_state[
                        f"first_section_discharge_flow_m_section_1_point_{i}"
                    ],
                    parameters_map["first_section_discharge_flow_m"]["selected_units"],
                )
            else:
                kwargs["first_section_discharge_flow_m"] = None

            first_section_test_points.append(
                PointFirstSection(
                    speed=Q_(
                        st.session_state[f"speed_section_1_point_{i}"],
                        parameters_map["speed"]["selected_units"],
                    ),
                    b=Q_(10.15, "mm"),
                    D=Q_(365, "mm"),
                    oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
                    oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
                    oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
                    oil_inlet_temperature=Q_(41.544, "degC"),
                    oil_outlet_temperature_de=Q_(49.727, "degC"),
                    oil_outlet_temperature_nde=Q_(50.621, "degC"),
                    casing_area=5.5,
                    **kwargs,
                )
            )
