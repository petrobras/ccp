import ccp
import io
import zipfile
import streamlit as st
import pandas as pd
import base64
import time
import sentry_sdk
import logging
import json
import toml
import tempfile
import os
import shutil
from pathlib import Path

# import everything that is common to ccp_app_straight_through and ccp_app_back_to_back
from ccp.app.common import (
    pressure_units,
    temperature_units,
    flow_units,
    flow_v_units,
    speed_units,
    head_units,
    power_units,
    parameters_map,
    get_gas_composition,
)

sentry_sdk.init(
    dsn="https://8fd0e79dffa94dbb9747bf64e7e55047@o348313.ingest.sentry.io/4505046640623616",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    auto_enabling_integrations=False,
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
    ## Curves Conversion
    """
    )

    def get_session():
        # Initialize session state variables
        if "session_name" not in st.session_state:
            st.session_state.session_name = ""
        if "impeller_conversion_state" not in st.session_state:
            st.session_state.impeller_conversion_state = ""
        if "original_impeller" not in st.session_state:
            st.session_state.original_impeller = None
        if "converted_impeller" not in st.session_state:
            st.session_state.converted_impeller = None
        if "expander_state" not in st.session_state:
            st.session_state.expander_state = False
        if "ccp_version" not in st.session_state:
            st.session_state.ccp_version = ccp.__version__
        if "app_type" not in st.session_state:
            st.session_state.app_type = "curves_conversion"
        if "uploaded_csv_files" not in st.session_state:
            st.session_state.uploaded_csv_files = {}

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
                        session_state_data = json.loads(my_zip.read(name))
                        # Check if it's an impeller conversion file
                        if (
                            "app_type" not in session_state_data
                            or session_state_data.get("app_type") != "curves_conversion"
                        ):
                            # Set as impeller conversion file
                            session_state_data["app_type"] = "curves_conversion"

                # extract CSV files and impeller objects
                csv_file_number = 1
                for name in my_zip.namelist():
                    if name.endswith(".csv"):
                        session_state_data[f"curves_file_{csv_file_number}"] = {
                            "name": name,
                            "content": my_zip.read(name),
                        }
                        csv_file_number += 1
                    if name.endswith(".toml"):
                        # create file object to read the toml file
                        impeller_file = io.StringIO(my_zip.read(name).decode("utf-8"))
                        if name.startswith("original_impeller"):
                            session_state_data["original_impeller"] = ccp.Impeller.load(
                                impeller_file
                            )
                        elif name.startswith("converted_impeller"):
                            session_state_data["converted_impeller"] = (
                                ccp.Impeller.load(impeller_file)
                            )

            session_state_data_copy = session_state_data.copy()
            # remove keys that cannot be set with st.session_state.update
            for key in list(session_state_data.keys()):
                if key.startswith(
                    (
                        "FormSubmitter",
                        "my_form",
                        "uploaded",
                        "form",
                        "table",
                    )
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

                # Save impeller objects
                for key, value in session_state_dict.items():
                    if isinstance(value, ccp.Impeller):
                        if key == "original_impeller":
                            my_zip.writestr(
                                "original_impeller.toml",
                                toml.dumps(value._dict_to_save()),
                            )
                        elif key == "converted_impeller":
                            my_zip.writestr(
                                "converted_impeller.toml",
                                toml.dumps(value._dict_to_save()),
                            )
                        del session_state_dict_copy[key]
                    if key.startswith("curves_file_"):
                        my_zip.writestr(
                            session_state_dict[key]["name"],
                            session_state_dict[key]["content"],
                        )
                        del session_state_dict_copy[key]

                # Set app type
                session_state_dict_copy["app_type"] = "impeller_conversion"

                # Remove file uploader keys and other non-serializable keys
                keys_to_remove = []
                for key in session_state_dict_copy.keys():
                    if key.startswith(
                        (
                            "FormSubmitter",
                            "my_form",
                            "uploaded",
                            "form",
                            "table",
                        )
                    ) or isinstance(
                        session_state_dict_copy[key],
                        (bytes, st.runtime.uploaded_file_manager.UploadedFile),
                    ):
                        keys_to_remove.append(key)

                for key in keys_to_remove:
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
        with st.expander("Gas Selection", expanded=st.session_state.expander_state):
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
                    Gas name will be selected for original and new suction conditions.

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

    # Original Impeller Suction Conditions
    with st.expander(
        "Original Curves Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Original Suction Conditions")
        st.markdown("Define the suction conditions for the original curves data.")

        # Gas selection for original impeller
        gas_options = [st.session_state[f"gas_{i}"] for i in range(6)]

        # Gas selection container
        gas_container = st.container()
        gas_col1, gas_col2, gas_col3 = gas_container.columns(3)

        gas_col1.markdown("Gas Selection")
        gas_col2.markdown("")
        original_gas = gas_col3.selectbox(
            "Gas for Original Curves",
            options=gas_options,
            key="original_gas_selection",
            label_visibility="collapsed",
            help="Select the gas composition for the original curves",
        )

        # Suction Pressure
        pressure_container = st.container()
        pressure_col1, pressure_col2, pressure_col3 = pressure_container.columns(3)

        pressure_col1.markdown("Suction Pressure")
        original_suc_p_unit = pressure_col2.selectbox(
            "Original Suction P Unit",
            options=pressure_units,
            key="original_suc_p_unit",
            label_visibility="collapsed",
            index=0,
        )
        original_suc_p = pressure_col3.number_input(
            "Original Suction Pressure",
            key="original_suc_p",
            label_visibility="collapsed",
            help="Suction pressure for the original curves data",
        )

        # Suction Temperature
        temperature_container = st.container()
        temperature_col1, temperature_col2, temperature_col3 = (
            temperature_container.columns(3)
        )

        temperature_col1.markdown("Suction Temperature")
        original_suc_t_unit = temperature_col2.selectbox(
            "Original Suction T Unit",
            options=temperature_units,
            key="original_suc_t_unit",
            label_visibility="collapsed",
            index=1,
        )
        original_suc_t = temperature_col3.number_input(
            "Original Suction Temperature",
            key="original_suc_t",
            label_visibility="collapsed",
            help="Suction temperature for the original curves data",
        )

    # Original Impeller Curves
    with st.expander("Original Curves", expanded=st.session_state.expander_state):
        # Units for curves
        st.markdown("### Loaded Curves Units")
        loaded_curves_units_cols = st.columns(6)

        with loaded_curves_units_cols[0]:
            loaded_curves_speed_units = st.selectbox(
                "Speed",
                options=speed_units,
                key="loaded_curves_speed_units",
                index=0,
            )
        with loaded_curves_units_cols[1]:
            loaded_curves_flow_units = st.selectbox(
                "Flow",
                options=flow_units,
                key="loaded_curves_flow_units",
                index=6,
            )
        with loaded_curves_units_cols[2]:
            loaded_curves_disch_p_units = st.selectbox(
                "Disch. Pres.",
                options=pressure_units,
                key="loaded_curves_disch_p_units",
                index=0,
            )
        with loaded_curves_units_cols[3]:
            loaded_curves_disch_T_units = st.selectbox(
                "Disch. Temp.",
                options=temperature_units,
                key="loaded_curves_disch_T_units",
                index=0,
            )
        with loaded_curves_units_cols[4]:
            loaded_curves_head_units = st.selectbox(
                "Head",
                options=head_units,
                key="loaded_curves_head_units",
                index=0,
            )
        with loaded_curves_units_cols[5]:
            loaded_curves_power_units = st.selectbox(
                "Power",
                options=power_units,
                key="loaded_curves_power_units",
                index=0,
            )

        st.markdown("### Plot Curves Units")

        plot_curves_units_cols = st.columns(6)

        with plot_curves_units_cols[0]:
            plot_curves_speed_units = st.selectbox(
                "Speed",
                options=speed_units,
                key="plot_curves_speed_units",
                index=0,
            )
        with plot_curves_units_cols[1]:
            plot_curves_flow_units = st.selectbox(
                "Flow",
                options=flow_units,
                key="plot_curves_flow_units",
                index=6,
            )
        with plot_curves_units_cols[2]:
            plot_curves_disch_p_units = st.selectbox(
                "Disch. Pres.",
                options=pressure_units,
                key="plot_curves_disch_p_units",
                index=0,
            )
        with plot_curves_units_cols[3]:
            plot_curves_disch_T_units = st.selectbox(
                "Disch. Temp.",
                options=temperature_units,
                key="plot_curves_disch_T_units",
                index=0,
            )
        with plot_curves_units_cols[4]:
            plot_curves_head_units = st.selectbox(
                "Head",
                options=head_units,
                key="plot_curves_head_units",
                index=0,
            )
        with plot_curves_units_cols[5]:
            plot_curves_power_units = st.selectbox(
                "Power",
                options=power_units,
                key="plot_curves_power_units",
                index=0,
            )

        if loaded_curves_flow_units in flow_v_units:
            loaded_curves_flow_v_units = loaded_curves_flow_units
        else:
            loaded_curves_flow_v_units = "m³/h"

        if plot_curves_flow_units in flow_v_units:
            plot_curves_flow_v_units = plot_curves_flow_units
        else:
            plot_curves_flow_v_units = "m³/h"

        st.markdown("### Upload Engauge Digitized Files")
        st.markdown(
            """
        Upload CSV files from Engauge Digitizer containing the original performance curves. \n\n
        If you are uploading head and eff files, they should be saved with the following convention:\n
            - <curve-name>-head.csv
            - <curve-name>-eff.csv
        Check in the link how to get points with Engauge Digitizer:
        [Engauge Digitizer Guide](https://ccp-centrifugal-compressor-performance.readthedocs.io/en/stable/user_guide/engauge.html).
        """
        )

        # File upload areas
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Performance Curves File 1")
            uploaded_curves_file_1 = st.file_uploader(
                "Upload first curves file",
                type=["csv"],
                key="uploaded_curves_file_1",
                help="CSV file from Engauge Digitizer with performance curve data",
            )

        with col2:
            st.markdown("#### Performance Curves File 2")
            uploaded_curves_file_2 = st.file_uploader(
                "Upload second curves file",
                type=["csv"],
                key="uploaded_curves_file_2",
                help="CSV file from Engauge Digitizer with performance curve data (optional)",
            )

        # Store uploaded files in session state immediately upon upload
        if uploaded_curves_file_1 is not None:
            st.session_state["curves_file_1"] = {
                "name": uploaded_curves_file_1.name,
                "content": uploaded_curves_file_1.getvalue(),
            }

        if uploaded_curves_file_2 is not None:
            st.session_state["curves_file_2"] = {
                "name": uploaded_curves_file_2.name,
                "content": uploaded_curves_file_2.getvalue(),
            }

        # Load impeller button
        load_impeller_button = st.button(
            "Load Original Curves",
            type="secondary",
            help="Load the original curves from the uploaded files",
        )

        # Process uploaded files
        if load_impeller_button:
            # Check if we have files from uploader or from session state
            try:
                has_files_from_session = bool(
                    bool(st.session_state.curves_file_1)
                    and bool(st.session_state.curves_file_2)
                )
            except AttributeError as e:
                st.error(f"No curves files uploaded: {str(e)}")
                logging.error(f"No curves files uploaded: {e}")
                return

            if has_files_from_session:
                try:
                    # Create temporary directory for files

                    # Function to extract curve name from filename
                    def extract_curve_name(filename):
                        """Extract curve name from filename, removing suffix like -head, -eff, etc."""
                        # Remove file extension
                        name = filename.rsplit(".", 1)[0]

                        # Check for known suffixes
                        suffixes = [
                            "head",
                            "eff",
                            "power",
                            "power_shaft",
                            "pressure_ratio",
                            "disch_T",
                        ]
                        for suffix in suffixes:
                            if name.endswith(f"-{suffix}"):
                                return name[: -len(f"-{suffix}")]

                        # If no suffix found, return the full name
                        return name

                    # Create temporary directory
                    temp_dir = tempfile.mkdtemp()
                    temp_path = Path(temp_dir)

                    # Get curve name from first available file
                    filenames = [
                        st.session_state["curves_file_1"]["name"],
                        st.session_state["curves_file_2"]["name"],
                    ]
                    if filenames:
                        curve_name = extract_curve_name(filenames[0])
                        st.session_state.curve_name = curve_name

                        # Save session state CSV files to temporary directory
                        for csv_file in [
                            st.session_state["curves_file_1"],
                            st.session_state["curves_file_2"],
                        ]:
                            file_path = temp_path / csv_file["name"]
                            with open(file_path, "wb") as f:
                                f.write(csv_file["content"])
                    else:
                        st.error("No CSV files found in session state")
                        return

                    # Create suction state
                    gas_composition_original = get_gas_composition(
                        original_gas, gas_compositions_table, default_components
                    )

                    original_suc_state = ccp.State(
                        p=Q_(original_suc_p, original_suc_p_unit),
                        T=Q_(original_suc_t, original_suc_t_unit),
                        fluid=gas_composition_original,
                    )

                    # Load impeller from Engauge files
                    progress_bar = st.progress(0, text="Loading curves from files...")

                    original_impeller = ccp.Impeller.load_from_engauge_csv(
                        suc=original_suc_state,
                        curve_name=curve_name,
                        curve_path=temp_path,
                        flow_units=loaded_curves_flow_units,
                        disch_p_units=loaded_curves_disch_p_units,
                        disch_T_units=loaded_curves_disch_T_units,
                        head_units=loaded_curves_head_units,
                        power_units=loaded_curves_power_units,
                        speed_units=loaded_curves_speed_units,
                    )

                    progress_bar.progress(100, text="Curves loaded successfully!")
                    time.sleep(0.5)
                    progress_bar.empty()

                    # Store in session state
                    st.session_state.original_impeller = original_impeller

                    # Clean up temporary files
                    shutil.rmtree(temp_dir)

                    st.success(
                        f"Original curves loaded successfully with {len(original_impeller.points)} points!"
                    )

                except Exception as e:
                    st.error(f"Error loading impeller: {str(e)}")
                    logging.error(f"Error loading impeller: {e}")

                    # Clean up temporary directory on error
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass

        if st.session_state.original_impeller is not None:
            # Display basic info
            st.markdown("#### Loaded Curves Information")
            st.write(f"Curve name: {st.session_state.curve_name}")
            st.write(
                f"Number of points: {len(st.session_state.original_impeller.points)}"
            )
            st.write(
                f"Number of curves: {len(st.session_state.original_impeller.curves)}"
            )
            if st.session_state.original_impeller.points:
                speeds = [
                    p.speed.to("rpm").m
                    for p in st.session_state.original_impeller.points
                ]
                st.write(f"Speed range: {min(speeds):.0f} - {max(speeds):.0f} RPM")
                flows = [
                    p.flow_v.to("m³/h").m
                    for p in st.session_state.original_impeller.points
                ]
                st.write(f"Flow range: {min(flows):.2f} - {max(flows):.2f} m³/h")

            # Display curves
            st.markdown("#### Curves")

            # Project Flow
            project_flow_container = st.container()
            (
                project_flow_col1,
                project_flow_col2,
                dummy_project_flow_col3,
                dummy_project_flow_col4,
            ) = project_flow_container.columns(4)
            project_flow_col1.markdown(
                f"Operational Flow (**{plot_curves_flow_v_units}**)"
            )
            project_flow = project_flow_col2.number_input(
                "Operational Flow (m³/h)",
                min_value=0.0,
                value=st.session_state.original_impeller.points[0]
                .flow_v.to(plot_curves_flow_v_units)
                .m,
                help="Select an operational flow to display the curves at that flow",
                label_visibility="collapsed",
            )
            # Project Speed
            project_speed_container = st.container()
            (
                project_speed_col1,
                project_speed_col2,
                dummy_project_speed_col3,
                dummy_project_speed_col4,
            ) = project_speed_container.columns(4)
            project_speed_col1.markdown(
                f"Operational Speed (**{plot_curves_speed_units}**)"
            )
            project_speed = project_speed_col2.number_input(
                "Operational Speed (RPM)",
                min_value=0.0,
                value=st.session_state.original_impeller.points[0]
                .speed.to(plot_curves_speed_units)
                .m,
                help="Select an operational speed to display the curves at that speed",
                label_visibility="collapsed",
            )

            @st.cache_data
            def generate_plots(
                _impeller,
                impeller_hash,  # Manual invalidation to avoid caching issues with ccp.Impeller object
                point_flow,
                point_flow_v_units,
                point_speed,
                point_speed_units,
            ):
                head_plot = _impeller.head_plot(
                    flow_v_units=plot_curves_flow_v_units,
                    head_units=plot_curves_head_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                power_plot = _impeller.power_plot(
                    flow_v_units=plot_curves_flow_v_units,
                    power_units=plot_curves_power_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                disch_T_plot = _impeller.disch.T_plot(
                    flow_v_units=plot_curves_flow_v_units,
                    temperature_units=plot_curves_disch_T_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                eff_plot = _impeller.eff_plot(
                    flow_v_units=plot_curves_flow_v_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                disch_p_plot = _impeller.disch.p_plot(
                    flow_v_units=plot_curves_flow_v_units,
                    p_units=plot_curves_disch_p_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                point = _impeller.point(
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )

                return (
                    head_plot,
                    power_plot,
                    disch_T_plot,
                    eff_plot,
                    disch_p_plot,
                    point,
                )

            (
                head_plot,
                power_plot,
                disch_T_plot,
                eff_plot,
                disch_p_plot,
                project_point,
            ) = generate_plots(
                st.session_state.original_impeller,
                hash(st.session_state.original_impeller),  # Manual invalidation
                project_flow,
                plot_curves_flow_v_units,
                project_speed,
                plot_curves_speed_units,
            )

            # Display 4 plots (head, eff, power, discharge pressure) in 2 columns and 2 rows
            plot_col1, plot_col2 = st.columns(2)
            with plot_col1:
                st.plotly_chart(
                    head_plot,
                    use_container_width=True,
                )
                st.plotly_chart(
                    power_plot,
                    use_container_width=True,
                )
                st.plotly_chart(
                    disch_T_plot,
                    use_container_width=True,
                )
            with plot_col2:
                st.plotly_chart(
                    eff_plot,
                    use_container_width=True,
                )
                st.plotly_chart(
                    disch_p_plot,
                    use_container_width=True,
                )
                # Display summary table
                st.markdown("#### Project Point")
                st.code(
                    f"""
                            -----------------------------\n 
                                Speed:                 {project_point.speed.to('rpm').m:.0f} {plot_curves_speed_units} 
                                Flow:                  {project_point.flow_v.to(plot_curves_flow_v_units).m:.2f} {plot_curves_flow_v_units} 
                                Head:                  {project_point.head.to(plot_curves_head_units).m:.2f} {plot_curves_head_units} 
                                Eff:                   {project_point.eff.m:.2f} % 
                                Power:                 {project_point.power.to(plot_curves_power_units).m:.2f} {plot_curves_power_units} 

                                Suction Conditions
                                --------------------
                                Suction Pressure:      {project_point.suc.p(plot_curves_disch_p_units).m:.2f} {plot_curves_disch_p_units} 
                                Suction Temperature:   {project_point.suc.T(plot_curves_disch_T_units).m:.2f} {plot_curves_disch_T_units} 

                                Discharge Conditions
                                --------------------
                                Discharge Pressure:    {project_point.disch.p(plot_curves_disch_p_units).m:.2f} {plot_curves_disch_p_units} 
                                Discharge Temperature: {project_point.disch.T(plot_curves_disch_T_units).m:.2f} {plot_curves_disch_T_units} 
    
"""
                )

    # New Suction Conditions
    with st.expander(
        "New Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Target Suction Conditions")
        st.markdown("Define the new suction conditions for the curves conversion.")

        # Gas selection container
        new_gas_container = st.container()
        new_gas_col1, new_gas_col2, new_gas_col3 = new_gas_container.columns(3)

        new_gas_col1.markdown("Gas Selection")
        new_gas_col2.markdown("")
        new_gas = new_gas_col3.selectbox(
            "Gas for New Conditions",
            options=gas_options,
            key="new_gas_selection",
            label_visibility="collapsed",
            help="Select the gas composition for the new suction conditions",
        )

        # New Suction Pressure
        new_pressure_container = st.container()
        new_pressure_col1, new_pressure_col2, new_pressure_col3 = (
            new_pressure_container.columns(3)
        )

        new_pressure_col1.markdown("Suction Pressure")
        new_suc_p_unit = new_pressure_col2.selectbox(
            "New Suction P Unit",
            options=pressure_units,
            key="new_suc_p_unit",
            label_visibility="collapsed",
            index=0,
        )
        new_suc_p = new_pressure_col3.number_input(
            "New Suction Pressure",
            key="new_suc_p",
            label_visibility="collapsed",
            help="New suction pressure",
        )

        # New Suction Temperature
        new_temperature_container = st.container()
        new_temperature_col1, new_temperature_col2, new_temperature_col3 = (
            new_temperature_container.columns(3)
        )

        new_temperature_col1.markdown("Suction Temperature")
        new_suc_t_unit = new_temperature_col2.selectbox(
            "New Suction T Unit",
            options=temperature_units,
            key="new_suc_t_unit",
            label_visibility="collapsed",
            index=1,
        )
        new_suc_t = new_temperature_col3.number_input(
            "New Suction Temperature",
            key="new_suc_t",
            label_visibility="collapsed",
            help="New suction temperature",
        )

    # Conversion Options
    with st.expander("Conversion Options", expanded=st.session_state.expander_state):
        st.markdown("### Conversion Parameters")

        col1, col2 = st.columns(2)

        with col1:
            find_method = st.selectbox(
                "Find Method",
                options=["speed", "volume_ratio"],
                help="Method for conversion: 'speed' keeps volume ratio constant, 'volume_ratio' uses specified speed",
            )

        with col2:
            speed_option = st.selectbox(
                "Speed Option",
                options=["same", "calculate"],
                help="Keep same speed or calculate new speed",
            )

            if speed_option == "calculate":
                speed_option_arg = None
            else:
                speed_option_arg = "same"

    # Convert Button
    convert_button = st.button(
        "Convert Curves",
        type="primary",
        use_container_width=True,
        help="Convert the curves to new suction conditions",
    )

    # Conversion Process
    if convert_button:
        # Validate inputs
        if st.session_state.original_impeller is None:
            st.error(
                "Please load the original curves first using the 'Load Original Curves' button"
            )
            return

        if new_suc_p <= 0 or new_suc_t <= 0:
            st.error("Please fill in all new suction condition values")
            return

        progress_bar = st.progress(0, text="Starting conversion...")

        try:
            # Get original impeller from session state
            original_impeller = st.session_state.original_impeller

            progress_bar.progress(30, text="Creating new suction conditions...")

            # Create new suction conditions
            gas_composition_new = get_gas_composition(
                new_gas, gas_compositions_table, default_components
            )

            new_suc_state = ccp.State(
                p=Q_(new_suc_p, new_suc_p_unit),
                T=Q_(new_suc_t, new_suc_t_unit),
                fluid=gas_composition_new,
            )

            progress_bar.progress(60, text="Converting curves...")

            # Convert impeller
            conversion_kwargs = {
                "original_impeller": original_impeller,
                "suc": new_suc_state,
                "find": find_method,
                "speed": speed_option_arg,
            }

            converted_impeller = ccp.Impeller.convert_from(**conversion_kwargs)
            st.session_state.converted_impeller = converted_impeller

            progress_bar.progress(100, text="Conversion complete!")
            time.sleep(0.5)
            progress_bar.empty()

            st.success("Curves conversion completed successfully!")

        except Exception as e:
            st.error(f"Error during conversion: {str(e)}")
            logging.error(f"Conversion error: {e}")
            progress_bar.empty()
            return

    # Results Display
    if st.session_state.converted_impeller is not None:
        with st.expander("Conversion Results", expanded=True):
            st.markdown("### Converted Curves")

            original_imp = st.session_state.original_impeller
            converted_imp = st.session_state.converted_impeller

            # Display summary
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Original Curves")
                st.write(f"Number of points: {len(original_imp.points)}")
                st.write(
                    f"Speed range: {min(p.speed.to('rpm').m for p in original_imp.points):.0f} - {max(p.speed.to('rpm').m for p in original_imp.points):.0f} RPM"
                )
                st.write(
                    f"Flow range: {min(p.flow_v.to('m³/h').m for p in original_imp.points):.2f} - {max(p.flow_v.to('m³/h').m for p in original_imp.points):.2f} m³/h"
                )

            with col2:
                st.markdown("#### Converted Curves")
                st.write(f"Number of points: {len(converted_imp.points)}")
                st.write(
                    f"Speed range: {min(p.speed.to('rpm').m for p in converted_imp.points):.0f} - {max(p.speed.to('rpm').m for p in converted_imp.points):.0f} RPM"
                )
                st.write(
                    f"Flow range: {min(p.flow_v.to('m³/h').m for p in converted_imp.points):.2f} - {max(p.flow_v.to('m³/h').m for p in converted_imp.points):.2f} m³/h"
                )

            # Performance curves
            st.markdown("#### Performance Curves")

            # Display curves
            st.markdown("#### Curves")

            # Give the user the option to select an operational flow
            # New Flow
            new_flow_container = st.container()
            new_flow_col1, new_flow_col2, dummy_new_flow_col3, dummy_new_flow_col4 = (
                new_flow_container.columns(4)
            )
            new_flow_col1.markdown(f"Operational Flow (**{plot_curves_flow_v_units}**)")
            # make so that new_flow_v_units is equal to the plot_curves_flow_v_units
            new_flow = new_flow_col2.number_input(
                "Operational Flow (m³/h)",
                min_value=0.0,
                value=st.session_state.converted_impeller.points[0]
                .flow_v.to(plot_curves_flow_v_units)
                .m,
                help="Select an operational flow to display the curves at that flow",
                label_visibility="collapsed",
                key="new_flow_input",
            )
            # New Speed
            new_speed_container = st.container()
            (
                new_speed_col1,
                new_speed_col2,
                dummy_new_speed_col3,
                dummy_new_speed_col4,
            ) = new_speed_container.columns(4)
            new_speed_col1.markdown(
                f"Operational Speed (**{plot_curves_speed_units}**)"
            )
            new_speed = new_speed_col2.number_input(
                "Operational Speed (RPM)",
                min_value=0.0,
                value=st.session_state.converted_impeller.points[0]
                .speed.to(plot_curves_speed_units)
                .m,
                help="Select an operational speed to display the curves at that speed",
                label_visibility="collapsed",
                key="new_speed_input",
            )

            (
                new_head_plot,
                new_power_plot,
                new_disch_T_plot,
                new_eff_plot,
                new_disch_p_plot,
                new_point,
            ) = generate_plots(
                st.session_state.converted_impeller,
                hash(st.session_state.converted_impeller),  # Manual invalidation
                new_flow,
                plot_curves_flow_v_units,
                new_speed,
                plot_curves_speed_units,
            )

            # Display 4 plots (head, eff, power, discharge pressure) in 2 columns and 2 rows
            plot_conv_col1, plot_conv_col2 = st.columns(2)
            with plot_conv_col1:
                st.plotly_chart(
                    new_head_plot,
                    use_container_width=True,
                )
                st.plotly_chart(
                    new_power_plot,
                    use_container_width=True,
                )
                st.plotly_chart(
                    new_disch_T_plot,
                    use_container_width=True,
                )
            with plot_conv_col2:
                st.plotly_chart(
                    new_eff_plot,
                    use_container_width=True,
                )
                st.plotly_chart(
                    new_disch_p_plot,
                    use_container_width=True,
                )
                st.markdown("#### New Point")

                st.code(
                    f"""
                            -----------------------------\n 
                                Speed:                 {new_point.speed.to('rpm').m:.0f} {plot_curves_speed_units} 
                                Flow:                  {new_point.flow_v.to(plot_curves_flow_v_units).m:.2f} {plot_curves_flow_v_units} 
                                Head:                  {new_point.head.to(plot_curves_head_units).m:.2f} {plot_curves_head_units} 
                                Eff:                   {new_point.eff.m:.2f} % 
                                Power:                 {new_point.power.to(plot_curves_power_units).m:.2f} {plot_curves_power_units} 

                                Suction Conditions
                                --------------------
                                Suction Pressure:      {new_point.suc.p(plot_curves_disch_p_units).m:.2f} {plot_curves_disch_p_units} 
                                Suction Temperature:   {new_point.suc.T(plot_curves_disch_T_units).m:.2f} {plot_curves_disch_T_units} 

                                Discharge Conditions
                                --------------------
                                Discharge Pressure:    {new_point.disch.p(plot_curves_disch_p_units).m:.2f} {plot_curves_disch_p_units} 
                                Discharge Temperature: {new_point.disch.T(plot_curves_disch_T_units).m:.2f} {plot_curves_disch_T_units} 
    
"""
                )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.info("app: curves_conversion")
        logging.info(f"session state: {st.session_state}")
        logging.error(e)
        raise e
