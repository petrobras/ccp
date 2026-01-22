import base64
import io
import json
import logging
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import pandas as pd
import sentry_sdk
import streamlit as st
import toml

import ccp
from ccp.app.common import (
    flow_units,
    gas_selection_form,
    get_gas_composition,
    head_units,
    length_units,
    power_units,
    pressure_units,
    speed_units,
    temperature_units,
)

sentry_sdk.init(
    dsn="https://8fd0e79dffa94dbb9747bf64e7e55047@o348313.ingest.sentry.io/4505046640623616",
    traces_sample_rate=1.0,
    auto_enabling_integrations=False,
)


def fetch_pi_data(tag_mappings, n_points=3):
    """Mock PI data fetch - loads from test parquet files.

    Parameters
    ----------
    tag_mappings : dict
        Dictionary with tag mappings (used to determine which file to load).
    n_points : int, optional
        Number of points to return.

    Returns
    -------
    pd.DataFrame
        DataFrame with the requested number of points.
    """
    data_path = Path(ccp.__file__).parent / "tests/data"

    if tag_mappings.get("delta_p_tag"):
        df = pd.read_parquet(data_path / "data_delta_p.parquet")
    else:
        df = pd.read_parquet(data_path / "data.parquet")

    return df.tail(n_points)


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
        page_title="ccp - Online Monitoring",
        page_icon=str(ccp_ico),
        layout="wide",
    )

    def image_base64(im):
        with open(im, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
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
    ## Online Monitoring
    """
    )

    def get_session():
        # Initialize session state variables
        if "session_name" not in st.session_state:
            st.session_state.session_name = ""
        if "expander_state" not in st.session_state:
            st.session_state.expander_state = True
        if "ccp_version" not in st.session_state:
            st.session_state.ccp_version = ccp.__version__
        if "app_type" not in st.session_state:
            st.session_state.app_type = "online_monitoring"

        # Initialize impellers for each case
        for case in ["A", "B", "C", "D"]:
            if f"impeller_case_{case}" not in st.session_state:
                st.session_state[f"impeller_case_{case}"] = None
            if f"curves_file_1_case_{case}" not in st.session_state:
                st.session_state[f"curves_file_1_case_{case}"] = None
            if f"curves_file_2_case_{case}" not in st.session_state:
                st.session_state[f"curves_file_2_case_{case}"] = None

        # Initialize tag mappings
        if "tag_mappings" not in st.session_state:
            st.session_state.tag_mappings = {}

        # Initialize evaluation
        if "evaluation" not in st.session_state:
            st.session_state.evaluation = None

        # Initialize monitoring results
        if "monitoring_results" not in st.session_state:
            st.session_state.monitoring_results = None

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
                        # Check if it's an online monitoring file
                        if (
                            "app_type" not in session_state_data
                            or session_state_data.get("app_type") != "online_monitoring"
                        ):
                            session_state_data["app_type"] = "online_monitoring"

                # extract CSV files and impeller objects
                for name in my_zip.namelist():
                    if name.endswith(".csv"):
                        # Parse CSV filename to determine case and file number
                        # Format: curves_file_1_case_A.csv
                        if "curves_file_" in name:
                            parts = name.replace(".csv", "").split("_")
                            # Extract file number and case from filename
                            file_num = parts[2]
                            case = parts[-1]
                            session_state_data[
                                f"curves_file_{file_num}_case_{case}"
                            ] = {
                                "name": name,
                                "content": my_zip.read(name),
                            }
                    if name.endswith(".toml"):
                        # create file object to read the toml file
                        impeller_file = io.StringIO(my_zip.read(name).decode("utf-8"))
                        # Parse impeller filename: impeller_case_A.toml
                        if name.startswith("impeller_case_"):
                            case = name.replace("impeller_case_", "").replace(
                                ".toml", ""
                            )
                            session_state_data[f"impeller_case_{case}"] = (
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
                        "load_curves",
                        "fetch_data",
                        "auto_refresh",
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

                # Save impeller objects for each case
                for key, value in session_state_dict.items():
                    if isinstance(value, ccp.Impeller):
                        # Save impeller with case identifier: impeller_case_A.toml
                        my_zip.writestr(
                            f"{key}.toml",
                            toml.dumps(value._dict_to_save()),
                        )
                        del session_state_dict_copy[key]
                    # Save CSV files for each case
                    if key.startswith("curves_file_") and "_case_" in key:
                        if session_state_dict[key] is not None:
                            # Extract case and file number for filename
                            # key format: curves_file_1_case_A
                            parts = key.split("_")
                            file_num = parts[2]
                            case = parts[-1]
                            my_zip.writestr(
                                f"curves_file_{file_num}_case_{case}.csv",
                                session_state_dict[key]["content"],
                            )
                        if key in session_state_dict_copy:
                            del session_state_dict_copy[key]

                # Set app type
                session_state_dict_copy["app_type"] = "online_monitoring"

                # Remove file uploader keys and other non-serializable keys
                keys_to_remove = []
                for key in session_state_dict_copy.keys():
                    value = session_state_dict_copy[key]
                    if key.startswith(
                        (
                            "FormSubmitter",
                            "my_form",
                            "uploaded",
                            "form",
                            "table",
                            "load_curves",
                            "fetch_data",
                            "auto_refresh",
                        )
                    ) or isinstance(
                        value,
                        (bytes, st.runtime.uploaded_file_manager.UploadedFile),
                    ):
                        keys_to_remove.append(key)
                    # Also catch dicts containing bytes (like curves_file entries)
                    elif isinstance(value, dict) and any(
                        isinstance(v, bytes) for v in value.values()
                    ):
                        keys_to_remove.append(key)

                # Also remove evaluation and monitoring_results as they can't be serialized
                for key in ["evaluation", "monitoring_results", "last_fetch"]:
                    if key in session_state_dict_copy:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    if key in session_state_dict_copy:
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

    gas_compositions_table = gas_selection_form(fluid_list, default_components)

    # Design Cases Suction Conditions
    with st.expander(
        "Design Cases Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Design Suction Conditions")
        st.markdown("Define the suction conditions for each design case (A, B, C, D).")

        gas_options = [st.session_state[f"gas_{i}"] for i in range(6)]

        # Header row
        header_cols = st.columns(6)
        header_cols[0].markdown("**Parameter**")
        header_cols[1].markdown("**Unit**")
        header_cols[2].markdown("**Case A**")
        header_cols[3].markdown("**Case B**")
        header_cols[4].markdown("**Case C**")
        header_cols[5].markdown("**Case D**")

        # Gas selection row
        gas_row = st.columns(6)
        gas_row[0].markdown("Gas Selection")
        gas_row[1].markdown("")  # No unit for gas
        for idx, case in enumerate(["A", "B", "C", "D"]):
            with gas_row[idx + 2]:
                st.selectbox(
                    f"Gas Case {case}",
                    options=gas_options,
                    key=f"gas_case_{case}",
                    label_visibility="collapsed",
                )

        # Suction Pressure row
        p_row = st.columns(6)
        p_row[0].markdown("Suction Pressure")
        with p_row[1]:
            design_suc_p_unit = st.selectbox(
                "Suction Pressure Unit",
                options=pressure_units,
                key="design_suc_p_unit",
                index=0,
                label_visibility="collapsed",
            )
        for idx, case in enumerate(["A", "B", "C", "D"]):
            with p_row[idx + 2]:
                st.number_input(
                    f"Suction P Case {case}",
                    key=f"suc_p_case_{case}",
                    label_visibility="collapsed",
                    value=0.0,
                )

        # Suction Temperature row
        T_row = st.columns(6)
        T_row[0].markdown("Suction Temperature")
        with T_row[1]:
            design_suc_T_unit = st.selectbox(
                "Suction Temperature Unit",
                options=temperature_units,
                key="design_suc_T_unit",
                index=1,
                label_visibility="collapsed",
            )
        for idx, case in enumerate(["A", "B", "C", "D"]):
            with T_row[idx + 2]:
                st.number_input(
                    f"Suction T Case {case}",
                    key=f"suc_T_case_{case}",
                    label_visibility="collapsed",
                    value=0.0,
                )

    # Performance Curves Upload
    with st.expander(
        "Performance Curves Upload", expanded=st.session_state.expander_state
    ):
        st.markdown("### Upload Engauge Digitized Files")
        st.markdown(
            """
        Upload CSV files from Engauge Digitizer containing the performance curves for each design case.
        Files should be saved with the convention: `<curve-name>-head.csv` and `<curve-name>-eff.csv`.
        """
        )

        # Units for loaded curves
        st.markdown("### Loaded Curves Units")
        loaded_curves_units_cols = st.columns(4)

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
            loaded_curves_head_units = st.selectbox(
                "Head",
                options=head_units,
                key="loaded_curves_head_units",
                index=0,
            )
        with loaded_curves_units_cols[3]:
            loaded_curves_power_units = st.selectbox(
                "Power",
                options=power_units,
                key="loaded_curves_power_units",
                index=0,
            )

        st.markdown("---")

        for case in ["A", "B", "C", "D"]:
            st.markdown(f"#### Case {case}")
            col1, col2 = st.columns(2)

            with col1:
                uploaded_file_1 = st.file_uploader(
                    f"Performance Curves File 1 - Case {case}",
                    type=["csv"],
                    key=f"uploaded_curves_file_1_case_{case}",
                )

            with col2:
                uploaded_file_2 = st.file_uploader(
                    f"Performance Curves File 2 - Case {case}",
                    type=["csv"],
                    key=f"uploaded_curves_file_2_case_{case}",
                )

            # Store uploaded files in session state
            if uploaded_file_1 is not None:
                st.session_state[f"curves_file_1_case_{case}"] = {
                    "name": uploaded_file_1.name,
                    "content": uploaded_file_1.getvalue(),
                }

            if uploaded_file_2 is not None:
                st.session_state[f"curves_file_2_case_{case}"] = {
                    "name": uploaded_file_2.name,
                    "content": uploaded_file_2.getvalue(),
                }

            # Load impeller button
            if st.button(
                f"Load Curves for Case {case}",
                key=f"load_curves_case_{case}",
                type="secondary",
            ):
                try:
                    has_files = bool(
                        st.session_state.get(f"curves_file_1_case_{case}")
                        and st.session_state.get(f"curves_file_2_case_{case}")
                    )

                    if not has_files:
                        st.error(f"Please upload both curve files for Case {case}")
                        continue

                    # Create temporary directory for files
                    def extract_curve_name(filename):
                        name = filename.rsplit(".", 1)[0]
                        suffixes = ["head", "eff", "power", "power_shaft"]
                        for suffix in suffixes:
                            if name.endswith(f"-{suffix}"):
                                return name[: -len(f"-{suffix}")]
                        return name

                    temp_dir = tempfile.mkdtemp()
                    temp_path = Path(temp_dir)

                    filenames = [
                        st.session_state[f"curves_file_1_case_{case}"]["name"],
                        st.session_state[f"curves_file_2_case_{case}"]["name"],
                    ]
                    curve_name = extract_curve_name(filenames[0])

                    # Save CSV files to temporary directory
                    for csv_file in [
                        st.session_state[f"curves_file_1_case_{case}"],
                        st.session_state[f"curves_file_2_case_{case}"],
                    ]:
                        file_path = temp_path / csv_file["name"]
                        with open(file_path, "wb") as f:
                            f.write(csv_file["content"])

                    # Get gas composition
                    gas_name = st.session_state.get(f"gas_case_{case}")
                    if "gas_compositions_table" in st.session_state:
                        gas_composition = get_gas_composition(
                            gas_name,
                            st.session_state["gas_compositions_table"],
                            default_components,
                        )
                    else:
                        st.error("Please submit gas compositions first")
                        shutil.rmtree(temp_dir)
                        continue

                    if not gas_composition:
                        st.error(
                            f"No gas composition found for {gas_name}. Please define molar fractions."
                        )
                        shutil.rmtree(temp_dir)
                        continue

                    # Get suction conditions
                    suc_p = st.session_state.get(f"suc_p_case_{case}", 0)
                    suc_T = st.session_state.get(f"suc_T_case_{case}", 0)

                    if suc_p <= 0 or suc_T <= 0:
                        st.error(
                            f"Please define valid suction conditions for Case {case}"
                        )
                        shutil.rmtree(temp_dir)
                        continue

                    # Create suction state
                    suc_state = ccp.State(
                        p=Q_(suc_p, design_suc_p_unit),
                        T=Q_(suc_T, design_suc_T_unit),
                        fluid=gas_composition,
                    )

                    # Load impeller
                    progress_bar = st.progress(0, text="Loading curves...")

                    impeller = ccp.Impeller.load_from_engauge_csv(
                        suc=suc_state,
                        curve_name=curve_name,
                        curve_path=temp_path,
                        flow_units=loaded_curves_flow_units,
                        head_units=loaded_curves_head_units,
                        power_units=loaded_curves_power_units,
                        speed_units=loaded_curves_speed_units,
                    )

                    progress_bar.progress(100, text="Curves loaded!")
                    time.sleep(0.5)
                    progress_bar.empty()

                    st.session_state[f"impeller_case_{case}"] = impeller
                    st.session_state[f"curve_name_case_{case}"] = curve_name
                    shutil.rmtree(temp_dir)

                    st.success(
                        f"Case {case} curves loaded: {len(impeller.points)} points, {len(impeller.curves)} curves"
                    )

                except Exception as e:
                    st.error(f"Error loading Case {case}: {str(e)}")
                    logging.error(f"Error loading Case {case}: {e}")
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass

            # Show loaded impeller info
            if st.session_state.get(f"impeller_case_{case}") is not None:
                imp = st.session_state[f"impeller_case_{case}"]
                st.info(f"Loaded: {len(imp.points)} points, {len(imp.curves)} curves")

            st.markdown("---")

    # Tags Configuration Expander
    with st.expander("Tags Configuration", expanded=st.session_state.expander_state):
        st.markdown("### Process Parameter Tags")

        # Row 1: Suction Pressure + Suction Temperature
        row1 = st.columns([3, 1, 3, 1])
        with row1[0]:
            st.text_input("Suction Pressure Tag", key="suc_p_tag")
        with row1[1]:
            st.selectbox("Unit", options=pressure_units, key="suc_p_unit")
        with row1[2]:
            st.text_input("Suction Temperature Tag", key="suc_T_tag")
        with row1[3]:
            st.selectbox("Unit", options=temperature_units, key="suc_T_unit")

        # Row 2: Discharge Pressure + Discharge Temperature
        row2 = st.columns([3, 1, 3, 1])
        with row2[0]:
            st.text_input("Discharge Pressure Tag", key="disch_p_tag")
        with row2[1]:
            st.selectbox("Unit", options=pressure_units, key="disch_p_unit")
        with row2[2]:
            st.text_input("Discharge Temperature Tag", key="disch_T_tag")
        with row2[3]:
            st.selectbox("Unit", options=temperature_units, key="disch_T_unit")

        # Row 3: Speed
        row3 = st.columns([3, 1, 3, 1])
        with row3[0]:
            st.text_input("Speed Tag", key="speed_tag")
        with row3[1]:
            st.selectbox("Unit", options=speed_units, key="speed_unit")

        # Row 4: Flow method selector + Flow tags
        if st.session_state.get("flow_method", "Direct") == "Direct":
            row4 = st.columns([2, 3, 1, 2])
            with row4[0]:
                flow_method = st.radio(
                    "Flow Measurement Method",
                    options=["Direct", "Orifice"],
                    key="flow_method",
                    horizontal=True,
                )
            with row4[1]:
                st.text_input("Flow Tag", key="flow_tag")
            with row4[2]:
                st.selectbox("Unit", options=flow_units, key="flow_unit")
        else:
            row4 = st.columns([2, 3, 1, 3, 1])
            with row4[0]:
                flow_method = st.radio(
                    "Flow Measurement Method",
                    options=["Direct", "Orifice"],
                    key="flow_method",
                    horizontal=True,
                )
            with row4[1]:
                st.text_input("Delta P Tag", key="delta_p_tag")
            with row4[2]:
                st.selectbox("Unit", options=pressure_units, key="delta_p_unit")
            with row4[3]:
                st.text_input("Downstream P Tag", key="p_downstream_tag")
            with row4[4]:
                st.selectbox("Unit", options=pressure_units, key="p_downstream_unit")

        # Orifice Parameters (if orifice method)
        if flow_method == "Orifice":
            orifice_row = st.columns([2, 3, 1, 3, 1])
            with orifice_row[0]:
                st.selectbox(
                    "Tappings",
                    options=["flange", "corner", "D D/2"],
                    key="orifice_tappings",
                )
            with orifice_row[1]:
                st.number_input(
                    "Pipe Diameter D",
                    key="orifice_D",
                    value=0.0,
                    format="%.6f",
                )
            with orifice_row[2]:
                st.selectbox("Unit", options=length_units, key="orifice_D_unit")
            with orifice_row[3]:
                st.number_input(
                    "Orifice Diameter d",
                    key="orifice_d",
                    value=0.0,
                    format="%.6f",
                )
            with orifice_row[4]:
                st.selectbox("Unit", options=length_units, key="orifice_d_unit")

        st.markdown("### Fluid Component")

        fluid_row_selector = st.columns([2, 6])
        with fluid_row_selector[0]:
            fluid_source = st.radio(
                "Fluid Source",
                options=["Fixed Operation Fluid", "Inform Component Tags"],
                key="fluid_source",
                label_visibility="collapsed",
            )
        with fluid_row_selector[1]:
            if fluid_source == "Fixed Operation Fluid":
                gas_options = [
                    st.session_state.get(f"gas_{i}", f"gas_{i}") for i in range(6)
                ]
                st.selectbox(
                    "Operation Fluid",
                    options=gas_options,
                    key="operation_fluid_gas",
                )

        if fluid_source == "Inform Component Tags":
            st.markdown("Configure tags for each component (mol %).")
            # Create 3 rows with 4 component+tag pairs per row (12 total)
            for row_idx in range(3):
                fluid_row = st.columns([1, 2, 1, 2, 1, 2, 1, 2])
                for col_idx in range(4):
                    comp_idx = row_idx * 4 + col_idx
                    with fluid_row[col_idx * 2]:
                        st.selectbox(
                            "Component",
                            options=fluid_list,
                            key=f"fluid_component_{comp_idx}",
                        )
                    with fluid_row[col_idx * 2 + 1]:
                        st.text_input("Tag", key=f"fluid_tag_{comp_idx}")

    # Online Monitoring Expander
    with st.expander("Online Monitoring", expanded=True):
        st.markdown("### Real-Time Performance Monitoring")

        # Get available cases (those with loaded impellers)
        available_cases = []
        for case in ["A", "B", "C", "D"]:
            if st.session_state.get(f"impeller_case_{case}") is not None:
                available_cases.append(case)

        if not available_cases:
            st.warning(
                "No design cases loaded. Please upload performance curves for at least one case."
            )
        else:
            # Case selector
            selected_case = st.selectbox(
                "Select Design Case",
                options=available_cases,
                key="monitoring_case",
            )

            # Monitoring controls
            control_cols = st.columns(3)
            with control_cols[0]:
                auto_refresh = st.checkbox("Auto-refresh", key="auto_refresh")
            with control_cols[1]:
                if auto_refresh:
                    refresh_interval = st.slider(
                        "Refresh interval (s)",
                        min_value=5,
                        max_value=60,
                        value=30,
                        key="refresh_interval",
                    )
            with control_cols[2]:
                fetch_button = st.button(
                    "Fetch Latest Data",
                    key="fetch_data",
                    type="primary",
                )

            # Build tag mappings
            tag_mappings = {
                "suc_p_tag": st.session_state.get("suc_p_tag", ""),
                "suc_T_tag": st.session_state.get("suc_T_tag", ""),
                "disch_p_tag": st.session_state.get("disch_p_tag", ""),
                "disch_T_tag": st.session_state.get("disch_T_tag", ""),
                "speed_tag": st.session_state.get("speed_tag", ""),
            }

            flow_method = st.session_state.get("flow_method", "Direct")
            if flow_method == "Direct":
                tag_mappings["flow_tag"] = st.session_state.get("flow_tag", "")
            else:
                tag_mappings["delta_p_tag"] = st.session_state.get("delta_p_tag", "")
                tag_mappings["p_downstream_tag"] = st.session_state.get(
                    "p_downstream_tag", ""
                )

            if fetch_button or (auto_refresh and "last_fetch" in st.session_state):
                try:
                    # Fetch data
                    df_raw = fetch_pi_data(tag_mappings, n_points=3)

                    # Get impeller for selected case
                    impeller = st.session_state[f"impeller_case_{selected_case}"]

                    # Get gas composition for the case
                    gas_name = st.session_state.get(f"gas_case_{selected_case}")
                    if "gas_compositions_table" in st.session_state:
                        operation_fluid = get_gas_composition(
                            gas_name,
                            st.session_state["gas_compositions_table"],
                            default_components,
                        )
                    else:
                        operation_fluid = None

                    # Build data units from per-tag unit selections
                    data_units = {
                        "ps": st.session_state.get("suc_p_unit", "bar"),
                        "Ts": st.session_state.get("suc_T_unit", "degC"),
                        "pd": st.session_state.get("disch_p_unit", "bar"),
                        "Td": st.session_state.get("disch_T_unit", "degC"),
                        "speed": st.session_state.get("speed_unit", "rpm"),
                    }

                    evaluation_kwargs = {
                        "data": df_raw,
                        "operation_fluid": operation_fluid,
                        "data_units": data_units,
                        "impellers": [impeller],
                        "n_clusters": 2,
                        "calculate_points": False,
                    }

                    if flow_method == "Direct":
                        data_units["flow_v"] = st.session_state.get("flow_unit", "m³/h")
                    else:
                        data_units["delta_p"] = st.session_state.get(
                            "delta_p_unit", "bar"
                        )
                        data_units["p_downstream"] = st.session_state.get(
                            "p_downstream_unit", "bar"
                        )
                        # Add orifice parameters
                        evaluation_kwargs["D"] = Q_(
                            st.session_state.get("orifice_D", 0.5905),
                            st.session_state.get("orifice_D_unit", "m"),
                        )
                        evaluation_kwargs["d"] = Q_(
                            st.session_state.get("orifice_d", 0.3661),
                            st.session_state.get("orifice_d_unit", "m"),
                        )
                        evaluation_kwargs["tappings"] = st.session_state.get(
                            "orifice_tappings", "flange"
                        )

                    # Create Evaluation
                    with st.spinner("Processing data..."):
                        evaluation = ccp.Evaluation(**evaluation_kwargs)

                        # Calculate points
                        df_results = evaluation.calculate_points(
                            df_raw, drop_invalid_values=False
                        )

                    st.session_state.evaluation = evaluation
                    st.session_state.monitoring_results = df_results
                    st.session_state.last_fetch = time.time()

                except Exception as e:
                    st.error(f"Error processing data: {str(e)}")
                    logging.error(f"Error in online monitoring: {e}")

            # Display results
            if st.session_state.get("monitoring_results") is not None:
                df_results = st.session_state.monitoring_results
                evaluation = st.session_state.evaluation

                # Get the latest valid point
                valid_results = df_results[df_results["valid"] == True]
                if len(valid_results) > 0:
                    latest = valid_results.iloc[-1]
                else:
                    latest = df_results.iloc[-1]

                # Get converted impeller for plotting
                cluster_idx = int(latest.cluster) if not pd.isna(latest.cluster) else 0
                converted_impeller = evaluation.impellers_new[cluster_idx]

                st.markdown("### Performance Curves with Current Point")

                # Plot curves units
                plot_flow_units = "m³/h"
                plot_head_units = "kJ/kg"
                plot_power_units = "kW"
                plot_p_units = "bar"

                # Create plots
                plot_col1, plot_col2 = st.columns(2)

                with plot_col1:
                    # Head plot
                    try:
                        head_fig = converted_impeller.head_plot(
                            flow_v=Q_(latest.flow_v, "m³/s"),
                            speed=Q_(
                                latest.speed,
                                st.session_state.get("speed_unit", "rpm"),
                            ),
                            flow_v_units=plot_flow_units,
                            head_units=plot_head_units,
                        )
                        st.plotly_chart(head_fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating head plot: {e}")

                    # Power plot
                    try:
                        power_fig = converted_impeller.power_plot(
                            flow_v=Q_(latest.flow_v, "m³/s"),
                            speed=Q_(
                                latest.speed,
                                st.session_state.get("speed_unit", "rpm"),
                            ),
                            flow_v_units=plot_flow_units,
                            power_units=plot_power_units,
                        )
                        st.plotly_chart(power_fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating power plot: {e}")

                with plot_col2:
                    # Efficiency plot
                    try:
                        eff_fig = converted_impeller.eff_plot(
                            flow_v=Q_(latest.flow_v, "m³/s"),
                            speed=Q_(
                                latest.speed,
                                st.session_state.get("speed_unit", "rpm"),
                            ),
                            flow_v_units=plot_flow_units,
                        )
                        st.plotly_chart(eff_fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating efficiency plot: {e}")

                    # Discharge Pressure plot
                    try:
                        disch_p_fig = converted_impeller.disch.p_plot(
                            flow_v=Q_(latest.flow_v, "m³/s"),
                            speed=Q_(
                                latest.speed,
                                st.session_state.get("speed_unit", "rpm"),
                            ),
                            flow_v_units=plot_flow_units,
                            p_units=plot_p_units,
                        )
                        st.plotly_chart(disch_p_fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error creating discharge pressure plot: {e}")

                # Current Point Info
                st.markdown("### Current Point Information")
                info_cols = st.columns(4)

                with info_cols[0]:
                    st.metric(
                        "Efficiency",
                        f"{latest.eff:.2f} %" if latest.eff > 0 else "N/A",
                        f"{latest.delta_eff:.2f} %" if latest.delta_eff != -1 else None,
                    )
                with info_cols[1]:
                    st.metric(
                        "Head",
                        f"{latest.head:.2f} kJ/kg" if latest.head > 0 else "N/A",
                        f"{latest.delta_head:.2f} %"
                        if latest.delta_head != -1
                        else None,
                    )
                with info_cols[2]:
                    st.metric(
                        "Power",
                        f"{latest.power:.2f} kW" if latest.power > 0 else "N/A",
                        f"{latest.delta_power:.2f} %"
                        if latest.delta_power != -1
                        else None,
                    )
                with info_cols[3]:
                    st.metric(
                        "Disch. Pressure",
                        f"{latest.p_disch:.2f} bar" if latest.p_disch > 0 else "N/A",
                        f"{latest.delta_p_disch:.2f} %"
                        if latest.delta_p_disch != -1
                        else None,
                    )

                # Historical Table
                st.markdown("### Recent Points History")
                display_cols = [
                    "eff",
                    "expected_eff",
                    "delta_eff",
                    "head",
                    "expected_head",
                    "delta_head",
                    "power",
                    "expected_power",
                    "delta_power",
                    "valid",
                ]
                available_cols = [c for c in display_cols if c in df_results.columns]
                st.dataframe(
                    df_results[available_cols].style.format(
                        {col: "{:.2f}" for col in available_cols if col != "valid"}
                    ),
                    use_container_width=True,
                )

            # Auto-refresh logic
            if auto_refresh and st.session_state.get("monitoring_results") is not None:
                time.sleep(refresh_interval)
                st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.info("app: online_monitoring")
        logging.info(f"session state: {st.session_state}")
        logging.error(e)
        raise e
