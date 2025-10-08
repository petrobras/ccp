import io
import streamlit as st
import ccp
import json
import pandas as pd
import base64
import zipfile
import toml
import time
import sentry_sdk
import logging
from ccp.compressor import PointFirstSection, PointSecondSection, BackToBack
from ccp.config.utilities import r_getattr
from ccp.config.units import ureg
from pathlib import Path

# import everything that is common to ccp_app_straight_through and ccp_app_back_to_back
from ccp.app.common import (
    pressure_units,
    specific_heat_units,
    density_units,
    polytropic_methods,
    parameters_map,
    oil_iso_options,
    specific_heat_calculate,
    density_calculate,
    get_gas_composition,
    to_excel,
    convert,
)


sentry_sdk.init(
    dsn="https://8fd0e79dffa94dbb9747bf64e7e55047@o348313.ingest.sentry.io/4505046640623616",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)


def main():
    """The code has to be inside this main function to allow sentry to work."""
    Q_ = ccp.Q_

    assets = Path(__file__).parent / "assets"
    ccp_ico = assets / "favicon.ico"
    ccp_logo = assets / "ccp.png"
    css_path = assets / "style.css"
    with open(css_path, "r") as f:
        css = f.read()

    st.set_page_config(
        page_title="ccp",
        page_icon=str(ccp_ico),
        layout="wide",
    )

    def image_base64(im):
        with open(im, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        encoded_image = "data:image/png;base64," + encoded_string
        html_string = f'<img src="data:image/png;base64,{encoded_string}" style="text-align: center" width="250">'
        return html_string

    with st.sidebar.container():
        st.sidebar.markdown(image_base64(ccp_logo), unsafe_allow_html=True)

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    title_alignment = """
    <p style="text-align: center; font-weight: bold; font-size:20px;">
     ccp 
    </p>
    """
    st.sidebar.markdown(title_alignment, unsafe_allow_html=True)
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

    # Create a Streamlit sidebar with a file uploader to load a session state file
    with st.sidebar.expander("📁 File"):
        with st.form("my_form", clear_on_submit=False):
            st.session_state.session_name = st.text_input(
                "Session name",
                value=st.session_state.session_name,
            )

            file = st.file_uploader("📂 Open File", type=["ccp"])
            submitted = st.form_submit_button("Load")
            save_button = st.form_submit_button("💾 Save")

        if submitted and file is not None:
            st.write("Loaded!")
            # open file with zip
            with zipfile.ZipFile(file) as my_zip:
                # get the ccp version
                try:
                    version = my_zip.read("ccp.version").decode("utf-8")
                except KeyError:
                    version = "0.3.5"

                for name in my_zip.namelist():
                    if name.endswith(".json"):
                        session_state_data = convert(
                            json.loads(my_zip.read(name)), version
                        )
                        if (
                            "div_wall_flow_m_section_1_point_1"
                            not in session_state_data
                        ):
                            raise ValueError("File is not a ccp back-to-back file.")
                # extract figures and back_to_back objects
                for name in my_zip.namelist():
                    if name.endswith(".png"):
                        session_state_data[name.split(".")[0]] = my_zip.read(name)
                    elif name.endswith(".toml"):
                        # create file object to read the toml file
                        back_to_back_file = convert(
                            io.StringIO(my_zip.read(name).decode("utf-8")), version
                        )
                        session_state_data[name.split(".")[0]] = BackToBack.load(
                            back_to_back_file
                        )

            session_state_data_copy = session_state_data.copy()
            # remove keys that cannot be set with st.session_state.update
            for key in session_state_data.keys():
                if key.startswith(
                    ("FormSubmitter", "my_form", "uploaded", "form", "table")
                ):
                    del session_state_data_copy[key]
            st.session_state.update(session_state_data_copy)
            st.session_state.session_name = file.name.replace(".ccp", "")
            st.session_state.expander_state = True
            st.rerun()

        if save_button:
            session_state_dict = dict(st.session_state)

            # create a zip file to add the data to
            file_name = f"{st.session_state.session_name}.ccp"
            session_state_dict_copy = session_state_dict.copy()
            with zipfile.ZipFile(file_name, "w") as my_zip:
                my_zip.writestr("ccp.version", ccp.__version__)
                # first save figures
                for key, value in session_state_dict.items():
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
                # then save the rest of the session state
                session_state_json = json.dumps(session_state_dict_copy)
                my_zip.writestr("session_state.json", session_state_json)

            with open(file_name, "rb") as file:
                st.download_button(
                    label="💾 Save As",
                    data=file,
                    file_name=file_name,
                    mime="application/json",
                )

    def check_correct_separator(input):
        if "," in input:
            st.error("Please use '.' as decimal separator")

    # Gas selection
    fluid_list = []
    for fluid in ccp.fluid_list.keys():
        fluid_list.append(fluid.lower())
        for possible_name in ccp.fluid_list[fluid].possible_names:
            if possible_name != fluid.lower():
                fluid_list.append(possible_name)
    fluid_list = sorted(fluid_list)
    fluid_list.insert(0, "")
    with st.form(key="form_gas_selection", enter_to_submit=False, border=False):
        with st.expander(
            "Gas Selection",
            expanded=st.session_state.expander_state,
        ):
            gas_compositions_table = {}
            gas_columns = st.columns(6)
            for i, gas_column in enumerate(gas_columns):
                gas_compositions_table[f"gas_{i}"] = {}

                gas_compositions_table[f"gas_{i}"]["name"] = gas_column.text_input(
                    "Gas Name",
                    value=f"gas_{i}",
                    key=f"gas_{i}",
                    help=(
                        """
                    Gas name will be selected in Data Sheet and Test Data.

                    Fill in gas components and molar fractions for each gas.
                    """
                        if i == 0
                        else None
                    ),
                )

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
                    "n-nonane",
                    "nitrogen",
                    "h2s",
                    "co2",
                    "h2o",
                ]

                gas_composition_list = []
                for key in st.session_state:
                    if "compositions_table" in key:
                        for column in st.session_state[key][f"gas_{i}"]:
                            if "component" in column:
                                idx = column.split("_")[1]
                                gas_composition_list.append(
                                    {
                                        "component": st.session_state[key][f"gas_{i}"][
                                            column
                                        ],
                                        "molar_fraction": st.session_state[key][
                                            f"gas_{i}"
                                        ][f"molar_fraction_{idx}"],
                                    }
                                )
                if not gas_composition_list:
                    gas_composition_list = [
                        {"component": molecule, "molar_fraction": 0.0}
                        for molecule in default_components
                    ]

                gas_composition_df = pd.DataFrame(gas_composition_list)
                gas_composition_df_edited = gas_column.data_editor(
                    gas_composition_df,
                    num_rows="dynamic",
                    key=f"table_gas_{i}_composition",
                    height=int((len(default_components) + 1) * 37.35),
                    use_container_width=True,
                    column_config={
                        "component": st.column_config.SelectboxColumn(
                            st.session_state[f"gas_{i}"],
                            options=fluid_list,
                            width="small",
                        ),
                        "molar_fraction": st.column_config.NumberColumn(
                            "mol %",
                            min_value=0.0,
                            default=0.0,
                            required=True,
                            format="%.3f",
                        ),
                    },
                )

                for column in gas_composition_df_edited:
                    for j, value in enumerate(gas_composition_df_edited[column]):
                        gas_compositions_table[f"gas_{i}"][f"{column}_{j}"] = value

            submit_composition = st.form_submit_button("Submit", type="primary")

            if "gas_compositions_table" not in st.session_state or submit_composition:
                st.session_state["gas_compositions_table"] = gas_compositions_table

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
            help="If marked, show points in the plotted curves in addition to interpolation.",
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

        def on_oil_specific_heat_change():
            if st.session_state.oil_specific_heat:
                st.session_state.oil_iso = False

        def on_oil_iso_change():
            if st.session_state.oil_iso:
                st.session_state.oil_specific_heat = False

        # add text input for the test lube oil specific heat
        st.text("Test Lube Oil")
        # select box for oil specific heat input
        (
            oil_specific_heat_checkbox_col,
            oil_specific_heat_magnitude_col,
            oil_specific_heat_unit_col,
        ) = st.columns([0.5, 0.2, 0.3])
        with oil_specific_heat_checkbox_col:
            oil_specific_heat = st.checkbox(
                "Specific Heat",
                key="oil_specific_heat",
                value=False,
                on_change=on_oil_specific_heat_change,
                help="If marked, uses this oil specific heat "
                "and density for bearing mechanical losses calculation "
                "and disables ISO oil classification.",
            )
        with oil_specific_heat_magnitude_col:
            oil_specific_heat_magnitude = st.text_input(
                "Oil Specific Heat",
                value=2.03,
                key="oil_specific_heat_magnitude",
                label_visibility="collapsed",
                disabled=not st.session_state.oil_specific_heat,
            )
        with oil_specific_heat_unit_col:
            oil_specific_heat_unit = st.selectbox(
                "Unit",
                options=specific_heat_units,
                index=specific_heat_units.index("kJ/kg/degK"),
                key="oil_specific_heat_unit",
                label_visibility="collapsed",
                disabled=not st.session_state.oil_specific_heat,
            )

        oil_density_col, oil_density_magnitude_col, oil_density_unit_col = st.columns(
            [0.5, 0.2, 0.3]
        )
        with oil_density_col:
            st.text("Density")
        with oil_density_magnitude_col:
            oil_density_magnitude = st.text_input(
                "Oil Density",
                value=846.9,
                key="oil_density_magnitude",
                label_visibility="collapsed",
                disabled=not st.session_state.oil_specific_heat,
            )
        with oil_density_unit_col:
            oil_density_unit = st.selectbox(
                "Unit",
                options=density_units,
                index=density_units.index("kg/m³"),
                key="oil_density_unit",
                label_visibility="collapsed",
                disabled=not st.session_state.oil_specific_heat,
            )
        if oil_specific_heat:
            oil_specific_heat_value = Q_(
                float(oil_specific_heat_magnitude), oil_specific_heat_unit
            ).to("kJ/kg/kelvin")
            oil_density_value = Q_(float(oil_density_magnitude), oil_density_unit).to(
                "kg/m³"
            )

        # select box for oil ISO classification input
        oil_iso_checkbox_col, oil_iso_select_box_col = st.columns([0.6, 0.4])
        with oil_iso_checkbox_col:
            oil_iso = st.checkbox(
                "Oil ISO Classification",
                key="oil_iso",
                on_change=on_oil_iso_change,
                help="If marked, uses the ISO oil classification "
                "for bearing mechanical losses calculation "
                "and disables specific heat and density input.",
            )
        with oil_iso_select_box_col:
            oil_iso_classification = st.selectbox(
                "ISO",
                options=oil_iso_options,
                index=oil_iso_options.index("VG 32"),
                key="oil_iso_classification",
                label_visibility="collapsed",
                disabled=not st.session_state.oil_iso,
            )

        st.text("Polytropic method")
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
            st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_columns)
        ]

        # fill the gas selection dropdowns with the gases selected
        def get_index_selected_gas(gas_name):
            try:
                index_gas_name = gas_options.index(st.session_state[gas_name])
            except (KeyError, ValueError):
                index_gas_name = 0
            return index_gas_name

        gas_name_section_1_point_guarantee = points_gas_columns[2].selectbox(
            "gas_section_1_point_guarantee",
            options=gas_options,
            label_visibility="collapsed",
            index=get_index_selected_gas("gas_section_1_point_guarantee"),
        )
        gas_name_section_2_point_guarantee = points_gas_columns[3].selectbox(
            "gas_section_2_point_guarantee",
            options=gas_options,
            label_visibility="collapsed",
            index=get_index_selected_gas("gas_section_2_point_guarantee"),
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
                        for i, gas in enumerate(gas_columns)
                    ]
                    col.selectbox(
                        f"gas_section_1_point_{i - 1}",
                        options=gas_options,
                        label_visibility="collapsed",
                        index=get_index_selected_gas(f"gas_section_1_point_{i - 1}"),
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
                        for i, gas in enumerate(gas_columns)
                    ]
                    col.selectbox(
                        f"gas_section_2_point_{i - 1}",
                        options=gas_options,
                        label_visibility="collapsed",
                        index=get_index_selected_gas(f"gas_section_2_point_{i - 1}"),
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
            use_container_width=True,
            help="Calculate results using the data sheet speed.",
        )
        calculate_speed_button = calculate_speed_col.button(
            "Calculate Speed",
            type="primary",
            use_container_width=True,
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
                        i: f"Point {i+1}"
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

                        def highlight_cell(
                            styled_df,
                            df,
                            row_index,
                            col_index,
                            lower_limit,
                            higher_limit,
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
                                styled_df = styled_df.map(
                                    lambda x: (
                                        "background-color: #C8E6C9"
                                        if x == cell_value
                                        else ""
                                    )
                                ).map(
                                    lambda x: (
                                        "font-color: #33691E" if x == cell_value else ""
                                    )
                                )

                            else:
                                styled_df = styled_df.map(
                                    lambda x: (
                                        "background-color: #FFCDD2"
                                        if x == cell_value
                                        else ""
                                    )
                                ).map(
                                    lambda x: (
                                        "font-color: #FFCDD2" if x == cell_value else ""
                                    )
                                )

                            return styled_df

                        styled_df_results = df_results.style

                        mach_limits = point_interpolated.mach_limits()
                        styled_df_results = highlight_cell(
                            styled_df_results,
                            df_results,
                            "Guarantee Point",
                            f"Mach{_t} - Mach{_sp}",
                            mach_limits["lower"],
                            mach_limits["upper"],
                        )
                        reynolds_limits = point_interpolated.reynolds_limits()
                        styled_df_results = highlight_cell(
                            styled_df_results,
                            df_results,
                            "Guarantee Point",
                            f"Re{_t} / Re{_sp}",
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
                            use_container_width=True,
                        )

                        with st.container():
                            mach_col, reynolds_col = st.columns(2)
                            mach_col.plotly_chart(
                                point_interpolated.plot_mach(), use_container_width=True
                            )
                            reynolds_col.plotly_chart(
                                point_interpolated.plot_reynolds(),
                                use_container_width=True,
                            )

                        def add_background_image(
                            curve_name=None, section=None, fig=None, image=None
                        ):
                            """Add png file to plot background

                            Parameters
                            ----------
                            curve_name : str
                                The name of the curve to add the background image to.
                            section : str
                                Compressor section.
                            fig : plotly.graph_objects.Figure
                                The figure to add the background image to.
                            image : io.BytesIO
                                The image to add to the background.
                            """
                            encoded_string = base64.b64encode(image).decode()
                            encoded_image = "data:image/png;base64," + encoded_string
                            fig.add_layout_image(
                                dict(
                                    source=encoded_image,
                                    xref="x",
                                    yref="y",
                                    x=plot_limits[curve_name][section]["x"][
                                        "lower_limit"
                                    ],
                                    y=plot_limits[curve_name][section]["y"][
                                        "upper_limit"
                                    ],
                                    sizex=float(
                                        plot_limits[curve_name][section]["x"][
                                            "upper_limit"
                                        ]
                                    )
                                    - float(
                                        plot_limits[curve_name][section]["x"][
                                            "lower_limit"
                                        ]
                                    ),
                                    sizey=float(
                                        plot_limits[curve_name][section]["y"][
                                            "upper_limit"
                                        ]
                                    )
                                    - float(
                                        plot_limits[curve_name][section]["y"][
                                            "lower_limit"
                                        ]
                                    ),
                                    sizing="stretch",
                                    opacity=0.5,
                                    layer="below",
                                )
                            )
                            return fig

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
                                    ).replace(
                                        "Discharge_pressure", "Disch. p"
                                    )
                                )
                            else:
                                plots_dict[curve].data[1].update(
                                    name=f"Flow: {point_interpolated.flow_v.to(flow_v_units):.~2f}, {curve.capitalize()}: {r_getattr(point_interpolated, curve_plot_method).to(curve_units):.~2f}".replace(
                                        "m ** 3 / h", "m³/h"
                                    ).replace(
                                        "Discharge_pressure", "Disch. p"
                                    )
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
                                    curve_name=curve,
                                    fig=plots_dict[curve],
                                    section=sec,
                                    image=st.session_state[f"fig_{curve}_{sec}"],
                                )

                        with st.container():
                            head_col, eff_col = st.columns(2)
                            head_col.plotly_chart(
                                plots_dict["head"], use_container_width=True
                            )
                            eff_col.plotly_chart(
                                plots_dict["eff"], use_container_width=True
                            )

                        with st.container():
                            disch_p_col, power_col = st.columns(2)
                            disch_p_col.plotly_chart(
                                plots_dict["discharge_pressure"],
                                use_container_width=True,
                            )
                            power_col.plotly_chart(
                                plots_dict["power"], use_container_width=True
                            )

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
    try:
        main()
    except Exception as e:
        logging.info("app: back_to_back")
        logging.info(f"session state: {st.session_state}")
        logging.error(e)
        raise e
