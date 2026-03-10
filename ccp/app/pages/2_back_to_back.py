import io
import streamlit as st
import ccp
import json
import pandas as pd
import base64
import zipfile
import toml
import time
import logging
from ccp.compressor import PointFirstSection, PointSecondSection, BackToBack
from ccp.config.utilities import r_getattr
from ccp.config.units import ureg
from pathlib import Path

from ccp.app.common import (
    pressure_units,
    polytropic_methods,
    parameters_map,
    specific_heat_calculate,
    density_calculate,
    get_gas_composition,
    get_index_selected_gas,
    highlight_cell,
    add_background_image,
    to_excel,
    convert,
    file_sidebar,
    gas_selection_form,
    init_sentry,
    oil_input_widgets,
    setup_page,
    get_fluid_list,
    run_app,
)

init_sentry()


def main():
    """The code has to be inside this main function to allow sentry to work."""
    Q_ = ccp.Q_

    setup_page()
    st.markdown(
        """
    ## Performance Test Back-to-Back Compressor
    """
    )

    def get_session():
        # if file is being loaded, session_name is set with the file name
        if "session_name" not in st.session_state:
            st.session_state.session_name = ""
        if "back_to_back" not in st.session_state:
            st.session_state.back_to_back = ""
        if "expander_state" not in st.session_state:
            st.session_state.expander_state = False
        if "ccp_version" not in st.session_state:
            st.session_state.ccp_version = ccp.__version__
        if "app_type" not in st.session_state:
            st.session_state.app_type = "back_to_back"
        for sec in ["sec1", "sec2"]:
            for curve in ["head", "power", "eff", "discharge_pressure"]:
                if f"fig_{curve}_{sec}" not in st.session_state:
                    st.session_state[f"fig_{curve}_{sec}"] = ""
        if "bearing_mechanical_losses" not in st.session_state:
            st.session_state.bearing_mechanical_losses = False
        if "oil_specific_heat" not in st.session_state:
            st.session_state.oil_specific_heat = False
        if "oil_iso" not in st.session_state:
            st.session_state.oil_iso = False

    get_session()

    def _load_back_to_back(my_zip, version):
        for name in my_zip.namelist():
            if name.endswith(".json"):
                session_state_data = convert(
                    json.loads(my_zip.read(name)), version
                )
                if "div_wall_flow_m_section_1_point_1" not in session_state_data:
                    raise ValueError("File is not a ccp back-to-back file.")
        for name in my_zip.namelist():
            if name.endswith(".png"):
                session_state_data[name.split(".")[0]] = my_zip.read(name)
            elif name.endswith(".toml"):
                back_to_back_file = convert(
                    io.StringIO(my_zip.read(name).decode("utf-8")), version
                )
                session_state_data[name.split(".")[0]] = BackToBack.load(
                    back_to_back_file
                )
        return session_state_data

    def _save_back_to_back(my_zip, session_state_dict_copy):
        for key, value in dict(session_state_dict_copy).items():
            if isinstance(
                value, (bytes, st.runtime.uploaded_file_manager.UploadedFile)
            ):
                if key.startswith("fig"):
                    my_zip.writestr(f"{key}.png", value)
                del session_state_dict_copy[key]
            if isinstance(value, BackToBack):
                my_zip.writestr(
                    f"{key}.toml", toml.dumps(value._dict_to_save())
                )
                del session_state_dict_copy[key]
        return session_state_dict_copy

    file_sidebar(_load_back_to_back, _save_back_to_back)

    def check_correct_separator(input):
        if "," in input:
            st.error("Please use '.' as decimal separator")

    # Gas selection
    fluid_list, default_components = get_fluid_list()
    gas_compositions_table = gas_selection_form(fluid_list, default_components)

    # add container with 4 columns and 2 rows
    with st.sidebar.expander("⚙️ Options"):
        reynolds_correction = st.checkbox("Reynolds Correction", value=True)
        casing_heat_loss = st.checkbox("Casing Heat Loss", value=True)
        bearing_mechanical_losses = st.checkbox("Bearing Mechanical Losses", value=True)
        calculate_leakages = st.checkbox(
            "Calculate Leakages",
            value=True,
        )
        seal_gas_flow = st.checkbox(
            "Seal Gas Flow",
            value=True,
        )

        # add a disabled flag in the parameters_map dict based on the checkbox
        if seal_gas_flow:
            parameters_map["seal_gas_flow_m"]["disabled"] = False
            parameters_map["seal_gas_temperature"]["disabled"] = False
        else:
            parameters_map["seal_gas_flow_m"]["disabled"] = True
            parameters_map["seal_gas_temperature"]["disabled"] = True
            parameters_map["seal_gas_flow_m"]["value"] = ""
            parameters_map["seal_gas_temperature"]["value"] = ""

        if calculate_leakages:
            parameters_map["balance_line_flow_m"]["disabled"] = False
            parameters_map["end_seal_upstream_pressure"]["disabled"] = False
            parameters_map["end_seal_upstream_temperature"]["disabled"] = False
            parameters_map["div_wall_flow_m"]["disabled"] = False
            parameters_map["div_wall_upstream_pressure"]["disabled"] = False
            parameters_map["div_wall_upstream_temperature"]["disabled"] = False
            parameters_map["first_section_discharge_flow_m"]["disabled"] = False
        else:
            parameters_map["balance_line_flow_m"]["disabled"] = True
            parameters_map["end_seal_upstream_pressure"]["disabled"] = True
            parameters_map["end_seal_upstream_temperature"]["disabled"] = True
            parameters_map["seal_gas_flow_m"]["disabled"] = True
            parameters_map["seal_gas_temperature"]["disabled"] = True
            parameters_map["div_wall_flow_m"]["disabled"] = True
            parameters_map["div_wall_upstream_pressure"]["disabled"] = True
            parameters_map["div_wall_upstream_temperature"]["disabled"] = True
            parameters_map["first_section_discharge_flow_m"]["disabled"] = True
            parameters_map["balance_line_flow_m"]["value"] = ""
            parameters_map["end_seal_upstream_pressure"]["value"] = ""
            parameters_map["end_seal_upstream_temperature"]["value"] = ""
            parameters_map["seal_gas_flow_m"]["value"] = ""
            parameters_map["seal_gas_temperature"]["value"] = ""
            parameters_map["div_wall_flow_m"]["value"] = ""
            parameters_map["div_wall_upstream_pressure"]["value"] = ""
            parameters_map["div_wall_upstream_temperature"]["value"] = ""
            parameters_map["first_section_discharge_flow_m"]["value"] = ""

        variable_speed = st.checkbox("Variable Speed", value=True)
        show_points = st.checkbox(
            "Show Points",
            value=True,
            help="If marked, shows points in the plotted curves in addition to interpolation.",
        )
        # add text input for the ambient pressure
        st.text("Ambient Pressure")
        ambient_pressure_magnitude_col, ambient_pressure_unit_col = st.columns(2)
        with ambient_pressure_magnitude_col:
            ambient_pressure_magnitude = st.text_input(
                "Ambient Pressure",
                value=1.01325,
                key="ambient_pressure_magnitude",
                label_visibility="collapsed",
            )
        with ambient_pressure_unit_col:
            ambient_pressure_unit = st.selectbox(
                "Unit",
                options=pressure_units,
                index=pressure_units.index("bar"),
                key="ambient_pressure_unit",
                label_visibility="collapsed",
            )
        ambient_pressure = Q_(
            float(ambient_pressure_magnitude), ambient_pressure_unit
        ).to("bar")
        ureg.define(f"barg = 1 * bar; offset: {ambient_pressure.magnitude}")

        (
            oil_specific_heat,
            oil_specific_heat_value,
            oil_density_value,
            oil_iso,
            oil_iso_classification,
        ) = oil_input_widgets()

        st.text("Polytropic Method")
        polytropic_method = st.selectbox(
            "Polytropic",
            options=polytropic_methods.keys(),
            index=list(polytropic_methods.keys()).index("Sandberg-Colby"),
            key="polytropic_method",
            label_visibility="collapsed",
        )

    ccp.config.POLYTROPIC_METHOD = polytropic_methods[polytropic_method]

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

    with st.expander("Data Sheet", expanded=st.session_state.expander_state):
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
        gas_options = [
            st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_compositions_table)
        ]

        gas_name_section_1_point_guarantee = points_gas_columns[2].selectbox(
            "gas_section_1_point_guarantee",
            options=gas_options,
            label_visibility="collapsed",
            index=get_index_selected_gas(gas_options,"gas_section_1_point_guarantee"),
        )
        gas_name_section_2_point_guarantee = points_gas_columns[3].selectbox(
            "gas_section_2_point_guarantee",
            options=gas_options,
            label_visibility="collapsed",
            index=get_index_selected_gas(gas_options,"gas_section_2_point_guarantee"),
        )

        # build one container with 8 columns for each parameter
        for parameter in [
            "flow",
            "suction_pressure",
            "suction_temperature",
            "discharge_pressure",
            "discharge_temperature",
            "power",
            "power_shaft",
            "speed",
            "head",
            "eff",
            "b",
            "D",
            "surface_roughness",
            "casing_area",
        ]:
            parameter_container = st.container()
            (
                parameters_col,
                units_col,
                first_section_col,
                second_section_col,
            ) = parameter_container.columns(4, gap="small")

            parameters_col.markdown(
                f"{parameters_map[parameter]['label']}",
                help=f"{parameters_map[parameter].get('help', '')}",
            )

            # use same units for section 1 and 2 in data sheet
            parameters_map[parameter]["section_1"]["data_sheet_units"] = parameters_map[
                parameter
            ]["section_2"]["data_sheet_units"] = units_col.selectbox(
                f"{parameter} units",
                options=parameters_map[parameter]["units"],
                key=f"{parameter}_units_section_1_point_guarantee",
                label_visibility="collapsed",
            )
            parameters_map[parameter]["section_1"]["point_guarantee"]["value"] = (
                first_section_col.text_input(
                    f"{parameter} value.",
                    key=f"{parameter}_section_1_point_guarantee",
                    label_visibility="collapsed",
                )
            )
            check_correct_separator(
                parameters_map[parameter]["section_1"]["point_guarantee"]
            )
            parameters_map[parameter]["section_2"]["point_guarantee"]["value"] = (
                second_section_col.text_input(
                    f"{parameter} value.",
                    key=f"{parameter}_section_2_point_guarantee",
                    label_visibility="collapsed",
                )
            )
            check_correct_separator(
                parameters_map[parameter]["section_2"]["point_guarantee"]
            )

    with st.expander("Curves", expanded=st.session_state.expander_state):
        # add upload button for each section curve
        # check if fig_dict was created when loading state. Otherwise, create it
        plot_limits = {}
        fig_dict_uploaded = {}

        for curve in ["head", "eff", "discharge_pressure", "power"]:
            st.markdown(f"### {parameters_map[curve]['label']}")
            parameter_container = st.empty()
            first_section_col, second_section_col = parameter_container.columns(
                2, gap="small"
            )
            plot_limits[curve] = {}
            # create upload button for each section
            for section in ["sec1", "sec2"]:
                plot_limits[curve][section] = {}
                if section == "sec1":
                    section_col = first_section_col
                else:
                    section_col = second_section_col
                # create upload button for each section
                fig_dict_uploaded[f"uploaded_fig_{curve}_{section}"] = (
                    section_col.file_uploader(
                        f"Upload {curve} curve for {section}.",
                        type=["png"],
                        key=f"uploaded_fig_{curve}_{section}",
                        label_visibility="collapsed",
                    )
                )

                if fig_dict_uploaded[f"uploaded_fig_{curve}_{section}"] is not None:
                    st.session_state[f"fig_{curve}_{section}"] = fig_dict_uploaded[
                        f"uploaded_fig_{curve}_{section}"
                    ].read()

                # add container to x range
                for axis in ["x", "y"]:
                    with st.container():
                        (
                            plot_limit,
                            units_col,
                            lower_value_col,
                            upper_value_col,
                        ) = section_col.columns(4, gap="small")
                        plot_limit.markdown(f"{axis} range")
                        plot_limits[curve][section][f"{axis}"] = {}
                        plot_limits[curve][section][f"{axis}"]["lower_limit"] = (
                            lower_value_col.text_input(
                                "Lower limit",
                                key=f"{axis}_{curve}_{section}_lower",
                                label_visibility="collapsed",
                            )
                        )
                        check_correct_separator(
                            plot_limits[curve][section][f"{axis}"]["lower_limit"]
                        )
                        plot_limits[curve][section][f"{axis}"]["upper_limit"] = (
                            upper_value_col.text_input(
                                "Upper limit",
                                key=f"{axis}_{curve}_{section}_upper",
                                label_visibility="collapsed",
                            )
                        )
                        check_correct_separator(
                            plot_limits[curve][section][f"{axis}"]["upper_limit"]
                        )
                        if axis == "x":
                            plot_limits[curve][section][f"{axis}"]["units"] = (
                                units_col.selectbox(
                                    f"{parameter} units",
                                    options=parameters_map["flow_v"]["units"],
                                    key=f"{axis}_{curve}_{section}_flow_units",
                                    label_visibility="collapsed",
                                )
                            )
                        else:
                            plot_limits[curve][section][f"{axis}"]["units"] = (
                                units_col.selectbox(
                                    f"{parameter} units",
                                    options=parameters_map[curve]["units"],
                                    key=f"{axis}_{curve}_{section}_units",
                                    label_visibility="collapsed",
                                )
                            )

    number_of_test_points = 6
    number_of_columns = number_of_test_points + 2

    with st.expander("Test Data", expanded=st.session_state.expander_state):
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
            point_gas = st.container()
            point_gas_columns = point_gas.columns(number_of_columns, gap="small")
            for i, col in enumerate(point_gas_columns):
                if i == 0:
                    col.markdown("Gas Selection")
                elif i == 1:
                    col.markdown("")
                else:
                    gas_options = [
                        st.session_state[f"gas_{i}"]
                        for i, gas in enumerate(gas_compositions_table)
                    ]
                    col.selectbox(
                        f"gas_section_1_point_{i - 1}",
                        options=gas_options,
                        label_visibility="collapsed",
                        index=get_index_selected_gas(gas_options,f"gas_section_1_point_{i - 1}"),
                        key=f"gas_section_1_point_{i - 1}",
                    )

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
                "oil_flow_journal_bearing_de",
                "oil_flow_journal_bearing_nde",
                "oil_flow_thrust_bearing_nde",
                "oil_inlet_temperature",
                "oil_outlet_temperature_de",
                "oil_outlet_temperature_nde",
            ]:
                parameter_container = st.container()
                parameter_columns = parameter_container.columns(
                    number_of_columns, gap="small"
                )

                for i, col in enumerate(parameter_columns):
                    if i == 0:
                        col.markdown(
                            f"{parameters_map[parameter]['label']}",
                            help=f"{parameters_map[parameter].get('help', '')}",
                        )
                    elif i == 1:
                        parameters_map[parameter]["section_1"]["test_units"] = (
                            col.selectbox(
                                f"{parameter} units",
                                options=parameters_map[parameter]["units"],
                                key=f"{parameter}_units_section_1",
                                label_visibility="collapsed",
                                disabled=parameters_map[parameter].get(
                                    "disabled", False
                                ),
                            )
                        )
                    else:
                        parameters_map[parameter]["section_1"][f"point_{i - 1}"][
                            "value"
                        ] = col.text_input(
                            f"{parameter} value.",
                            key=f"{parameter}_section_1_point_{i - 1}",
                            label_visibility="collapsed",
                            disabled=parameters_map[parameter].get("disabled", False),
                        )
                        check_correct_separator(
                            parameters_map[parameter]["section_1"][f"point_{i - 1}"][
                                "value"
                            ]
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

            # gas selection
            point_gas = st.container()
            point_gas_columns = point_gas.columns(number_of_columns, gap="small")
            for i, col in enumerate(point_gas_columns):
                if i == 0:
                    col.markdown("Gas Selection")
                elif i == 1:
                    col.markdown("")
                else:
                    gas_options = [
                        st.session_state[f"gas_{i}"]
                        for i, gas in enumerate(gas_compositions_table)
                    ]
                    col.selectbox(
                        f"gas_section_2_point_{i - 1}",
                        options=gas_options,
                        label_visibility="collapsed",
                        index=get_index_selected_gas(gas_options,f"gas_section_2_point_{i - 1}"),
                        key=f"gas_section_2_point_{i - 1}",
                    )

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
                "oil_flow_journal_bearing_de",
                "oil_flow_journal_bearing_nde",
                "oil_flow_thrust_bearing_nde",
                "oil_inlet_temperature",
                "oil_outlet_temperature_de",
                "oil_outlet_temperature_nde",
            ]:
                parameter_container = st.container()
                parameter_columns = parameter_container.columns(
                    number_of_columns, gap="small"
                )
                for i, col in enumerate(parameter_columns):
                    if i == 0:
                        col.markdown(
                            f"{parameters_map[parameter]['label']}",
                            help=f"{parameters_map[parameter].get('help', '')}",
                        )
                    elif i == 1:
                        parameters_map[parameter]["section_2"]["test_units"] = (
                            col.selectbox(
                                f"{parameter} units",
                                options=parameters_map[parameter]["units"],
                                key=f"{parameter}_units_section_2",
                                label_visibility="collapsed",
                                disabled=parameters_map[parameter].get(
                                    "disabled", False
                                ),
                            )
                        )
                    else:
                        parameters_map[parameter]["section_2"][f"point_{i - 1}"][
                            "value"
                        ] = col.text_input(
                            f"{parameter} value.",
                            key=f"{parameter}_section_2_point_{i - 1}",
                            label_visibility="collapsed",
                            disabled=parameters_map[parameter].get("disabled", False),
                        )
                        check_correct_separator(
                            parameters_map[parameter]["section_2"][f"point_{i - 1}"][
                                "value"
                            ]
                        )

    # add calculate button
    back_to_back = None

    with st.container():
        calculate_col, calculate_speed_col = st.columns([1, 1])
        calculate_button = calculate_col.button(
            "Calculate",
            type="primary",
            width="stretch",
            help="Calculate results using the data sheet speed.",
        )
        calculate_speed_button = calculate_speed_col.button(
            "Calculate Speed",
            type="primary",
            width="stretch",
            help="Calculate speed to match the second section discharge pressure.",
        )

    # create test points for first section
    first_section_test_points = []
    second_section_test_points = []
    kwargs = {}

    if calculate_button or calculate_speed_button:
        progress_value = 0
        progress_bar = st.progress(progress_value, text="Calculating...")
        # calculate guarantee point for first and second section
        kwargs_guarantee_section_1 = {}
        kwargs_guarantee_section_2 = {}

        # get gas composition from selected gas
        gas_composition_data_sheet = {}
        gas_composition_data_sheet["section_1_point_guarantee"] = get_gas_composition(
            gas_name_section_1_point_guarantee,
            gas_compositions_table,
            default_components,
        )
        gas_composition_data_sheet["section_2_point_guarantee"] = get_gas_composition(
            gas_name_section_2_point_guarantee,
            gas_compositions_table,
            default_components,
        )

        for section, section_kws in zip(
            ["section_1", "section_2"],
            [kwargs_guarantee_section_1, kwargs_guarantee_section_2],
        ):
            # to get data sheet units we use parameters_map[paramter]["selected_units"]
            # since first and section share the same units in the forms
            if (
                Q_(
                    0, parameters_map["flow"][section]["data_sheet_units"]
                ).dimensionality
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
                    float(
                        st.session_state[f"suction_pressure_{section}_point_guarantee"]
                    ),
                    parameters_map["suction_pressure"][section]["data_sheet_units"],
                ),
                T=Q_(
                    float(
                        st.session_state[
                            f"suction_temperature_{section}_point_guarantee"
                        ]
                    ),
                    parameters_map["suction_temperature"][section]["data_sheet_units"],
                ),
                fluid=gas_composition_data_sheet[f"{section}_point_guarantee"],
            )
            section_kws["disch"] = ccp.State(
                p=Q_(
                    float(
                        st.session_state[
                            f"discharge_pressure_{section}_point_guarantee"
                        ]
                    ),
                    parameters_map["discharge_pressure"][section]["data_sheet_units"],
                ),
                T=Q_(
                    float(
                        st.session_state[
                            f"discharge_temperature_{section}_point_guarantee"
                        ],
                    ),
                    parameters_map["discharge_temperature"][section][
                        "data_sheet_units"
                    ],
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
            power_guarantee = Q_(
                float(st.session_state[f"power_{section}_point_guarantee"]),
                parameters_map["power"][section]["data_sheet_units"],
            )
            if bearing_mechanical_losses:
                if st.session_state[f"power_shaft_{section}_point_guarantee"] == "":
                    power_shaft_guarantee = Q_(
                        float(st.session_state[f"power_{section}_point_guarantee"]),
                        parameters_map["power"][section]["data_sheet_units"],
                    ).to("kW")
                else:
                    power_shaft_guarantee = Q_(
                        float(
                            st.session_state[f"power_shaft_{section}_point_guarantee"]
                        ),
                        parameters_map["power_shaft"][section]["data_sheet_units"],
                    ).to("kW")
                section_kws["power_losses"] = power_shaft_guarantee - power_guarantee
            else:
                section_kws["power_losses"] = Q_(0, "W")

        time.sleep(0.1)
        progress_value += 5
        progress_bar.progress(progress_value, text="Calculating guarantee points...")
        guarantee_point_section_1 = ccp.Point(
            **kwargs_guarantee_section_1,
        )
        guarantee_point_section_2 = ccp.Point(
            **kwargs_guarantee_section_2,
        )

        for section in ["section_1", "section_2"]:
            for i in range(1, number_of_test_points + 1):
                time.sleep(0.1)
                progress_value += 1
                progress_bar.progress(
                    progress_value,
                    text=f"Calculating test point: {section} point {i}...",
                )

                kwargs = {}
                # check if at least flow, suction pressure and suction temperature are filled
                if (
                    st.session_state[f"flow_{section}_point_{i}"] == ""
                    or st.session_state[f"suction_pressure_{section}_point_{i}"] == ""
                    or st.session_state[f"suction_temperature_{section}_point_{i}"]
                    == ""
                ):
                    if i < 6:
                        st.warning(f"Please fill the data for point {i}")
                    continue
                else:
                    calculate_button = False
                    if (
                        Q_(
                            0, parameters_map["flow"][section]["test_units"]
                        ).dimensionality
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
                                st.session_state[
                                    f"suction_pressure_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["suction_pressure"][section]["test_units"],
                        ),
                        T=Q_(
                            float(
                                st.session_state[
                                    f"suction_temperature_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["suction_temperature"][section][
                                "test_units"
                            ],
                        ),
                        fluid=get_gas_composition(
                            st.session_state[f"gas_{section}_point_{i}"],
                            gas_compositions_table,
                            default_components,
                        ),
                    )
                    kwargs["disch"] = ccp.State(
                        p=Q_(
                            float(
                                st.session_state[
                                    f"discharge_pressure_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["discharge_pressure"][section]["test_units"],
                        ),
                        T=Q_(
                            float(
                                st.session_state[
                                    f"discharge_temperature_{section}_point_{i}"
                                ]
                            ),
                            parameters_map["discharge_temperature"][section][
                                "test_units"
                            ],
                        ),
                        fluid=get_gas_composition(
                            st.session_state[f"gas_{section}_point_{i}"],
                            gas_compositions_table,
                            default_components,
                        ),
                    )
                    if (
                        st.session_state[f"casing_delta_T_{section}_point_{i}"]
                        and casing_heat_loss
                    ):
                        kwargs["casing_temperature"] = Q_(
                            float(
                                st.session_state[f"casing_delta_T_{section}_point_{i}"]
                            ),
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
                        if (
                            seal_gas_flow
                            and st.session_state[f"seal_gas_flow_m_{section}_point_{i}"]
                            != ""
                        ):
                            kwargs["seal_gas_flow_m"] = Q_(
                                float(
                                    st.session_state[
                                        f"seal_gas_flow_m_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["seal_gas_flow_m"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["seal_gas_flow_m"] = Q_(
                                0,
                                parameters_map["seal_gas_flow_m"][section][
                                    "test_units"
                                ],
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
                                parameters_map["end_seal_upstream_temperature"][
                                    section
                                ]["test_units"],
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
                                parameters_map["div_wall_upstream_temperature"][
                                    section
                                ]["test_units"],
                            )
                            if (
                                seal_gas_flow
                                and st.session_state[
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

                    kwargs["bearing_mechanical_losses"] = bearing_mechanical_losses
                    if bearing_mechanical_losses:
                        if (
                            st.session_state[
                                f"oil_flow_journal_bearing_de_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["oil_flow_journal_bearing_de"] = Q_(
                                float(
                                    st.session_state[
                                        f"oil_flow_journal_bearing_de_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["oil_flow_journal_bearing_de"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["oil_flow_journal_bearing_nde"] = None
                        if (
                            st.session_state[
                                f"oil_flow_journal_bearing_nde_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["oil_flow_journal_bearing_nde"] = Q_(
                                float(
                                    st.session_state[
                                        f"oil_flow_journal_bearing_nde_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["oil_flow_journal_bearing_nde"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["oil_flow_thrust_bearing_nde"] = None
                        if (
                            st.session_state[
                                f"oil_flow_thrust_bearing_nde_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["oil_flow_thrust_bearing_nde"] = Q_(
                                float(
                                    st.session_state[
                                        f"oil_flow_thrust_bearing_nde_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["oil_flow_thrust_bearing_nde"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["oil_inlet_temperature"] = None
                        if (
                            st.session_state[
                                f"oil_inlet_temperature_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["oil_inlet_temperature"] = Q_(
                                float(
                                    st.session_state[
                                        f"oil_inlet_temperature_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["oil_inlet_temperature"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["oil_outlet_temperature_de"] = None
                        if (
                            st.session_state[
                                f"oil_outlet_temperature_de_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["oil_outlet_temperature_de"] = Q_(
                                float(
                                    st.session_state[
                                        f"oil_outlet_temperature_de_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["oil_outlet_temperature_de"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["oil_outlet_temperature_nde"] = None
                        if (
                            st.session_state[
                                f"oil_outlet_temperature_nde_{section}_point_{i}"
                            ]
                            != ""
                        ):
                            kwargs["oil_outlet_temperature_nde"] = Q_(
                                float(
                                    st.session_state[
                                        f"oil_outlet_temperature_nde_{section}_point_{i}"
                                    ]
                                ),
                                parameters_map["oil_outlet_temperature_nde"][section][
                                    "test_units"
                                ],
                            )
                        else:
                            kwargs["oil_outlet_temperature_nde"] = None
                    if oil_iso and bearing_mechanical_losses:
                        oil_specific_heat_de = specific_heat_calculate(
                            kwargs["oil_inlet_temperature"],
                            kwargs["oil_outlet_temperature_de"],
                            oil_iso_classification,
                        )
                        oil_specific_heat_nde = specific_heat_calculate(
                            kwargs["oil_inlet_temperature"],
                            kwargs["oil_outlet_temperature_nde"],
                            oil_iso_classification,
                        )

                        oil_density_de = density_calculate(
                            kwargs["oil_inlet_temperature"],
                            kwargs["oil_outlet_temperature_de"],
                            oil_iso_classification,
                        )
                        oil_density_nde = density_calculate(
                            kwargs["oil_inlet_temperature"],
                            kwargs["oil_outlet_temperature_nde"],
                            oil_iso_classification,
                        )

                        kwargs["oil_specific_heat_de"] = oil_specific_heat_de
                        kwargs["oil_specific_heat_nde"] = oil_specific_heat_nde

                        kwargs["oil_density_de"] = oil_density_de
                        kwargs["oil_density_nde"] = oil_density_nde

                    elif oil_specific_heat and bearing_mechanical_losses:
                        kwargs["oil_specific_heat_de"] = oil_specific_heat_value
                        kwargs["oil_specific_heat_nde"] = oil_specific_heat_value
                        kwargs["oil_density_de"] = oil_density_value
                        kwargs["oil_density_nde"] = oil_density_value

                    kwargs["b"] = Q_(
                        float(st.session_state[f"b_{section}_point_guarantee"]),
                        parameters_map["b"][section]["data_sheet_units"],
                    )
                    kwargs["D"] = Q_(
                        float(st.session_state[f"D_{section}_point_guarantee"]),
                        parameters_map["D"][section]["data_sheet_units"],
                    )
                    kwargs["casing_area"] = Q_(
                        float(
                            st.session_state[f"casing_area_{section}_point_guarantee"]
                        ),
                        parameters_map["casing_area"][section]["data_sheet_units"],
                    )
                    kwargs["surface_roughness"] = Q_(
                        float(
                            st.session_state[
                                f"surface_roughness_{section}_point_guarantee"
                            ]
                        ),
                        parameters_map["surface_roughness"][section][
                            "data_sheet_units"
                        ],
                    )
                    time.sleep(0.1)
                    progress_value += 2
                    progress_bar.progress(
                        progress_value, text="Calculating test points..."
                    )
                    if section == "section_1":
                        first_section_test_points.append(
                            PointFirstSection(
                                speed=Q_(
                                    float(
                                        st.session_state[f"speed_section_1_point_{i}"]
                                    ),
                                    parameters_map["speed"][section]["test_units"],
                                ),
                                **kwargs,
                            )
                        )
                    elif section == "section_2":
                        second_section_test_points.append(
                            PointSecondSection(
                                speed=Q_(
                                    float(
                                        st.session_state[f"speed_section_2_point_{i}"]
                                    ),
                                    parameters_map["speed"][section]["test_units"],
                                ),
                                **kwargs,
                            )
                        )
        time.sleep(0.1)
        progress_value += 10
        progress_bar.progress(progress_value, text="Converting points...")
        back_to_back = BackToBack(
            guarantee_point_sec1=guarantee_point_section_1,
            guarantee_point_sec2=guarantee_point_section_2,
            test_points_sec1=first_section_test_points,
            test_points_sec2=second_section_test_points,
            reynolds_correction=reynolds_correction,
            bearing_mechanical_losses=bearing_mechanical_losses,
        )

        if calculate_speed_button:
            time.sleep(0.1)
            progress_value += 10
            progress_bar.progress(progress_value, text="Finding speed...")
            back_to_back = back_to_back.calculate_speed_to_match_discharge_pressure()

        time.sleep(0.1)
        progress_bar.progress(100, text="Done!")

        # add back_to_back object to session state
        st.session_state["back_to_back"] = back_to_back

    # if back_to_back is not defined, pickle the saved file
    if (
        st.session_state["back_to_back"] is not None
        and st.session_state["back_to_back"] != ""
    ):
        back_to_back = st.session_state["back_to_back"]

    if (
        st.session_state["back_to_back"] is not None
        and st.session_state["back_to_back"] != ""
    ):
        with st.expander("Results"):
            st.write(
                f"Final speed used in calculation: {back_to_back.speed_operational.to('rpm').m:.2f} RPM"
            )
            _t = "\u209c"
            _sp = "\u209b\u209a"
            conv = "\u1d9c" + "\u1d52" + "\u207f" + "\u1d5b"

            results_section_1 = {}
            results_section_2 = {}
            tab_results_section_1, tab_results_section_2 = st.tabs(
                ["First Section", "Second Section"]
            )
            if back_to_back:
                # create interpolated point with point method
                point_interpolated_sec1 = getattr(back_to_back, "point_sec1")(
                    flow_v=getattr(back_to_back, "guarantee_point_sec1").flow_v,
                    speed=back_to_back.speed_operational,
                )
                point_interpolated_sec2 = getattr(back_to_back, "point_sec2")(
                    flow_v=getattr(back_to_back, "guarantee_point_sec2").flow_v,
                    speed=back_to_back.speed_operational,
                )

                for results, section, sec, point_interpolated in zip(
                    [results_section_1, results_section_2],
                    ["section_1", "section_2"],
                    ["sec1", "sec2"],
                    [point_interpolated_sec1, point_interpolated_sec2],
                ):
                    results[f"φ{_t}"] = [
                        round(p.phi.m, 5)
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"φ{_t} / φ{_sp}"] = [
                        round(
                            p.phi.m
                            / getattr(back_to_back, f"guarantee_point_{sec}").phi.m,
                            5,
                        )
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results["vi / vd"] = [
                        round(p.volume_ratio.m, 5)
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"(vi/vd){_t}/(vi/vd){_sp}"] = [
                        round(
                            p.volume_ratio.m
                            / getattr(
                                back_to_back, f"guarantee_point_{sec}"
                            ).volume_ratio.m,
                            5,
                        )
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"Mach{_t}"] = [
                        round(p.mach.m, 5)
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"Mach{_t} - Mach{_sp}"] = [
                        round(
                            p.mach.m
                            - getattr(back_to_back, f"guarantee_point_{sec}").mach.m,
                            5,
                        )
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"Re{_t}"] = [
                        round(p.reynolds.m, 5)
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"Re{_t} / Re{_sp}"] = [
                        round(
                            p.reynolds.m
                            / getattr(
                                back_to_back, f"guarantee_point_{sec}"
                            ).reynolds.m,
                            5,
                        )
                        for p in getattr(back_to_back, f"test_points_{sec}")
                    ]
                    results[f"pd{conv} (bar)"] = [
                        round(p.disch.p("bar").m, 5)
                        for p in getattr(back_to_back, f"points_flange_sp_{sec}")
                    ]
                    results[f"pd{conv}/pd{_sp}"] = [
                        round(
                            p.disch.p("bar").m
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .disch.p("bar")
                            .m,
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
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .head.to("kJ/kg")
                            .m,
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
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .head.to("kJ/kg")
                            .m,
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
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .flow_v.to("m³/h")
                            .m,
                            5,
                        )
                        for p in getattr(back_to_back, f"points_flange_sp_{sec}")
                    ]
                    results[f"W{_t} (kW)"] = [
                        round(p.power_shaft.to("kW").m, 5)
                        for p in getattr(back_to_back, f"points_rotor_t_{sec}")
                    ]
                    if bearing_mechanical_losses:
                        results[f"W{_t}/W{_sp}"] = [
                            round(
                                p.power_shaft.to("kW").m
                                / Q_(
                                    float(
                                        st.session_state[
                                            f"power_shaft_{section}_point_guarantee"
                                        ]
                                    ),
                                    parameters_map["power_shaft"][section][
                                        "data_sheet_units"
                                    ],
                                )
                                .to("kW")
                                .m,
                                5,
                            )
                            for p in getattr(back_to_back, f"points_rotor_t_{sec}")
                        ]
                    else:
                        results[f"W{_t}/W{_sp}"] = [
                            round(
                                p.power.to("kW").m
                                / Q_(
                                    float(
                                        st.session_state[
                                            f"power_{section}_point_guarantee"
                                        ]
                                    ),
                                    parameters_map["power"][section][
                                        "data_sheet_units"
                                    ],
                                )
                                .to("kW")
                                .m,
                                5,
                            )
                            for p in getattr(back_to_back, f"points_rotor_t_{sec}")
                        ]
                    results[f"W{conv} (kW)"] = [
                        round(p.power_shaft.to("kW").m, 5)
                        for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
                    ]
                    if bearing_mechanical_losses:
                        results[f"W{conv}/W{_sp}"] = [
                            round(
                                p.power_shaft.to("kW").m
                                / Q_(
                                    float(
                                        st.session_state[
                                            f"power_shaft_{section}_point_guarantee"
                                        ]
                                    ),
                                    parameters_map["power_shaft"][section][
                                        "data_sheet_units"
                                    ],
                                )
                                .to("kW")
                                .m,
                                5,
                            )
                            for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
                        ]
                    else:
                        results[f"W{conv}/W{_sp}"] = [
                            round(
                                p.power.to("kW").m
                                / Q_(
                                    float(
                                        st.session_state[
                                            f"power_{section}_point_guarantee"
                                        ]
                                    ),
                                    parameters_map["power"][section][
                                        "data_sheet_units"
                                    ],
                                )
                                .to("kW")
                                .m,
                                5,
                            )
                            for p in getattr(back_to_back, f"points_rotor_sp_{sec}")
                        ]
                    results[f"Eff{_t}"] = [
                        round(p.eff.m, 5)
                        for p in getattr(back_to_back, f"points_flange_t_{sec}")
                    ]
                    results[f"Eff{conv}"] = [
                        round(p.eff.m, 5)
                        for p in getattr(back_to_back, f"points_flange_sp_{sec}")
                    ]

                    results[f"φ{_t}"].append(round(point_interpolated.phi.m, 5))
                    results[f"φ{_t} / φ{_sp}"].append(
                        round(
                            point_interpolated.phi.m
                            / getattr(back_to_back, f"guarantee_point_{sec}").phi.m,
                            5,
                        )
                    )
                    results["vi / vd"].append(
                        round(point_interpolated.volume_ratio.m, 5)
                    )
                    results[f"(vi/vd){_t}/(vi/vd){_sp}"].append(
                        round(
                            point_interpolated.volume_ratio.m
                            / getattr(
                                back_to_back, f"guarantee_point_{sec}"
                            ).volume_ratio.m,
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
                            / getattr(
                                back_to_back, f"guarantee_point_{sec}"
                            ).reynolds.m,
                            5,
                        )
                    )
                    results[f"pd{conv} (bar)"].append(
                        round(point_interpolated.disch.p("bar").m, 5)
                    )
                    results[f"pd{conv}/pd{_sp}"].append(
                        round(
                            point_interpolated.disch.p("bar").m
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .disch.p("bar")
                            .m,
                            5,
                        )
                    )
                    results[f"Head{_t} (kJ/kg)"].append(
                        round(point_interpolated.head.to("kJ/kg").m, 5)
                    )
                    results[f"Head{_t}/Head{_sp}"].append(
                        round(
                            point_interpolated.head.to("kJ/kg").m
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .head.to("kJ/kg")
                            .m,
                            5,
                        )
                    )
                    results[f"Head{conv} (kJ/kg)"].append(
                        round(point_interpolated.head.to("kJ/kg").m, 5)
                    )
                    results[f"Head{conv}/Head{_sp}"].append(
                        round(
                            point_interpolated.head.to("kJ/kg").m
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .head.to("kJ/kg")
                            .m,
                            5,
                        )
                    )
                    results[f"Q{conv} (m3/h)"].append(
                        round(point_interpolated.flow_v.to("m³/h").m, 5)
                    )
                    results[f"Q{conv}/Q{_sp}"].append(
                        round(
                            point_interpolated.flow_v.to("m³/h").m
                            / getattr(back_to_back, f"guarantee_point_{sec}")
                            .flow_v.to("m³/h")
                            .m,
                            5,
                        )
                    )
                    results[f"W{_t} (kW)"].append(None)
                    results[f"W{_t}/W{_sp}"].append(None)
                    if bearing_mechanical_losses:
                        results[f"W{conv} (kW)"].append(
                            round(point_interpolated.power_shaft.to("kW").m, 5)
                        )
                        results[f"W{conv}/W{_sp}"].append(
                            round(
                                point_interpolated.power_shaft.to("kW").m
                                / Q_(
                                    float(
                                        st.session_state[
                                            f"power_shaft_{section}_point_guarantee"
                                        ]
                                    ),
                                    parameters_map["power_shaft"][section][
                                        "data_sheet_units"
                                    ],
                                )
                                .to("kW")
                                .m,
                                5,
                            )
                        )
                    else:
                        results[f"W{conv} (kW)"].append(
                            round(point_interpolated.power.to("kW").m, 5)
                        )
                        results[f"W{conv}/W{_sp}"].append(
                            round(
                                point_interpolated.power.to("kW").m
                                / Q_(
                                    float(
                                        st.session_state[
                                            f"power_{section}_point_guarantee"
                                        ]
                                    ),
                                    parameters_map["power"][section][
                                        "data_sheet_units"
                                    ],
                                )
                                .to("kW")
                                .m,
                                5,
                            )
                        )
                    results[f"Eff{_t}"].append(round(point_interpolated.eff.m, 5))
                    results[f"Eff{conv}"].append(round(point_interpolated.eff.m, 5))

                    # add overall results to both dataframes
                    for key in results.keys():
                        if key == f"pd{conv} (bar)":
                            results[f"pd{conv} (bar)"].append(
                                round(
                                    point_interpolated_sec2.disch.p("bar").m,
                                    5,
                                )
                            )
                        elif key == f"pd{conv}/pd{_sp}":
                            results[key].append(
                                round(
                                    point_interpolated_sec2.disch.p("bar").m
                                    / getattr(back_to_back, "guarantee_point_sec2")
                                    .disch.p("bar")
                                    .m,
                                    5,
                                )
                            )
                        elif key == f"W{conv} (kW)":
                            if bearing_mechanical_losses:
                                results[key].append(
                                    round(
                                        point_interpolated_sec1.power.to("kW").m
                                        + point_interpolated_sec2.power.to("kW").m
                                        + max(
                                            point_interpolated_sec1.power_losses.to(
                                                "kW"
                                            ).m,
                                            point_interpolated_sec2.power_losses.to(
                                                "kW"
                                            ).m,
                                        ),
                                        5,
                                    )
                                )
                            else:
                                results[key].append(
                                    round(
                                        point_interpolated_sec1.power.to("kW").m
                                        + point_interpolated_sec2.power.to("kW").m,
                                        5,
                                    )
                                )
                        elif key == f"W{conv}/W{_sp}":
                            if bearing_mechanical_losses:
                                results[key].append(
                                    round(
                                        (
                                            point_interpolated_sec1.power.to("kW").m
                                            + point_interpolated_sec2.power.to("kW").m
                                            + max(
                                                point_interpolated_sec1.power_losses.to(
                                                    "kW"
                                                ).m,
                                                point_interpolated_sec2.power_losses.to(
                                                    "kW"
                                                ).m,
                                            )
                                        )
                                        / (
                                            Q_(
                                                float(
                                                    st.session_state[
                                                        "power_shaft_section_1_point_guarantee"
                                                    ]
                                                ),
                                                parameters_map["power_shaft"][section][
                                                    "data_sheet_units"
                                                ],
                                            )
                                            .to("kW")
                                            .m
                                            + Q_(
                                                float(
                                                    st.session_state[
                                                        "power_shaft_section_2_point_guarantee"
                                                    ]
                                                ),
                                                parameters_map["power_shaft"][section][
                                                    "data_sheet_units"
                                                ],
                                            )
                                            .to("kW")
                                            .m
                                        ),
                                        5,
                                    )
                                )
                            else:
                                results[key].append(
                                    round(
                                        (
                                            point_interpolated_sec1.power.to("kW").m
                                            + point_interpolated_sec2.power.to("kW").m
                                        )
                                        / (
                                            Q_(
                                                float(
                                                    st.session_state[
                                                        "power_section_1_point_guarantee"
                                                    ]
                                                ),
                                                parameters_map["power"][section][
                                                    "data_sheet_units"
                                                ],
                                            )
                                            .to("kW")
                                            .m
                                            + Q_(
                                                float(
                                                    st.session_state[
                                                        "power_section_2_point_guarantee"
                                                    ]
                                                ),
                                                parameters_map["power"][section][
                                                    "data_sheet_units"
                                                ],
                                            )
                                            .to("kW")
                                            .m
                                        ),
                                        5,
                                    )
                                )
                        else:
                            results[key].append(None)

                    df_results = pd.DataFrame(results)
                    rename_index = {
                        i: f"Point {i + 1}"
                        for i in range(
                            len(getattr(back_to_back, f"points_flange_t_{sec}"))
                        )
                    }
                    rename_index[
                        len(getattr(back_to_back, f"points_flange_t_{sec}"))
                    ] = "Guarantee Point"
                    rename_index[
                        len(getattr(back_to_back, f"points_flange_t_{sec}")) + 1
                    ] = "Overall"

                    df_results.rename(
                        index=rename_index,
                        inplace=True,
                    )

                    if section == "section_1":
                        tab_results = tab_results_section_1
                    else:
                        tab_results = tab_results_section_2

                    with tab_results:

                        styled_df_results = df_results.style

                        mach_limits = point_interpolated.mach_limits()
                        styled_df_results = highlight_cell(
                            styled_df_results,
                            df_results,
                            "Guarantee Point",
                            f"Mach{_t}",
                            mach_limits["lower"],
                            mach_limits["upper"],
                        )
                        reynolds_limits = point_interpolated.reynolds_limits()
                        styled_df_results = highlight_cell(
                            styled_df_results,
                            df_results,
                            "Guarantee Point",
                            f"Re{_t}",
                            reynolds_limits["lower"],
                            reynolds_limits["upper"],
                        )
                        styled_df_results = highlight_cell(
                            styled_df_results,
                            df_results,
                            "Guarantee Point",
                            f"(vi/vd){_t}/(vi/vd){_sp}",
                            0.95,
                            1.05,
                        )
                        styled_df_results = highlight_cell(
                            styled_df_results,
                            df_results,
                            "Guarantee Point",
                            f"φ{_t} / φ{_sp}",
                            0.96,
                            1.04,
                        )

                        if variable_speed:
                            power_limit = 1.04
                            pressure_limit = 1e15
                        else:
                            power_limit = 1.07
                            pressure_limit = 1.05

                        for _point in ["Guarantee Point", "Overall"]:
                            # highlight pdconv/pdsp
                            styled_df_results = highlight_cell(
                                styled_df_results,
                                df_results,
                                _point,
                                f"pd{conv}/pd{_sp}",
                                1.0,
                                pressure_limit,
                            )
                            # highlight Wconv/Wsp
                            styled_df_results = highlight_cell(
                                styled_df_results,
                                df_results,
                                _point,
                                f"W{conv}/W{_sp}",
                                0.0,
                                power_limit,
                            )

                        st.dataframe(
                            styled_df_results.format(
                                "{:.2%}",
                                subset=[
                                    f"φ{_t} / φ{_sp}",
                                    f"pd{conv}/pd{_sp}",
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

                        table_excel = to_excel(styled_df_results)
                        st.download_button(
                            "Download Results Table",
                            data=table_excel,
                            file_name=f"{sec}.xlsx",
                            mime="application/vnd.ms-excel",
                            width="stretch",
                        )

                        with st.container():
                            mach_col, reynolds_col = st.columns(2)
                            mach_col.plotly_chart(
                                point_interpolated.plot_mach(), width="stretch"
                            )
                            reynolds_col.plotly_chart(
                                point_interpolated.plot_reynolds(),
                                width="stretch",
                            )


                        plots_dict = {}
                        for curve in ["head", "eff", "discharge_pressure", "power"]:
                            flow_v_units = (
                                plot_limits.get(curve, {})
                                .get(sec, {})
                                .get("x", {})
                                .get("units")
                            )
                            curve_units = (
                                plot_limits.get(curve, {})
                                .get(sec, {})
                                .get("y", {})
                                .get("units")
                            )

                            kwargs = {}
                            if flow_v_units is not None and flow_v_units != "":
                                kwargs["flow_v_units"] = flow_v_units
                            if curve_units is not None and curve_units != "":
                                if curve == "discharge_pressure":
                                    kwargs["p_units"] = curve_units
                                else:
                                    kwargs[f"{curve}_units"] = curve_units

                            if curve == "discharge_pressure":
                                curve_plot_method = "disch.p"
                            else:
                                curve_plot_method = curve

                            plots_dict[curve] = r_getattr(
                                getattr(back_to_back, f"imp_flange_sp_{sec}"),
                                f"{curve_plot_method}_plot",
                            )(
                                show_points=show_points,
                                **kwargs,
                            )
                            plots_dict[curve] = r_getattr(
                                point_interpolated, f"{curve_plot_method}_plot"
                            )(
                                fig=plots_dict[curve],
                                show_points=show_points,
                                **kwargs,
                            )

                            plots_dict[curve].data[0].update(
                                name=f"Converted Curve {back_to_back.speed_operational.to('rpm').m:.0f} RPM",
                            )
                            if curve == "discharge_pressure":
                                plots_dict[curve].data[1].update(
                                    name=f"Flow: {point_interpolated.flow_v.to(flow_v_units):.~2f}, {curve.capitalize()}: {r_getattr(point_interpolated, curve_plot_method)(curve_units):.~2f}".replace(
                                        "m ** 3 / h", "m³/h"
                                    ).replace("Discharge_pressure", "Disch. p")
                                )
                            else:
                                plots_dict[curve].data[1].update(
                                    name=f"Flow: {point_interpolated.flow_v.to(flow_v_units):.~2f}, {curve.capitalize()}: {r_getattr(point_interpolated, curve_plot_method).to(curve_units):.~2f}".replace(
                                        "m ** 3 / h", "m³/h"
                                    ).replace("Discharge_pressure", "Disch. p")
                                )

                            plots_dict[curve].update_layout(
                                showlegend=True,
                                # position legend at the bottom left
                                legend=dict(
                                    yanchor="bottom",
                                    y=0.01,
                                    xanchor="left",
                                    x=0.01,
                                ),
                            )

                            x_lower = (
                                plot_limits.get(curve, {})
                                .get(sec, {})
                                .get("x", {})
                                .get("lower_limit")
                            )
                            x_upper = (
                                plot_limits.get(curve, {})
                                .get(sec, {})
                                .get("x", {})
                                .get("upper_limit")
                            )
                            y_lower = (
                                plot_limits.get(curve, {})
                                .get(sec, {})
                                .get("y", {})
                                .get("lower_limit")
                            )
                            y_upper = (
                                plot_limits.get(curve, {})
                                .get(sec, {})
                                .get("y", {})
                                .get("upper_limit")
                            )

                            if (
                                x_lower is not None
                                and x_lower != ""
                                and x_upper is not None
                                and x_upper != ""
                                and y_lower is not None
                                and y_lower != ""
                                and y_upper is not None
                                and y_upper != ""
                            ):
                                plots_dict[curve].update_layout(
                                    xaxis_range=(
                                        plot_limits[curve][sec]["x"]["lower_limit"],
                                        plot_limits[curve][sec]["x"]["upper_limit"],
                                    ),
                                    yaxis_range=(
                                        plot_limits[curve][sec]["y"]["lower_limit"],
                                        plot_limits[curve][sec]["y"]["upper_limit"],
                                    ),
                                )

                            if (
                                st.session_state.get(f"fig_{curve}_{sec}") is not None
                                and st.session_state.get(f"fig_{curve}_{sec}") != ""
                            ):
                                plots_dict[curve] = add_background_image(
                                    limits=plot_limits[curve][sec],
                                    fig=plots_dict[curve],
                                    image=st.session_state[f"fig_{curve}_{sec}"],
                                )

                        with st.container():
                            head_col, eff_col = st.columns(2)
                            head_col.plotly_chart(plots_dict["head"], width="stretch")
                            eff_col.plotly_chart(plots_dict["eff"], width="stretch")

                        with st.container():
                            disch_p_col, power_col = st.columns(2)
                            disch_p_col.plotly_chart(
                                plots_dict["discharge_pressure"],
                                width="stretch",
                            )
                            power_col.plotly_chart(plots_dict["power"], width="stretch")

    # this part will only show if we start streamlit with --client.toolbarMode developer
    if st.config.get_option("client.toolbarMode") == "developer":
        with st.expander("Session State"):
            session_state_copy = {}
            for key, value in st.session_state.items():
                session_state_copy[key] = value

            # remove session state keys that start with fig_
            for key in list(session_state_copy.keys()):
                if key.startswith("fig_"):
                    del session_state_copy[key]

            # sort
            session_state_copy = dict(sorted(session_state_copy.items()))

            st.write(session_state_copy)


if __name__ == "__main__":
    run_app(main, "back_to_back")
