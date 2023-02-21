import streamlit as st
import ccp
import json
import pandas as pd
import pickle
from ccp.compressor import PointFirstSection, PointSecondSection, BackToBack
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

st.markdown(
    """
# Performance Test Back-to-Back Compressor
"""
)


def get_session():
    # if file is being loaded, session_name is set with the file name
    if "session_name" not in st.session_state:
        st.session_state.session_name = ""


get_session()

# Create a Streamlit sidebar with a file uploader to load a session state file
with st.sidebar.expander("📁 File"):
    st.session_state.session_name = st.text_input(
        "Session name", value=st.session_state.session_name
    )

    with st.form("my_form", clear_on_submit=True):
        file = st.file_uploader("Load Data")
        submitted = st.form_submit_button("Load")

    if submitted and file is not None:
        st.write("Loaded!")
        session_state_data = json.load(file)
        # remove keys that cannot be set with st.session_state.update
        for key in [
            "FormSubmitter:my_form-Load",
            "FormSubmitter:my_form-Load Data",
            "my_form",
        ]:
            try:
                del session_state_data[key]
            except KeyError:
                pass
        st.session_state.update(session_state_data)
        st.session_state.session_name = file.name.replace(".json", "")
        st.experimental_rerun()

    if st.button("Save session state"):
        session_state_dict = dict(st.session_state)
        session_state_json = json.dumps(session_state_dict)
        file_name = f"{st.session_state.session_name}.json" or "session_state.json"
        with open(file_name, "w") as f:
            f.write(session_state_json)
        st.download_button(
            label="Download session state",
            data=session_state_json,
            file_name=file_name,
            mime="application/json",
        )


# Gas selection
fluid_list = []
for fluid in ccp.fluid_list.keys():
    fluid_list.append(fluid.lower())
    for possible_name in ccp.fluid_list[fluid].possible_names:
        if possible_name != fluid.lower():
            fluid_list.append(possible_name)
fluid_list = sorted(fluid_list)
fluid_list.insert(0, "")

with st.expander("Gas Selection"):
    gas_compositions_table = {}
    gas_columns = st.columns(5)
    for i, gas_column in enumerate(gas_columns):
        gas_compositions_table[f"gas_{i}"] = {}

        gas_compositions_table[f"gas_{i}"]["name"] = gas_column.text_input(
            f"Gas Name",
            value=f"gas_{i}",
            key=f"gas_{i}",
        )
        component, molar_fraction = gas_column.columns([2, 1])
        default_components = [
            "methane",
            "ethane",
            "propane",
            "n-butane",
            "i-butane",
            "n-pentane",
            "i-pentane",
            "n-hexane",
            "n-heptane",
            "n-octane",
            "nitrogen",
            "h2s",
            "co2",
            "h2o",
        ]
        for j, default_component in enumerate(default_components):
            gas_compositions_table[f"gas_{i}"][f"component_{j}"] = component.selectbox(
                "Component",
                options=fluid_list,
                index=fluid_list.index(default_component),
                key=f"gas_{i}_component_{j}",
                label_visibility="collapsed",
            )
            gas_compositions_table[f"gas_{i}"][
                f"molar_fraction_{j}"
            ] = molar_fraction.text_input(
                "Molar Fraction",
                value="0",
                key=f"gas_{i}_molar_fraction_{j}",
                label_visibility="collapsed",
            )


# add container with 4 columns and 2 rows
with st.sidebar.expander("⚙️ Options"):
    reynolds_correction = st.checkbox("Reynolds Correction", value=True)
    casing_heat_loss = st.checkbox("Casing Heat Loss", value=True)
    calculate_leakages = st.checkbox("Calculate Leakages", value=True)
    seal_gas_flow = st.checkbox("Seal Gas Flow", value=True)
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
        "label": "Gas Power",
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

# add dict to each section to store the values for guarantee and test points
# in the parameters_map
number_of_test_points = 6
points_list = ["point_guarantee"] + [
    f"point_{i}" for i in range(1, number_of_test_points + 1)
]
for parameter in parameters_map:
    for section in ["section_1", "section_2"]:
        parameters_map[parameter][section] = {
            "data_sheet_units": None,
            "test_units": None,
        }
        for point in points_list:
            parameters_map[parameter][section][point] = {
                "value": None,
            }

