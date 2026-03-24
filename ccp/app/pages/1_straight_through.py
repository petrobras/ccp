import ccp
import streamlit as st
import json
import pandas as pd
import io
import base64
import zipfile
import toml
import time
import logging
from ccp.compressor import Point1Sec, StraightThrough
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
    ## Performance Test Straight-Through Compressor
    """
    )

    def get_session():
        # if file is being loaded, session_name is set with the file name
        if "session_name" not in st.session_state:
            st.session_state.session_name = ""
        if "straight_through" not in st.session_state:
            st.session_state.straight_through = ""
        if "expander_state" not in st.session_state:
            st.session_state.expander_state = False
        if "ccp_version" not in st.session_state:
            st.session_state.ccp_version = ccp.__version__
        if "app_type" not in st.session_state:
            st.session_state.app_type = "straight_through"
        for curve in ["head", "power", "eff", "discharge_pressure"]:
            if f"fig_{curve}" not in st.session_state:
                st.session_state[f"fig_{curve}"] = ""
        if "bearing_mechanical_losses" not in st.session_state:
            st.session_state.bearing_mechanical_losses = False
        if "oil_specific_heat" not in st.session_state:
            st.session_state.oil_specific_heat = False
        if "oil_iso" not in st.session_state:
            st.session_state.oil_iso = False

    get_session()

    def _load_straight_through(my_zip, version):
        for name in my_zip.namelist():
            if name.endswith(".json"):
                session_state_data = convert(
                    json.loads(my_zip.read(name)), version
                )
                if "flow_point_guarantee" not in session_state_data:
                    raise ValueError("File is not a ccp straight-through file.")
        for name in my_zip.namelist():
            if name.endswith(".png"):
                session_state_data[name.split(".")[0]] = my_zip.read(name)
            elif name.endswith(".toml"):
                straight_through_file = convert(
                    io.StringIO(my_zip.read(name).decode("utf-8")), version
                )
                session_state_data[name.split(".")[0]] = StraightThrough.load(
                    straight_through_file
                )
        return session_state_data

    def _save_straight_through(my_zip, session_state_dict_copy):
        for key, value in dict(session_state_dict_copy).items():
            if isinstance(
                value, (bytes, st.runtime.uploaded_file_manager.UploadedFile)
            ):
                if key.startswith("fig"):
                    my_zip.writestr(f"{key}.png", value)
                del session_state_dict_copy[key]
            if isinstance(value, StraightThrough):
                my_zip.writestr(
                    f"{key}.toml", toml.dumps(value._dict_to_save())
                )
                del session_state_dict_copy[key]
        return session_state_dict_copy

    file_sidebar(_load_straight_through, _save_straight_through)

    # Gas selection
    fluid_list, default_components = get_fluid_list()
    gas_compositions_table = gas_selection_form(fluid_list, default_components)

    # add container with 4 columns and 2 rows
    with st.sidebar.expander("⚙️ Options"):
        reynolds_correction = st.checkbox("Reynolds Correction", value=True)
        casing_heat_loss = st.checkbox("Casing Heat Loss", value=True)
        bearing_mechanical_losses = st.checkbox("Bearing Mechanical Losses", value=True)
        calculate_leakages = st.checkbox("Calculate Leakages", value=True)
        seal_gas_flow = st.checkbox("Seal Gas Flow", value=True)

        # add a disabled flag in the parameters_map dict based on the checkbox
        if seal_gas_flow:
            parameters_map["seal_gas_flow_m"]["disabled"] = False
            parameters_map["seal_gas_temperature"]["disabled"] = False
        else:
            parameters_map["seal_gas_flow_m"]["disabled"] = True
            parameters_map["seal_gas_temperature"]["disabled"] = True
            parameters_map["seal_gas_flow_m"]["value"] = ""
            parameters_map["seal_gas_temperature"]["value"] = ""

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

    # add dict to store the values for guarantee and test points
    # in the parameters_map
    number_of_test_points = 6
    points_list = ["point_guarantee"] + [
        f"point_{i}" for i in range(1, number_of_test_points + 1)
    ]
    points_fo_list = [f"point_fo_{i}" for i in range(1, number_of_test_points + 1)]

    for parameter in parameters_map:
        if not parameter.endswith("_fo"):
            parameters_map[parameter]["points"] = {
                "data_sheet_units": None,
                "test_units": None,
            }
            for point in points_list:
                parameters_map[parameter]["points"][point] = {
                    "value": None,
                }
        else:
            parameters_map[parameter]["points_fo"] = {
                "test_fo_units": None,
            }
            for point in points_fo_list:
                parameters_map[parameter]["points_fo"][point] = {
                    "value": None,
                }

    with st.expander("Data Sheet", expanded=st.session_state.expander_state):
        # build container with 8 columns
        points_title = st.container()
        points_title_columns = points_title.columns(3, gap="small")
        points_title_columns[0].markdown("")
        points_title_columns[1].markdown("Units")
        points_title_columns[2].markdown("")

        points_gas_columns = points_title.columns(3, gap="small")
        points_gas_columns[0].markdown("Gas Selection")
        points_gas_columns[1].markdown("")
        gas_options = [
            st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_compositions_table)
        ]

        gas_name_point_guarantee = points_gas_columns[2].selectbox(
            "gas_point_guarantee",
            options=gas_options,
            label_visibility="collapsed",
            key="gas_point_guarantee",
            index=get_index_selected_gas(gas_options,"gas_point_guarantee"),
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
                values_col,
            ) = parameter_container.columns(3, gap="small")

            parameters_col.markdown(
                f"{parameters_map[parameter]['label']}",
                help=f"{parameters_map[parameter].get('help', '')}",
            )

            parameters_map[parameter]["points"]["data_sheet_units"] = (
                units_col.selectbox(
                    f"{parameter} units",
                    options=parameters_map[parameter]["units"],
                    key=f"{parameter}_units_point_guarantee",
                    label_visibility="collapsed",
                )
            )
            parameters_map[parameter]["points"]["point_guarantee"]["value"] = (
                values_col.text_input(
                    f"{parameter} value.",
                    key=f"{parameter}_point_guarantee",
                    label_visibility="collapsed",
                )
            )

    with st.expander("Curves", expanded=st.session_state.expander_state):
        # add upload button for curve
        # check if fig_dict was created when loading state. Otherwise, create it
        plot_limits = {}
        fig_dict_uploaded = {}

        for curve in ["head", "eff", "discharge_pressure", "power"]:
            st.markdown(f"### {parameters_map[curve]['label']}")
            parameter_container = st.container()
            curves_col = parameter_container

            plot_limits[curve] = {}
            # create upload button
            fig_dict_uploaded[f"uploaded_fig_{curve}"] = curves_col.file_uploader(
                f"Upload {curve}.",
                type=["png"],
                key=f"uploaded_fig_{curve}",
                label_visibility="collapsed",
            )

            if fig_dict_uploaded[f"uploaded_fig_{curve}"] is not None:
                st.session_state[f"fig_{curve}"] = fig_dict_uploaded[
                    f"uploaded_fig_{curve}"
                ].read()

            # add container to x range
            for axis in ["x", "y"]:
                with st.container():
                    (
                        plot_limit,
                        units_col,
                        lower_value_col,
                        upper_value_col,
                    ) = curves_col.columns(4, gap="small")
                    plot_limit.markdown(f"{axis} range")
                    plot_limits[curve][f"{axis}"] = {}
                    plot_limits[curve][f"{axis}"]["lower_limit"] = (
                        lower_value_col.text_input(
                            "Lower limit",
                            key=f"{axis}_{curve}_lower",
                            label_visibility="collapsed",
                        )
                    )
                    plot_limits[curve][f"{axis}"]["upper_limit"] = (
                        upper_value_col.text_input(
                            "Upper limit",
                            key=f"{axis}_{curve}_upper",
                            label_visibility="collapsed",
                        )
                    )
                    if axis == "x":
                        plot_limits[curve][f"{axis}"]["units"] = units_col.selectbox(
                            f"{parameter} units",
                            options=parameters_map["flow_v"]["units"],
                            key=f"{axis}_{curve}_flow_units",
                            label_visibility="collapsed",
                        )
                    else:
                        plot_limits[curve][f"{axis}"]["units"] = units_col.selectbox(
                            f"{parameter} units",
                            options=parameters_map[curve]["units"],
                            key=f"{axis}_{curve}_units",
                            label_visibility="collapsed",
                        )

    number_of_test_points = 6
    number_of_columns = number_of_test_points + 2

    with st.expander("Test Data", expanded=st.session_state.expander_state):
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
                    st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_compositions_table)
                ]
                col.selectbox(
                    f"gas_point_{i - 1}",
                    options=gas_options,
                    label_visibility="collapsed",
                    key=f"gas_point_{i - 1}",
                    index=get_index_selected_gas(gas_options,f"gas_point_{i - 1}"),
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
                    parameters_map[parameter]["points"]["test_units"] = col.selectbox(
                        f"{parameter} units",
                        options=parameters_map[parameter]["units"],
                        key=f"{parameter}_units",
                        label_visibility="collapsed",
                        disabled=parameters_map[parameter].get("disabled", False),
                    )
                else:
                    parameters_map[parameter]["points"][f"point_{i - 1}"]["value"] = (
                        col.text_input(
                            f"{parameter} value.",
                            key=f"{parameter}_point_{i - 1}",
                            label_visibility="collapsed",
                            disabled=parameters_map[parameter].get("disabled", False),
                        )
                    )

    with st.expander("Flowrate Calculation", expanded=st.session_state.expander_state):
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
                    st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_compositions_table)
                ]
                col.selectbox(
                    f"gas_fo_{i - 1}",
                    options=gas_options,
                    label_visibility="collapsed",
                    key=f"gas_fo_{i - 1}",
                    index=get_index_selected_gas(gas_options,f"gas_fo_{i - 1}"),
                )

        # build one container with 8 columns for each parameter
        for parameter in [
            "outer_diameter_fo",
            "inner_diameter_fo",
            "upstream_pressure_fo",
            "upstream_temperature_fo",
            "pressure_drop_fo",
            "tappings_fo",
            "mass_flow_fo",
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
                    if parameter == "tappings_fo":
                        pass
                    else:
                        parameters_map[parameter]["points_fo"]["test_fo_units"] = (
                            col.selectbox(
                                f"{parameter} units",
                                options=parameters_map[parameter]["units"],
                                key=f"{parameter}_units",
                                label_visibility="collapsed",
                            )
                        )
                else:
                    if parameter == "tappings_fo":
                        parameters_map[parameter]["points_fo"]["test_fo_units"] = (
                            col.selectbox(
                                f"{parameter} value",
                                options=parameters_map[parameter]["units"],
                                key=f"{parameter}_{i - 1}",
                                label_visibility="collapsed",
                            )
                        )
                    else:
                        # elif parameter != "mass_flow_fo":
                        parameters_map[parameter]["points_fo"][f"point_fo_{i - 1}"][
                            "value"
                        ] = col.text_input(
                            f"{parameter} value.",
                            key=f"{parameter}_{i - 1}",
                            label_visibility="collapsed",
                        )

    # add calculate button
    straight_through = None

    def fo_calc():
        global missed_points
        kwargs = {}
        missed_points = []

        for i, col in enumerate(parameter_columns):
            if i > 1:
                if (
                    st.session_state[f"outer_diameter_fo_{i - 1}"] == ""
                    or st.session_state[f"inner_diameter_fo_{i - 1}"] == ""
                    or st.session_state[f"upstream_pressure_fo_{i - 1}"] == ""
                    or st.session_state[f"upstream_temperature_fo_{i - 1}"] == ""
                    or st.session_state[f"pressure_drop_fo_{i - 1}"] == ""
                ):
                    missed_points.append(i - 1)
                    parameters_map["mass_flow_fo"]["points_fo"][f"point_fo_{i - 1}"][
                        "value"
                    ] = ""
                    st.session_state[f"mass_flow_fo_{i - 1}"] = ""
                    continue
                else:
                    kwargs["state"] = ccp.State(
                        p=Q_(
                            float(st.session_state[f"upstream_pressure_fo_{i - 1}"]),
                            parameters_map["upstream_pressure_fo"]["points_fo"][
                                "test_fo_units"
                            ],
                        ),
                        T=Q_(
                            float(st.session_state[f"upstream_temperature_fo_{i - 1}"]),
                            parameters_map["upstream_temperature_fo"]["points_fo"][
                                "test_fo_units"
                            ],
                        ),
                        fluid=get_gas_composition(
                            st.session_state[f"gas_fo_{i - 1}"],
                            gas_compositions_table,
                            default_components,
                        ),
                    )

                    kwargs["delta_p"] = Q_(
                        float(st.session_state[f"pressure_drop_fo_{i - 1}"]),
                        parameters_map["pressure_drop_fo"]["points_fo"][
                            "test_fo_units"
                        ],
                    )

                    kwargs["D"] = Q_(
                        float(st.session_state[f"outer_diameter_fo_{i - 1}"]),
                        parameters_map["outer_diameter_fo"]["points_fo"][
                            "test_fo_units"
                        ],
                    )

                    kwargs["d"] = Q_(
                        float(st.session_state[f"inner_diameter_fo_{i - 1}"]),
                        parameters_map["inner_diameter_fo"]["points_fo"][
                            "test_fo_units"
                        ],
                    )

                    kwargs["tappings"] = st.session_state[f"tappings_fo_{i - 1}"]

                    fo_temp = ccp.FlowOrifice(**kwargs)
                    parameters_map["mass_flow_fo"]["points_fo"][f"point_fo_{i - 1}"][
                        "value"
                    ] = fo_temp.qm.to(
                        parameters_map["mass_flow_fo"]["points_fo"]["test_fo_units"]
                    ).m
                    st.session_state[f"mass_flow_fo_{i - 1}"] = str(
                        round(
                            parameters_map["mass_flow_fo"]["points_fo"][
                                f"point_fo_{i - 1}"
                            ]["value"],
                            5,
                        )
                    )
                st.session_state.missed_points = missed_points

    with st.container():
        calculate_col, calculate_speed_col, calculate_flowrate_col = st.columns(
            [1, 1, 1]
        )
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
            help="Calculate speed to match the discharge pressure.",
        )
        calculate_flowrate = calculate_flowrate_col.button(
            "Calculate Flowrate",
            type="primary",
            width="stretch",
            on_click=fo_calc,
            help="Calculate flowrate with orifice plate data.",
        )

    if calculate_flowrate:
        calculate_flowrate = False
        progress_value = 0
        progress_bar = st.progress(progress_value, text="Calculating...")

        if "missed_points" not in st.session_state:
            st.session_state["missed_points"] = []

        for i in range(len(st.session_state["missed_points"])):
            st.warning(
                f"Missing data for point {st.session_state['missed_points'][i]}!"
            )
        time.sleep(0.1)
        progress_bar.progress(100, text="Done!")

    # create test points
    test_points = []
    kwargs = {}

    if calculate_button or calculate_speed_button:
        progress_value = 0
        progress_bar = st.progress(progress_value, text="Calculating...")
        # calculate guarantee point
        kwargs_guarantee = {}

        # get gas composition from selected gas
        gas_composition_data_sheet = {}
        gas_composition_data_sheet["point_guarantee"] = get_gas_composition(
            gas_name_point_guarantee,
            gas_compositions_table,
            default_components,
        )

        # to get data sheet units we use parameters_map[parameter]["selected_units"]
        if (
            Q_(0, parameters_map["flow"]["points"]["data_sheet_units"]).dimensionality
            == "[mass] / [time]"
        ):
            kwargs_guarantee["flow_m"] = Q_(
                float(st.session_state["flow_point_guarantee"]),
                parameters_map["flow"]["points"]["data_sheet_units"],
            )
        else:
            kwargs_guarantee["flow_v"] = Q_(
                float(st.session_state["flow_point_guarantee"]),
                parameters_map["flow"]["points"]["data_sheet_units"],
            )
        kwargs_guarantee["suc"] = ccp.State(
            p=Q_(
                float(st.session_state["suction_pressure_point_guarantee"]),
                parameters_map["suction_pressure"]["points"]["data_sheet_units"],
            ),
            T=Q_(
                float(st.session_state["suction_temperature_point_guarantee"]),
                parameters_map["suction_temperature"]["points"]["data_sheet_units"],
            ),
            fluid=gas_composition_data_sheet["point_guarantee"],
        )
        kwargs_guarantee["disch"] = ccp.State(
            p=Q_(
                float(st.session_state["discharge_pressure_point_guarantee"]),
                parameters_map["discharge_pressure"]["points"]["data_sheet_units"],
            ),
            T=Q_(
                float(
                    st.session_state["discharge_temperature_point_guarantee"],
                ),
                parameters_map["discharge_temperature"]["points"]["data_sheet_units"],
            ),
            fluid=gas_composition_data_sheet["point_guarantee"],
        )
        kwargs_guarantee["speed"] = Q_(
            float(st.session_state["speed_point_guarantee"]),
            parameters_map["speed"]["points"]["data_sheet_units"],
        )
        kwargs_guarantee["b"] = Q_(
            float(st.session_state["b_point_guarantee"]),
            parameters_map["b"]["points"]["data_sheet_units"],
        )
        kwargs_guarantee["D"] = Q_(
            float(st.session_state["D_point_guarantee"]),
            parameters_map["D"]["points"]["data_sheet_units"],
        )

        power_guarantee = Q_(
            float(st.session_state["power_point_guarantee"]),
            parameters_map["power"]["points"]["data_sheet_units"],
        )
        if bearing_mechanical_losses:
            if st.session_state["power_shaft_point_guarantee"] == "":
                power_shaft_guarantee = Q_(
                    float(st.session_state["power_point_guarantee"]),
                    parameters_map["power"]["points"]["data_sheet_units"],
                ).to("kW")
            else:
                power_shaft_guarantee = Q_(
                    float(st.session_state["power_shaft_point_guarantee"]),
                    parameters_map["power_shaft"]["points"]["data_sheet_units"],
                ).to("kW")
            kwargs_guarantee["power_losses"] = power_shaft_guarantee - power_guarantee
        else:
            kwargs_guarantee["power_losses"] = Q_(0, "W")

        time.sleep(0.1)
        progress_value += 5
        progress_bar.progress(progress_value, text="Calculating guarantee point...")
        guarantee_point = ccp.Point(
            **kwargs_guarantee,
        )

        for i in range(1, number_of_test_points + 1):
            kwargs = {}
            # check if at least flow, suction pressure and suction temperature are filled
            if (
                st.session_state[f"flow_point_{i}"] == ""
                or st.session_state[f"suction_pressure_point_{i}"] == ""
                or st.session_state[f"suction_temperature_point_{i}"] == ""
            ):
                if i < 6:
                    st.warning(f"Please fill the data for point {i}")
                continue
            else:
                calculate_button = False
                if (
                    Q_(0, parameters_map["flow"]["points"]["test_units"]).dimensionality
                    == "[mass] / [time]"
                ):
                    if st.session_state[f"flow_point_{i}"]:
                        kwargs["flow_m"] = Q_(
                            float(st.session_state[f"flow_point_{i}"]),
                            parameters_map["flow"]["points"]["test_units"],
                        )
                    else:
                        kwargs["flow_m"] = None
                else:
                    if st.session_state[f"flow_point_{i}"]:
                        kwargs["flow_v"] = Q_(
                            float(st.session_state[f"flow_point_{i}"]),
                            parameters_map["flow"]["points"]["test_units"],
                        )
                    else:
                        kwargs["flow_v"] = None
                kwargs["suc"] = ccp.State(
                    p=Q_(
                        float(st.session_state[f"suction_pressure_point_{i}"]),
                        parameters_map["suction_pressure"]["points"]["test_units"],
                    ),
                    T=Q_(
                        float(st.session_state[f"suction_temperature_point_{i}"]),
                        parameters_map["suction_temperature"]["points"]["test_units"],
                    ),
                    fluid=get_gas_composition(
                        st.session_state[f"gas_point_{i}"],
                        gas_compositions_table,
                        default_components,
                    ),
                )
                kwargs["disch"] = ccp.State(
                    p=Q_(
                        float(st.session_state[f"discharge_pressure_point_{i}"]),
                        parameters_map["discharge_pressure"]["points"]["test_units"],
                    ),
                    T=Q_(
                        float(st.session_state[f"discharge_temperature_point_{i}"]),
                        parameters_map["discharge_temperature"]["points"]["test_units"],
                    ),
                    fluid=get_gas_composition(
                        st.session_state[f"gas_point_{i}"],
                        gas_compositions_table,
                        default_components,
                    ),
                )
                if st.session_state[f"casing_delta_T_point_{i}"] and casing_heat_loss:
                    kwargs["casing_temperature"] = Q_(
                        float(st.session_state[f"casing_delta_T_point_{i}"]),
                        parameters_map["casing_delta_T"]["points"]["test_units"],
                    )
                    kwargs["ambient_temperature"] = 0
                else:
                    kwargs["casing_temperature"] = 0
                    kwargs["ambient_temperature"] = 0

                if calculate_leakages:
                    if st.session_state[f"balance_line_flow_m_point_{i}"] != "":
                        kwargs["balance_line_flow_m"] = Q_(
                            float(st.session_state[f"balance_line_flow_m_point_{i}"]),
                            parameters_map["balance_line_flow_m"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["balance_line_flow_m"] = None
                    if (
                        seal_gas_flow
                        and st.session_state[f"seal_gas_flow_m_point_{i}"] != ""
                    ):
                        kwargs["seal_gas_flow_m"] = Q_(
                            float(st.session_state[f"seal_gas_flow_m_point_{i}"]),
                            parameters_map["seal_gas_flow_m"]["points"]["test_units"],
                        )
                    else:
                        kwargs["seal_gas_flow_m"] = Q_(
                            0, parameters_map["seal_gas_flow_m"]["points"]["test_units"]
                        )
                    if (
                        seal_gas_flow
                        and st.session_state[f"seal_gas_temperature_point_{i}"] != ""
                    ):
                        kwargs["seal_gas_temperature"] = Q_(
                            float(st.session_state[f"seal_gas_temperature_point_{i}"]),
                            parameters_map["seal_gas_temperature"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["seal_gas_temperature"] = Q_(
                            0,
                            parameters_map["seal_gas_temperature"]["points"][
                                "test_units"
                            ],
                        )
                else:
                    pass
                    # TODO implement calculation without leakages

                kwargs["bearing_mechanical_losses"] = bearing_mechanical_losses
                if bearing_mechanical_losses:
                    if st.session_state[f"oil_flow_journal_bearing_de_point_{i}"] != "":
                        kwargs["oil_flow_journal_bearing_de"] = Q_(
                            float(
                                st.session_state[
                                    f"oil_flow_journal_bearing_de_point_{i}"
                                ]
                            ),
                            parameters_map["oil_flow_journal_bearing_de"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["oil_flow_journal_bearing_nde"] = None
                    if (
                        st.session_state[f"oil_flow_journal_bearing_nde_point_{i}"]
                        != ""
                    ):
                        kwargs["oil_flow_journal_bearing_nde"] = Q_(
                            float(
                                st.session_state[
                                    f"oil_flow_journal_bearing_nde_point_{i}"
                                ]
                            ),
                            parameters_map["oil_flow_journal_bearing_nde"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["oil_flow_thrust_bearing_nde"] = None
                    if st.session_state[f"oil_flow_thrust_bearing_nde_point_{i}"] != "":
                        kwargs["oil_flow_thrust_bearing_nde"] = Q_(
                            float(
                                st.session_state[
                                    f"oil_flow_thrust_bearing_nde_point_{i}"
                                ]
                            ),
                            parameters_map["oil_flow_thrust_bearing_nde"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["oil_inlet_temperature"] = None
                    if st.session_state[f"oil_inlet_temperature_point_{i}"] != "":
                        kwargs["oil_inlet_temperature"] = Q_(
                            float(st.session_state[f"oil_inlet_temperature_point_{i}"]),
                            parameters_map["oil_inlet_temperature"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["oil_outlet_temperature_de"] = None
                    if st.session_state[f"oil_outlet_temperature_de_point_{i}"] != "":
                        kwargs["oil_outlet_temperature_de"] = Q_(
                            float(
                                st.session_state[f"oil_outlet_temperature_de_point_{i}"]
                            ),
                            parameters_map["oil_outlet_temperature_de"]["points"][
                                "test_units"
                            ],
                        )
                    else:
                        kwargs["oil_outlet_temperature_nde"] = None
                    if st.session_state[f"oil_outlet_temperature_nde_point_{i}"] != "":
                        kwargs["oil_outlet_temperature_nde"] = Q_(
                            float(
                                st.session_state[
                                    f"oil_outlet_temperature_nde_point_{i}"
                                ]
                            ),
                            parameters_map["oil_outlet_temperature_nde"]["points"][
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
                    float(st.session_state["b_point_guarantee"]),
                    parameters_map["b"]["points"]["data_sheet_units"],
                )
                kwargs["D"] = Q_(
                    float(st.session_state["D_point_guarantee"]),
                    parameters_map["D"]["points"]["data_sheet_units"],
                )
                kwargs["casing_area"] = Q_(
                    float(st.session_state["casing_area_point_guarantee"]),
                    parameters_map["casing_area"]["points"]["data_sheet_units"],
                )
                kwargs["surface_roughness"] = Q_(
                    float(st.session_state["surface_roughness_point_guarantee"]),
                    parameters_map["surface_roughness"]["points"]["data_sheet_units"],
                )
                time.sleep(0.1)
                progress_value += 2
                progress_bar.progress(progress_value, text="Calculating test points...")

                test_points.append(
                    Point1Sec(
                        speed=Q_(
                            float(st.session_state[f"speed_point_{i}"]),
                            parameters_map["speed"]["points"]["test_units"],
                        ),
                        **kwargs,
                    )
                )

        time.sleep(0.1)
        progress_value += 10
        progress_bar.progress(progress_value, text="Converting points...")
        straight_through = StraightThrough(
            guarantee_point=guarantee_point,
            test_points=test_points,
            reynolds_correction=reynolds_correction,
            bearing_mechanical_losses=bearing_mechanical_losses,
        )

        if calculate_speed_button:
            time.sleep(0.1)
            progress_value += 10
            progress_bar.progress(progress_value, text="Finding speed...")
            straight_through = (
                straight_through.calculate_speed_to_match_discharge_pressure()
            )

        time.sleep(0.1)
        progress_bar.progress(100, text="Done!")

        # add straight_through object to session state
        st.session_state["straight_through"] = straight_through

    # if straight_through is not defined, pickle the saved file
    if (
        st.session_state["straight_through"] is not None
        and st.session_state["straight_through"] != ""
    ):
        straight_through = st.session_state["straight_through"]

    if (
        st.session_state["straight_through"] is not None
        and st.session_state["straight_through"] != ""
    ):
        with st.expander("Results"):
            st.write(
                f"Final speed(s) used in calculation: {straight_through.speed_operational.to('rpm').m:.2f} RPM"
            )

            _t = "\u209c"
            _sp = "\u209b\u209a"
            conv = "\u1d9c" + "\u1d52" + "\u207f" + "\u1d5b"

            results = {}

            if straight_through:
                # create interpolated point with point method
                point_interpolated = getattr(straight_through, "point")(
                    flow_v=getattr(straight_through, "guarantee_point").flow_v,
                    speed=straight_through.speed_operational,
                )

                results[f"φ{_t}"] = [
                    round(p.phi.m, 5) for p in getattr(straight_through, "test_points")
                ]
                results[f"φ{_t} / φ{_sp}"] = [
                    round(
                        p.phi.m / getattr(straight_through, "guarantee_point").phi.m,
                        5,
                    )
                    for p in getattr(straight_through, "test_points")
                ]
                results["vi / vd"] = [
                    round(p.volume_ratio.m, 5)
                    for p in getattr(straight_through, "test_points")
                ]
                results[f"(vi/vd){_t}/(vi/vd){_sp}"] = [
                    round(
                        p.volume_ratio.m
                        / getattr(straight_through, "guarantee_point").volume_ratio.m,
                        5,
                    )
                    for p in getattr(straight_through, "test_points")
                ]
                results[f"Mach{_t}"] = [
                    round(p.mach.m, 5) for p in getattr(straight_through, "test_points")
                ]
                results[f"Mach{_t} - Mach{_sp}"] = [
                    round(
                        p.mach.m - getattr(straight_through, "guarantee_point").mach.m,
                        5,
                    )
                    for p in getattr(straight_through, "test_points")
                ]
                results[f"Re{_t}"] = [
                    round(p.reynolds.m, 5)
                    for p in getattr(straight_through, "test_points")
                ]
                results[f"Re{_t} / Re{_sp}"] = [
                    round(
                        p.reynolds.m
                        / getattr(straight_through, "guarantee_point").reynolds.m,
                        5,
                    )
                    for p in getattr(straight_through, "test_points")
                ]
                results[f"pd{conv} (bar)"] = [
                    round(p.disch.p("bar").m, 5)
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"pd{conv}/pd{_sp}"] = [
                    round(
                        p.disch.p("bar").m
                        / getattr(straight_through, "guarantee_point").disch.p("bar").m,
                        5,
                    )
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"Head{_t} (kJ/kg)"] = [
                    round(p.head.to("kJ/kg").m, 5)
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"Head{_t}/Head{_sp}"] = [
                    round(
                        p.head.to("kJ/kg").m
                        / getattr(straight_through, "guarantee_point")
                        .head.to("kJ/kg")
                        .m,
                        5,
                    )
                    for p in getattr(straight_through, "test_points")
                ]
                results[f"Head{conv} (kJ/kg)"] = [
                    round(p.head.to("kJ/kg").m, 5)
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"Head{conv}/Head{_sp}"] = [
                    round(
                        p.head.to("kJ/kg").m
                        / getattr(straight_through, "guarantee_point")
                        .head.to("kJ/kg")
                        .m,
                        5,
                    )
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"Q{conv} (m3/h)"] = [
                    round(p.flow_v.to("m³/h").m, 5)
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"Q{conv}/Q{_sp}"] = [
                    round(
                        p.flow_v.to("m³/h").m
                        / getattr(straight_through, "guarantee_point")
                        .flow_v.to("m³/h")
                        .m,
                        5,
                    )
                    for p in getattr(straight_through, "points_flange_sp")
                ]
                results[f"W{_t} (kW)"] = [
                    round(p.power_shaft.to("kW").m, 5)
                    for p in getattr(straight_through, "points_rotor_t")
                ]
                if bearing_mechanical_losses:
                    results[f"W{_t}/W{_sp}"] = [
                        round(
                            p.power_shaft.to("kW").m
                            / Q_(
                                float(st.session_state["power_shaft_point_guarantee"]),
                                parameters_map["power_shaft"]["points"][
                                    "data_sheet_units"
                                ],
                            )
                            .to("kW")
                            .m,
                            5,
                        )
                        for p in getattr(straight_through, "points_rotor_t")
                    ]
                else:
                    results[f"W{_t}/W{_sp}"] = [
                        round(
                            p.power_shaft.to("kW").m
                            / Q_(
                                float(st.session_state["power_point_guarantee"]),
                                parameters_map["power"]["points"]["data_sheet_units"],
                            )
                            .to("kW")
                            .m,
                            5,
                        )
                        for p in getattr(straight_through, "points_rotor_t")
                    ]
                results[f"W{conv} (kW)"] = [
                    round(p.power_shaft.to("kW").m, 5)
                    for p in getattr(straight_through, "points_rotor_sp")
                ]
                if bearing_mechanical_losses:
                    results[f"W{conv}/W{_sp}"] = [
                        round(
                            p.power_shaft.to("kW").m
                            / Q_(
                                float(st.session_state["power_shaft_point_guarantee"]),
                                parameters_map["power_shaft"]["points"][
                                    "data_sheet_units"
                                ],
                            )
                            .to("kW")
                            .m,
                            5,
                        )
                        for p in getattr(straight_through, "points_rotor_sp")
                    ]
                else:
                    results[f"W{conv}/W{_sp}"] = [
                        round(
                            p.power_shaft.to("kW").m
                            / Q_(
                                float(st.session_state["power_point_guarantee"]),
                                parameters_map["power"]["points"]["data_sheet_units"],
                            )
                            .to("kW")
                            .m,
                            5,
                        )
                        for p in getattr(straight_through, "points_rotor_sp")
                    ]
                results[f"Eff{_t}"] = [
                    round(p.eff.m, 5)
                    for p in getattr(straight_through, "points_flange_t")
                ]
                results[f"Eff{conv}"] = [
                    round(p.eff.m, 5)
                    for p in getattr(straight_through, "points_flange_sp")
                ]

                results[f"φ{_t}"].append(round(point_interpolated.phi.m, 5))
                results[f"φ{_t} / φ{_sp}"].append(
                    round(
                        point_interpolated.phi.m
                        / getattr(straight_through, "guarantee_point").phi.m,
                        5,
                    )
                )
                results["vi / vd"].append(round(point_interpolated.volume_ratio.m, 5))
                results[f"(vi/vd){_t}/(vi/vd){_sp}"].append(
                    round(
                        point_interpolated.volume_ratio.m
                        / getattr(straight_through, "guarantee_point").volume_ratio.m,
                        5,
                    )
                )
                results[f"Mach{_t}"].append(round(point_interpolated.mach.m, 5))
                results[f"Mach{_t} - Mach{_sp}"].append(
                    round(
                        point_interpolated.mach.m
                        - getattr(straight_through, "guarantee_point").mach.m,
                        5,
                    )
                )
                results[f"Re{_t}"].append(round(point_interpolated.reynolds.m, 5))
                results[f"Re{_t} / Re{_sp}"].append(
                    round(
                        point_interpolated.reynolds.m
                        / getattr(straight_through, "guarantee_point").reynolds.m,
                        5,
                    )
                )
                results[f"pd{conv} (bar)"].append(
                    round(point_interpolated.disch.p("bar").m, 5)
                )
                results[f"pd{conv}/pd{_sp}"].append(
                    round(
                        point_interpolated.disch.p("bar").m
                        / getattr(straight_through, "guarantee_point").disch.p("bar").m,
                        5,
                    )
                )
                results[f"Head{_t} (kJ/kg)"].append(
                    round(point_interpolated.head.to("kJ/kg").m, 5)
                )
                results[f"Head{_t}/Head{_sp}"].append(
                    round(
                        point_interpolated.head.to("kJ/kg").m
                        / getattr(straight_through, "guarantee_point")
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
                        / getattr(straight_through, "guarantee_point")
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
                        / getattr(straight_through, "guarantee_point")
                        .flow_v.to("m³/h")
                        .m,
                        5,
                    )
                )
                results[f"W{_t} (kW)"].append(None)
                results[f"W{_t}/W{_sp}"].append(None)
                results[f"W{conv} (kW)"].append(
                    round(point_interpolated.power_shaft.to("kW").m, 5)
                )
                if bearing_mechanical_losses:
                    results[f"W{conv}/W{_sp}"].append(
                        round(
                            point_interpolated.power_shaft.to("kW").m
                            / Q_(
                                float(st.session_state["power_shaft_point_guarantee"]),
                                parameters_map["power_shaft"]["points"][
                                    "data_sheet_units"
                                ],
                            )
                            .to("kW")
                            .m,
                            5,
                        )
                    )
                else:
                    results[f"W{conv}/W{_sp}"].append(
                        round(
                            point_interpolated.power_shaft.to("kW").m
                            / Q_(
                                float(st.session_state["power_point_guarantee"]),
                                parameters_map["power"]["points"]["data_sheet_units"],
                            )
                            .to("kW")
                            .m,
                            5,
                        )
                    )
                results[f"Eff{_t}"].append(round(point_interpolated.eff.m, 5))
                results[f"Eff{conv}"].append(round(point_interpolated.eff.m, 5))

                df_results = pd.DataFrame(results)
                rename_index = {
                    i: f"Point {i + 1}"
                    for i in range(len(getattr(straight_through, "points_flange_t")))
                }
                rename_index[len(getattr(straight_through, "points_flange_t"))] = (
                    "Guarantee Point"
                )

                df_results.rename(
                    index=rename_index,
                    inplace=True,
                )

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

                for _point in ["Guarantee Point"]:
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
                    file_name="results.xlsx",
                    mime="application/vnd.ms-excel",
                    width="stretch",
                )

                @st.cache_data
                def generate_st_plots(
                    _straight_through,
                    _point_interpolated,
                    compressor_hash,
                    plot_limits,
                    show_points,
                ):
                    mach_plot = _point_interpolated.plot_mach()
                    reynolds_plot = _point_interpolated.plot_reynolds()

                    plots_dict = {}
                    for curve in ["head", "eff", "discharge_pressure", "power"]:
                        flow_v_units = plot_limits.get(curve, {}).get("x", {}).get("units")
                        curve_units = plot_limits.get(curve, {}).get("y", {}).get("units")

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
                            _straight_through,
                            f"{curve_plot_method}_plot",
                        )(
                            show_points=show_points,
                            **kwargs,
                        )
                        plots_dict[curve] = r_getattr(
                            _point_interpolated, f"{curve_plot_method}_plot"
                        )(
                            fig=plots_dict[curve],
                            show_points=show_points,
                            **kwargs,
                        )

                        plots_dict[curve].data[0].update(
                            name=f"Converted Curve {_straight_through.speed_operational.to('rpm').m:.0f} RPM",
                        )
                        if curve == "discharge_pressure":
                            plots_dict[curve].data[1].update(
                                name=f"Flow: {_point_interpolated.flow_v.to(flow_v_units):.~2f}, {curve.capitalize()}: {r_getattr(_point_interpolated, curve_plot_method)(curve_units):.~2f}".replace(
                                    "m ** 3 / h", "m³/h"
                                ).replace("Discharge_pressure", "Disch. p")
                            )
                        else:
                            plots_dict[curve].data[1].update(
                                name=f"Flow: {_point_interpolated.flow_v.to(flow_v_units):.~2f}, {curve.capitalize()}: {r_getattr(_point_interpolated, curve_plot_method).to(curve_units):.~2f}".replace(
                                    "m ** 3 / h", "m³/h"
                                ).replace("Discharge_pressure", "Disch. p")
                            )

                        plots_dict[curve].update_layout(
                            showlegend=True,
                            legend=dict(
                                yanchor="bottom",
                                y=0.01,
                                xanchor="left",
                                x=0.01,
                            ),
                        )

                        x_lower = plot_limits.get(curve, {}).get("x", {}).get("lower_limit")
                        x_upper = plot_limits.get(curve, {}).get("x", {}).get("upper_limit")
                        y_lower = plot_limits.get(curve, {}).get("y", {}).get("lower_limit")
                        y_upper = plot_limits.get(curve, {}).get("y", {}).get("upper_limit")

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
                                    plot_limits[curve]["x"]["lower_limit"],
                                    plot_limits[curve]["x"]["upper_limit"],
                                ),
                                yaxis_range=(
                                    plot_limits[curve]["y"]["lower_limit"],
                                    plot_limits[curve]["y"]["upper_limit"],
                                ),
                            )

                    return mach_plot, reynolds_plot, plots_dict

                mach_plot, reynolds_plot, plots_dict = generate_st_plots(
                    straight_through,
                    point_interpolated,
                    id(straight_through),
                    plot_limits,
                    show_points,
                )

                # Apply background images outside cache
                for curve in ["head", "eff", "discharge_pressure", "power"]:
                    if (
                        st.session_state.get(f"fig_{curve}") is not None
                        and st.session_state.get(f"fig_{curve}") != ""
                    ):
                        plots_dict[curve] = add_background_image(
                            limits=plot_limits[curve],
                            fig=plots_dict[curve],
                            image=st.session_state[f"fig_{curve}"],
                        )

                with st.container():
                    mach_col, reynolds_col = st.columns(2)
                    mach_col.plotly_chart(mach_plot, width="stretch")
                    reynolds_col.plotly_chart(reynolds_plot, width="stretch")

                with st.container():
                    head_col, eff_col = st.columns(2)
                    head_col.plotly_chart(plots_dict["head"], width="stretch")
                    eff_col.plotly_chart(plots_dict["eff"], width="stretch")

                with st.container():
                    disch_p_col, power_col = st.columns(2)
                    disch_p_col.plotly_chart(
                        plots_dict["discharge_pressure"], width="stretch"
                    )
                    power_col.plotly_chart(plots_dict["power"], width="stretch")


if __name__ == "__main__":
    run_app(main, "straight_through")