with st.expander("Data Sheet"):
    # build container with 8 columns
    points_title = st.container()
    points_title_columns = points_title.columns(4, gap="small")
    points_title_columns[0].markdown("")
    points_title_columns[1].markdown("Units")
    points_title_columns[2].markdown("First Section")
    points_title_columns[3].markdown("Second Section")

    points_gas_columns = points_title.columns(4, gap="small")
    points_gas_columns[0].markdown("Gas Selection")
    points_gas_columns[1].markdown("")
    gas_options = [st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_columns)]
    gas_name_section_1_point_guarantee = points_gas_columns[2].selectbox(
        "gas_section_1_point_guarantee",
        options=gas_options,
        label_visibility="collapsed",
    )
    gas_name_section_2_point_guarantee = points_gas_columns[3].selectbox(
        "gas_section_2_point_guarantee",
        options=gas_options,
        label_visibility="collapsed",
    )

    # build one container with 8 columns for each parameter
    for parameter in [
        "flow",
        "suction_pressure",
        "suction_temperature",
        "discharge_pressure",
        "discharge_temperature",
        "power",
        "speed",
        "head",
        "efficiency",
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

        parameters_col.markdown(f"{parameters_map[parameter]['label']}")

        # use same units for section 1 and 2 in data sheet
        parameters_map[parameter]["section_1"]["data_sheet_units"] = parameters_map[
            parameter
        ]["section_2"]["data_sheet_units"] = units_col.selectbox(
            f"{parameter} units",
            options=parameters_map[parameter]["units"],
            key=f"{parameter}_units_section_1_point_guarantee",
            label_visibility="collapsed",
        )
        parameters_map[parameter]["section_1"]["point_guarantee"][
            "value"
        ] = first_section_col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_section_1_point_guarantee",
            label_visibility="collapsed",
        )
        parameters_map[parameter]["section_2"]["point_guarantee"][
            "value"
        ] = second_section_col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_section_2_point_guarantee",
            label_visibility="collapsed",
        )

number_of_test_points = 6
number_of_columns = number_of_test_points + 2

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

            for i, col in enumerate(parameter_columns):
                if i == 0:
                    col.markdown(f"{parameters_map[parameter]['label']}")
                elif i == 1:
                    parameters_map[parameter]["section_1"][
                        "test_units"
                    ] = col.selectbox(
                        f"{parameter} units",
                        options=parameters_map[parameter]["units"],
                        key=f"{parameter}_units_section_1",
                        label_visibility="collapsed",
                    )
                else:
                    parameters_map[parameter]["section_1"][f"point_{i - 1}"][
                        "value"
                    ] = col.text_input(
                        f"{parameter} value.",
                        key=f"{parameter}_section_1_point_{i - 1}",
                        label_visibility="collapsed",
                    )

    with tab_section_2:
        # add title
        number_of_columns = number_of_test_points + 2
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
            for i, col in enumerate(parameter_columns):
                if i == 0:
                    col.markdown(f"{parameters_map[parameter]['label']}")
                elif i == 1:
                    parameters_map[parameter]["section_2"][
                        "test_units"
                    ] = col.selectbox(
                        f"{parameter} units",
                        options=parameters_map[parameter]["units"],
                        key=f"{parameter}_units_section_2",
                        label_visibility="collapsed",
                    )
                else:
                    parameters_map[parameter]["section_2"][f"point_{i - 1}"][
                        "value"
                    ] = col.text_input(
                        f"{parameter} value.",
                        key=f"{parameter}_section_2_point_{i - 1}",
                        label_visibility="collapsed",
                    )

# add calculate button
back_to_back = None
calculate_button = st.button("Calculate", type="primary", use_container_width=True)


def get_gas_composition(gas_name):
    """Get gas composition from gas name.

    Parameters
    ----------
    gas_name : str
        Name of gas.

    Returns
    -------
    gas_composition : dict
        Gas composition.
    """
    gas_composition = {}
    for gas in gas_compositions_table.keys():
        if gas_compositions_table[gas]["name"] == gas_name:
            for i in range(len(default_components) - 1):
                component = gas_compositions_table[gas][f"component_{i}"]
                molar_fraction = float(
                    gas_compositions_table[gas][f"molar_fraction_{i}"]
                )
                if molar_fraction != 0:
                    gas_composition[component] = molar_fraction

    return gas_composition


# create test points for first section
first_section_test_points = []
second_section_test_points = []
kwargs = {}

if calculate_button:
    print("calculating")
    # calculate guarantee point for first and second section
    kwargs_guarantee_section_1 = {}
    kwargs_guarantee_section_2 = {}

    # get gas composition from selected gas
    gas_composition_data_sheet = {}
    gas_composition_data_sheet["section_1_point_guarantee"] = get_gas_composition(
        gas_name_section_1_point_guarantee
    )
    gas_composition_data_sheet["section_2_point_guarantee"] = get_gas_composition(
        gas_name_section_2_point_guarantee
    )

    for section, section_kws in zip(
        ["section_1", "section_2"],
        [kwargs_guarantee_section_1, kwargs_guarantee_section_2],
    ):
        # to get data sheet units we use parameters_map[paramter]["selected_units"]
        # since first and section share the same units in the forms
        if (
            Q_(0, parameters_map["flow"][section]["data_sheet_units"]).dimensionality
            == "[mass] / [time]"
        ):
            section_kws["flow_m"] = Q_(
                float(st.session_state[f"flow_{section}_point_guarantee"]),
                parameters_map["flow"][section]["data_sheet_units"],
            )
        else:
            section_kws["flow_v"] = Q_(
                float(st.session_state[f"flow_{section}_point_guarantee"]),
                parameters_map["flow"][section]["data_sheet_units"],
            )
        section_kws["suc"] = ccp.State(
            p=Q_(
                float(st.session_state[f"suction_pressure_{section}_point_guarantee"]),
                parameters_map["suction_pressure"][section]["data_sheet_units"],
            ),
            T=Q_(
                float(
                    st.session_state[f"suction_temperature_{section}_point_guarantee"]
                ),
                parameters_map["suction_temperature"][section]["data_sheet_units"],
            ),
            fluid=gas_composition_data_sheet[f"{section}_point_guarantee"],
        )
        section_kws["disch"] = ccp.State(
            p=Q_(
                float(
                    st.session_state[f"discharge_pressure_{section}_point_guarantee"]
                ),
                parameters_map["discharge_pressure"][section]["data_sheet_units"],
            ),
            T=Q_(
                float(
                    st.session_state[
                        f"discharge_temperature_{section}_point_guarantee"
                    ],
                ),
                parameters_map["discharge_temperature"][section]["data_sheet_units"],
            ),
            fluid=gas_composition_data_sheet[f"{section}_point_guarantee"],
        )
        section_kws["speed"] = Q_(
            float(st.session_state[f"speed_{section}_point_guarantee"]),
            parameters_map["speed"][section]["data_sheet_units"],
        )
        section_kws["b"] = Q_(
            float(st.session_state[f"b_{section}_point_guarantee"]),
            parameters_map["b"][section]["data_sheet_units"],
        )
        section_kws["D"] = Q_(
            float(st.session_state[f"D_{section}_point_guarantee"]),
            parameters_map["D"][section]["data_sheet_units"],
        )

    guarantee_point_section_1 = ccp.Point(
        **kwargs_guarantee_section_1,
    )
    guarantee_point_section_2 = ccp.Point(
        **kwargs_guarantee_section_2,
    )

    for section in ["section_1", "section_2"]:
        for i in range(1, number_of_test_points + 1):
            kwargs = {}
            # check if at least flow, suction pressure and suction temperature are filled
            if (
                st.session_state[f"flow_{section}_point_{i}"] == ""
                or st.session_state[f"suction_pressure_{section}_point_{i}"] == ""
                or st.session_state[f"suction_temperature_{section}_point_{i}"] == ""
            ):
                if i < 6:
                    st.warning(f"Please fill the data for point {i}")
                continue
            else:
                calculate_button = False
                if (
                    Q_(0, parameters_map["flow"][section]["test_units"]).dimensionality
                    == "[mass] / [time]"
                ):
                    if st.session_state[f"flow_{section}_point_{i}"]:
                        kwargs["flow_m"] = Q_(
                            float(st.session_state[f"flow_{section}_point_{i}"]),
                            parameters_map["flow"][section]["test_units"],
                        )
                    else:
                        kwargs["flow_m"] = None
                else:
                    if st.session_state[f"flow_{section}_point_{i}"]:
                        kwargs["flow_v"] = Q_(
                            float(st.session_state[f"flow_{section}_point_{i}"]),
                            parameters_map["flow"][section]["test_units"],
                        )
                    else:
                        kwargs["flow_v"] = None
                kwargs["suc"] = ccp.State(
                    p=Q_(
                        float(
                            st.session_state[f"suction_pressure_{section}_point_{i}"]
                        ),
                        parameters_map["suction_pressure"][section]["test_units"],
                    ),
                    T=Q_(
                        float(
                            st.session_state[f"suction_temperature_{section}_point_{i}"]
                        ),
                        parameters_map["suction_temperature"][section]["test_units"],
                    ),
                    fluid={"CO2": 1},
                )
                kwargs["disch"] = ccp.State(
                    p=Q_(
                        float(
                            st.session_state[f"discharge_pressure_{section}_point_{i}"]
                        ),
                        parameters_map["discharge_pressure"][section]["test_units"],
                    ),
                    T=Q_(
                        float(
                            st.session_state[
                                f"discharge_temperature_{section}_point_{i}"
                            ]
                        ),
                        parameters_map["discharge_temperature"][section]["test_units"],
                    ),
                    fluid={"CO2": 1},
                )
                if (
                    st.session_state[f"casing_delta_T_{section}_point_{i}"]
                    and casing_heat_loss
                ):
                    kwargs["casing_temperature"] = Q_(
                        float(st.session_state[f"casing_delta_T_{section}_point_{i}"]),
                        parameters_map["casing_delta_T"][section]["test_units"],
                    )
                    kwargs["ambient_temperature"] = 0
                else:
                    kwargs["casing_temperature"] = 0
                    kwargs["ambient_temperature"] = 0

                if calculate_leakages:
                    if (
                        st.session_state[f"balance_line_flow_m_{section}_point_{i}"]
                        != ""
                    ):
                        kwargs["balance_line_flow_m"] = Q_(
                            float(
                                st.session_state[
                                    f"balance_line_flow_m_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["balance_line_flow_m"][section][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["balance_line_flow_m"] = None
                    if st.session_state[f"seal_gas_flow_m_{section}_point_{i}"] != "":
                        kwargs["seal_gas_flow_m"] = Q_(
                            float(
                                st.session_state[f"seal_gas_flow_m_{section}_point_{i}"]
                            ),
                            parameters_map["seal_gas_flow_m"][section]["test_units"],
                        )
                    else:
                        kwargs["seal_gas_flow_m"] = Q_(
                            0, parameters_map["seal_gas_flow_m"][section]["test_units"]
                        )

                    if section == "section_1":
                        if (
                            st.session_state[f"div_wall_flow_m_{section}_point_{i}"]
                            != ""
                        ):
                            kwargs["div_wall_flow_m"] = Q_(
                                float(
                                    st.session_state[
                                        f"div_wall_flow_m_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["div_wall_flow_m"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["div_wall_flow_m"] = None
                        if (
                            st.session_state[
                                f"first_section_discharge_flow_m_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["first_section_discharge_flow_m"] = Q_(
                                float(
                                    st.session_state[
                                        f"first_section_discharge_flow_m_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["first_section_discharge_flow_m"][
                                    section
                                ]["test_units"],
                            )
                        else:
                            kwargs["first_section_discharge_flow_m"] = None

                        kwargs["end_seal_upstream_pressure"] = Q_(
                            float(
                                st.session_state[
                                    f"end_seal_upstream_pressure_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["end_seal_upstream_pressure"][section][
                                "test_units"
                            ],
                        )
                        kwargs["end_seal_upstream_temperature"] = Q_(
                            float(
                                st.session_state[
                                    f"end_seal_upstream_temperature_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["end_seal_upstream_temperature"][section][
                                "test_units"
                            ],
                        )
                        kwargs["div_wall_upstream_pressure"] = Q_(
                            float(
                                st.session_state[
                                    f"div_wall_upstream_pressure_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["div_wall_upstream_pressure"][section][
                                "test_units"
                            ],
                        )
                        kwargs["div_wall_upstream_temperature"] = Q_(
                            float(
                                st.session_state[
                                    f"div_wall_upstream_temperature_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["div_wall_upstream_temperature"][section][
                                "test_units"
                            ],
                        )
                        if (
                            st.session_state[
                                f"seal_gas_temperature_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["seal_gas_temperature"] = Q_(
                                float(
                                    st.session_state[
                                        f"seal_gas_temperature_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["seal_gas_temperature"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["seal_gas_temperature"] = Q_(
                                0,
                                parameters_map["seal_gas_temperature"][section][
                                    "test_units"
                                ],
                            )
                else:
                    pass
                    # TODO implement calculation without leakages

                kwargs["b"] = Q_(
                    float(st.session_state[f"b_{section}_point_guarantee"]),
                    parameters_map["b"][section]["data_sheet_units"],
                )
                kwargs["D"] = Q_(
                    float(st.session_state[f"D_{section}_point_guarantee"]),
                    parameters_map["D"][section]["data_sheet_units"],
                )
                kwargs["casing_area"] = Q_(
                    float(st.session_state[f"casing_area_{section}_point_guarantee"]),
                    parameters_map["casing_area"][section]["data_sheet_units"],
                )

                if section == "section_1":
                    first_section_test_points.append(
                        PointFirstSection(
                            speed=Q_(
                                float(st.session_state[f"speed_section_1_point_{i}"]),
                                parameters_map["speed"][section]["test_units"],
                            ),
                            oil_flow_journal_bearing_de=Q_(31.515, "l/min"),
                            oil_flow_journal_bearing_nde=Q_(22.67, "l/min"),
                            oil_flow_thrust_bearing_nde=Q_(126.729, "l/min"),
                            oil_inlet_temperature=Q_(41.544, "degC"),
                            oil_outlet_temperature_de=Q_(49.727, "degC"),
                            oil_outlet_temperature_nde=Q_(50.621, "degC"),
                            **kwargs,
                        )
                    )
                elif section == "section_2":
                    second_section_test_points.append(
                        PointSecondSection(
                            speed=Q_(
                                float(st.session_state[f"speed_section_2_point_{i}"]),
                                parameters_map["speed"][section]["test_units"],
                            ),
                            **kwargs,
                        )
                    )

    back_to_back = BackToBack(
        guarantee_point_sec1=guarantee_point_section_1,
        guarantee_point_sec2=guarantee_point_section_2,
        test_points_sec1=first_section_test_points,
        test_points_sec2=second_section_test_points,
        reynolds_correction=reynolds_correction,
    )
    # pickle back_to_back object
    with open("back_to_back.pkl", "wb") as f:
        pickle.dump(back_to_back, f)

# if back_to_back is not defined, pickle the saved file
if back_to_back is None:
    with open("back_to_back.pkl", "rb") as f:
        back_to_back = pickle.load(f)


with st.expander("Results"):
    _t = "\u209C"
    _sp = "\u209B\u209A"
    conv = "\u1D9C" + "\u1D52" + "\u207F" + "\u1D5B"

    results_section_1 = {}
    results_section_2 = {}
    tab_results_section_1, tab_results_section_2 = st.tabs(
        ["First Section", "Second Section"]
    )

    for results, section, sec in zip(
        [results_section_1, results_section_2],
        ["section_1", "section_2"],
        ["sec1", "sec2"],
    ):
        results[f"φ{_t}"] = [
            round(p.phi.m, 5) for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"φ{_t} / φ{_sp}"] = [
            round(p.phi.m / getattr(back_to_back, f"guarantee_point_{sec}").phi.m, 5)
            for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results["vi / vd"] = [
            round(p.volume_ratio.m, 5)
            for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"(vi/vd){_t}/(vi/vd){_sp}"] = [
            round(
                p.volume_ratio.m
                / getattr(back_to_back, f"guarantee_point_{sec}").volume_ratio.m,
                5,
            )
            for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"Mach{_t}"] = [
            round(p.mach.m, 5) for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"Mach{_t} - Mach{_sp}"] = [
            round(p.mach.m - getattr(back_to_back, f"guarantee_point_{sec}").mach.m, 5)
            for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"Re{_t}"] = [
            round(p.reynolds.m, 5) for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"Re{_t} / Re{_sp}"] = [
            round(
                p.reynolds.m
                / getattr(back_to_back, f"guarantee_point_{sec}").reynolds.m,
                5,
            )
            for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"pd{conv} (bar)"] = [
            round(p.disch.p("bar").m, 5)
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"pd{conv}/pd_sp"] = [
            round(
                p.disch.p("bar").m
                / getattr(back_to_back, f"guarantee_point_{sec}").disch.p("bar").m,
                5,
            )
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"Head{_t} (kJ/kg)"] = [
            round(p.head.to("kJ/kg").m, 5)
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"Head{_t}/Head{_sp}"] = [
            round(
                p.head.to("kJ/kg").m
                / getattr(back_to_back, f"guarantee_point_{sec}").head.to("kJ/kg").m,
                5,
            )
            for p in getattr(back_to_back, f"test_points_{sec}")
        ]
        results[f"Head{conv} (kJ/kg)"] = [
            round(p.head.to("kJ/kg").m, 5)
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"Head{conv}/Head{_sp}"] = [
            round(
                p.head.to("kJ/kg").m
                / getattr(back_to_back, f"guarantee_point_{sec}").head.to("kJ/kg").m,
                5,
            )
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"Q{conv} (m3/h)"] = [
            round(p.flow_v.to("m³/h").m, 5)
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"Q{conv}/Q{_sp}"] = [
            round(
                p.flow_v.to("m³/h").m
                / getattr(back_to_back, f"guarantee_point_{sec}").flow_v.to("m³/h").m,
                5,
            )
            for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]
        results[f"W{_t} (kW)"] = [
            round(p.power.to("kW").m, 5)
            for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
        ]
        results[f"W{_t}/W{_sp}"] = [
            round(
                p.power.to("kW").m
                / getattr(back_to_back, f"guarantee_point_{sec}").power.to("kW").m,
                5,
            )
            for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
        ]
        results[f"W{conv} (kW)"] = [
            round(p.power.to("kW").m, 5)
            for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
        ]
        results[f"W{conv}/W{_sp}"] = [
            round(
                p.power.to("kW").m
                / getattr(back_to_back, f"guarantee_point_{sec}").power.to("kW").m,
                5,
            )
            for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
        ]
        results[f"Eff{_t}"] = [
            round(p.eff.m, 5) for p in getattr(back_to_back, f"points_flange_t_{sec}")
        ]
        results[f"Eff{conv}"] = [
            round(p.eff.m, 5) for p in getattr(back_to_back, f"points_flange_sp_{sec}")
        ]

        # create interpolated point with point method
        point_interpolated = getattr(back_to_back, f"point_{sec}")(
            flow_v=getattr(back_to_back, f"guarantee_point_{sec}").flow_v,
            speed=getattr(back_to_back, f"guarantee_point_{sec}").speed,
        )

        results[f"φ{_t}"].append(round(point_interpolated.phi.m, 5))
        results[f"φ{_t} / φ{_sp}"].append(
            round(
                point_interpolated.phi.m
                / getattr(back_to_back, f"guarantee_point_{sec}").phi.m,
                5,
            )
        )
        results["vi / vd"].append(round(point_interpolated.volume_ratio.m, 5))
        results[f"(vi/vd){_t}/(vi/vd){_sp}"].append(
            round(
                point_interpolated.volume_ratio.m
                / getattr(back_to_back, f"guarantee_point_{sec}").volume_ratio.m,
                5,
            )
        )
        results[f"Mach{_t}"].append(round(point_interpolated.mach.m, 5))
        results[f"Mach{_t} - Mach{_sp}"].append(
            round(
                point_interpolated.mach.m
                - getattr(back_to_back, f"guarantee_point_{sec}").mach.m,
                5,
            )
        )
        results[f"Re{_t}"].append(round(point_interpolated.reynolds.m, 5))
        results[f"Re{_t} / Re{_sp}"].append(
            round(
                point_interpolated.reynolds.m
                / getattr(back_to_back, f"guarantee_point_{sec}").reynolds.m,
                5,
            )
        )
        results[f"pd{conv} (bar)"].append(round(point_interpolated.disch.p("bar").m, 5))
        results[f"pd{conv}/pd_sp"].append(
            round(
                point_interpolated.disch.p("bar").m
                / getattr(back_to_back, f"guarantee_point_{sec}").disch.p("bar").m,
                5,
            )
        )
        results[f"Head{_t} (kJ/kg)"].append(
            round(point_interpolated.head.to("kJ/kg").m, 5)
        )
        results[f"Head{_t}/Head{_sp}"].append(
            round(
                point_interpolated.head.to("kJ/kg").m
                / getattr(back_to_back, f"guarantee_point_{sec}").head.to("kJ/kg").m,
                5,
            )
        )
        results[f"Head{conv} (kJ/kg)"].append(
            round(point_interpolated.head.to("kJ/kg").m, 5)
        )
        results[f"Head{conv}/Head{_sp}"].append(
            round(
                point_interpolated.head.to("kJ/kg").m
                / getattr(back_to_back, f"guarantee_point_{sec}").head.to("kJ/kg").m,
                5,
            )
        )
        results[f"Q{conv} (m3/h)"].append(
            round(point_interpolated.flow_v.to("m³/h").m, 5)
        )
        results[f"Q{conv}/Q{_sp}"].append(
            round(
                point_interpolated.flow_v.to("m³/h").m
                / getattr(back_to_back, f"guarantee_point_{sec}").flow_v.to("m³/h").m,
                5,
            )
        )
        results[f"W{_t} (kW)"].append(None)
        results[f"W{_t}/W{_sp}"].append(None)
        results[f"W{conv} (kW)"].append(round(point_interpolated.power.to("kW").m, 5))
        results[f"W{conv}/W{_sp}"].append(
            round(
                point_interpolated.power.to("kW").m
                / getattr(back_to_back, f"guarantee_point_{sec}").power.to("kW").m,
                5,
            )
        )
        results[f"Eff{_t}"].append(round(point_interpolated.eff.m, 5))
        results[f"Eff{conv}"].append(round(point_interpolated.eff.m, 5))

        df_results = pd.DataFrame(results)
        rename_index = {
            i: f"Point {i+1}"
            for i in range(len(getattr(back_to_back, f"points_flange_t_{sec}")))
        }
        rename_index[
            len(getattr(back_to_back, f"points_flange_t_{sec}"))
        ] = "Guarantee Point"

        df_results.rename(
            index=rename_index,
            inplace=True,
        )

        if section == "section_1":
            tab_results = tab_results_section_1
        else:
            tab_results = tab_results_section_2

        with tab_results:

            def highlight_cell(
                styled_df, df, row_index, col_index, lower_limit, higher_limit
            ):
                """Applies conditional formatting to a specific cell in a pandas DataFrame.

                Args:
                    df (pandas.DataFrame): The DataFrame to apply conditional formatting to.
                    row_index (int or str): The row index of the cell to highlight.
                    col_index (int or str): The column index of the cell to highlight.
                    lower_limit (float): The lower limit of the value range to highlight in green.
                    higher_limit (float): The higher limit of the value range to highlight in green.

                Returns:
                    pandas.io.formats.style.Styler: A styled DataFrame with the specified cell highlighted.
                """
                # create a copy of the DataFrame with styling

                # apply conditional formatting to the specific cell
                cell_value = df.loc[row_index, col_index]
                if cell_value >= lower_limit and cell_value <= higher_limit:
                    styled_df = styled_df.applymap(
                        lambda x: "background-color: green" if x == cell_value else ""
                    )
                else:
                    styled_df = styled_df.applymap(
                        lambda x: "background-color: red" if x == cell_value else ""
                    )

                return styled_df

            styled_df_results = df_results.style
            styled_df_results = highlight_cell(
                styled_df_results,
                df_results,
                "Guarantee Point",
                f"W{conv}/W{_sp}",
                0.0,
                1.04,
            )

            st.dataframe(
                styled_df_results.format(
                    "{:.2%}",
                    subset=[
                        f"φ{_t} / φ{_sp}",
                        f"pd{conv}/pd_sp",
                        f"(vi/vd){_t}/(vi/vd){_sp}",
                        f"Head{_t}/Head{_sp}",
                        f"Head{conv}/Head{_sp}",
                        f"Q{conv}/Q{_sp}",
                        f"W{_t}/W{_sp}",
                        f"W{conv}/W{_sp}",
                        f"Eff{_t}",
                        f"Eff{conv}",
                    ],
                ).format(
                    "{:.4e}",
                    subset=[
                        f"Re{_t}",
                    ],
                )
            )
            st.plotly_chart(getattr(back_to_back, f"imp_flange_sp_{sec}").head_plot())
