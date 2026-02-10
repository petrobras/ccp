import base64
import io
import json
import logging
import random
import shutil
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import sentry_sdk
import streamlit as st
import toml

import ccp
from ccp.app.common import (
    display_debug_data,
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

# Parse command line arguments for testing mode
# Usage: streamlit run app.py -- testing=True
TESTING_MODE = "testing=True" in sys.argv

# pandaspi is only available inside Petrobras network.
# Guard the import so the rest of the app still works without it.
try:
    from pandaspi import SessionWeb

    HAS_PANDASPI = True
except ImportError:
    HAS_PANDASPI = False

sentry_sdk.init(
    dsn="https://8fd0e79dffa94dbb9747bf64e7e55047@o348313.ingest.sentry.io/4505046640623616",
    traces_sample_rate=1.0,
    auto_enabling_integrations=False,
)


def _build_pi_query(tag_mappings):
    """Build PI tag list and column rename map from tag_mappings.

    Parameters
    ----------
    tag_mappings : dict
        Dictionary with tag configuration from session state.

    Returns
    -------
    tags_list : list of str
        PI tag name strings to query.
    rename_map : dict
        Mapping from PI tag name to ccp internal column name.
    """
    # Map from tag_mappings key -> ccp internal column name
    key_to_col = {
        "suc_p_tag": "ps",
        "suc_T_tag": "Ts",
        "disch_p_tag": "pd",
        "disch_T_tag": "Td",
        "speed_tag": "speed",
        "flow_tag": "flow_v",
        "delta_p_tag": "delta_p",
        "p_downstream_tag": "p_downstream",
    }

    tags_list = []
    rename_map = {}

    for key, col_name in key_to_col.items():
        tag_name = tag_mappings.get(key, "")
        if tag_name:
            tags_list.append(tag_name)
            rename_map[tag_name] = col_name

    # Add fluid component tags if configured
    fluid_tags = tag_mappings.get("fluid_tags", {})
    for component_name, tag_name in fluid_tags.items():
        if tag_name:
            tags_list.append(tag_name)
            rename_map[tag_name] = f"fluid_{component_name}"

    return tags_list, rename_map


def _format_pi_time(dt):
    """Format a datetime object as a PI time string.

    Parameters
    ----------
    dt : datetime
        Datetime to format.

    Returns
    -------
    str
        Formatted time string in 'dd/mm/YYYY HH:MM:SS' format.
    """
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _apply_fluid_unit_conversions(df, tag_mappings):
    """Convert fluid component columns based on their configured units.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with fluid columns already renamed to ``fluid_*``.
    tag_mappings : dict
        Must contain ``fluid_units`` mapping component names to unit strings.

    Returns
    -------
    pd.DataFrame
        DataFrame with fluid columns converted where necessary.
        Columns in ``percent`` are divided by 100; ``mol_frac`` and ``ppm``
        are left as-is (``ppm`` is handled by ``ccp.Evaluation`` internally).
    """
    fluid_units = tag_mappings.get("fluid_units", {})
    for component_name, unit in fluid_units.items():
        col = f"fluid_{component_name}"
        if col in df.columns and unit == "percent":
            df[col] = df[col] / 100.0
    return df


def _sanitize_pi_dataframe(df):
    """Clean a raw PI DataFrame for use with ccp.Evaluation.

    PI Web API may return dict objects for digital/enumerated tags or when
    instrument errors occur (e.g. ``{'Name': 'Configure', 'Value': 240,
    'IsSystem': True}``).  These are detected, and the rows where *any*
    column contains a PI system/error dict are dropped so that downstream
    calculations only see valid numeric data.

    Additionally:

    - Strip timezone from the index.
    - Coerce all columns to numeric (non-numeric become NaN).

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from pandaspi ``SessionWeb`` (already column-renamed).

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with float64 columns and tz-naive DatetimeIndex.

    Raises
    ------
    ValueError
        If *all* rows in a column are PI error dicts (instrument is down).
    """
    # Detect columns that contain PI error/system dicts
    error_columns = {}
    for col in df.columns:
        if df[col].dtype == object:
            is_dict_mask = df[col].apply(lambda v: isinstance(v, dict))
            if is_dict_mask.any():
                n_dicts = is_dict_mask.sum()
                # Grab a sample dict for the error message
                sample = df[col][is_dict_mask].iloc[0]
                error_columns[col] = {
                    "count": n_dicts,
                    "total": len(df),
                    "sample": sample,
                }
                if n_dicts == len(df):
                    raise ValueError(
                        f"Tag mapped to column '{col}' returned only PI system "
                        f"values (instrument error). Sample value: {sample}. "
                        f"Please check if the instrument is operational."
                    )

    if error_columns:
        # Log which columns had errors
        for col, info in error_columns.items():
            print(
                f"[WARNING] Column '{col}': {info['count']}/{info['total']} rows "
                f"contain PI system/error values (e.g. {info['sample']}). "
                f"These rows will be dropped."
            )
        # Build a mask of rows where ANY column has a dict value
        dict_row_mask = pd.Series(False, index=df.index)
        for col in error_columns:
            dict_row_mask |= df[col].apply(lambda v: isinstance(v, dict))
        df = df[~dict_row_mask].copy()

    # Strip timezone (ccp.Evaluation expects tz-naive index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # Coerce all columns to numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_pi_data(tag_mappings, start_time=None, testing=False):
    """Fetch historical PI data from start_time to now.

    Parameters
    ----------
    tag_mappings : dict
        Dictionary with tag mappings (used to determine which file to load).
    start_time : datetime, optional
        Start time from which to fetch data. If None, returns all data.
    testing : bool, optional
        If True, returns complete test dataframe from parquet files.

    Returns
    -------
    pd.DataFrame
        DataFrame with data from start_time to now.
    """
    if testing:
        # Load test data from parquet files
        data_path = Path(ccp.__file__).parent / "tests/data"

        if tag_mappings.get("delta_p_tag"):
            df = pd.read_parquet(data_path / "data_delta_p.parquet")
        else:
            df = pd.read_parquet(data_path / "data.parquet")

        return df
    else:
        tags_list, rename_map = _build_pi_query(tag_mappings)
        if not tags_list:
            raise ValueError("No PI tags configured. Please fill in the tag names.")

        end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        print(f"[fetch_pi_data] tags={tags_list}, time_range=({_format_pi_time(start_time)}, {_format_pi_time(end_time)})")
        session = SessionWeb(
            server_name=tag_mappings.get("pi_server_name", ""),
            login=tag_mappings.get("pi_login"),
            tags=tags_list,
            time_range=(_format_pi_time(start_time), _format_pi_time(end_time)),
            time_span="450s",
            authentication=tag_mappings.get("pi_auth_method", "kerberos"),
        )

        print(f"[fetch_pi_data] raw PI DataFrame:\n{session.df}")
        print(f"[fetch_pi_data] raw dtypes:\n{session.df.dtypes}")
        df = session.df.rename(columns=rename_map)
        df = _sanitize_pi_dataframe(df)
        print(f"[fetch_pi_data] sanitized DataFrame:\n{df}")
        print(f"[fetch_pi_data] sanitized dtypes:\n{df.dtypes}")
        df = _apply_fluid_unit_conversions(df, tag_mappings)
        return df


def fetch_pi_data_online(tag_mappings, testing=False):
    """Fetch latest 3 points from PI server for online monitoring.

    Parameters
    ----------
    tag_mappings : dict
        Dictionary with tag mappings (used to determine which file to load).
    testing : bool, optional
        If True, returns 3 adjacent points from a random position in test data,
        with timestamps adjusted to simulate real-time data.

    Returns
    -------
    pd.DataFrame
        DataFrame with 3 latest data points.
    """
    if testing:
        # Load test data from parquet files
        data_path = Path(ccp.__file__).parent / "tests/data"

        if tag_mappings.get("delta_p_tag"):
            df = pd.read_parquet(data_path / "data_delta_p.parquet")
        else:
            df = pd.read_parquet(data_path / "data.parquet")

        # Filter for valid data (speed > 9000)
        df = df[df["speed"] > 9000].reset_index(drop=True)

        # Select random position and return 3 adjacent points
        max_start_idx = len(df) - 3
        if max_start_idx <= 0:
            df_sample = df.copy()
        else:
            start_idx = random.randint(0, max_start_idx)
            df_sample = df.iloc[start_idx : start_idx + 3].copy()

        # Adjust timestamps to simulate real-time data
        # Last point: current time
        # Middle point: current time - 7 min 30 sec
        # First point: current time - 15 min
        now = datetime.now()
        new_timestamps = [
            now - timedelta(minutes=15),
            now - timedelta(minutes=7, seconds=30),
            now,
        ]
        df_sample.index = pd.DatetimeIndex(new_timestamps[: len(df_sample)])

        return df_sample
    else:
        tags_list, rename_map = _build_pi_query(tag_mappings)
        if not tags_list:
            raise ValueError("No PI tags configured. Please fill in the tag names.")

        now = datetime.now()
        start_time = now - timedelta(minutes=15)

        print(f"[fetch_pi_data_online] tags={tags_list}, time_range=({_format_pi_time(start_time)}, {_format_pi_time(now)})")
        session = SessionWeb(
            server_name=tag_mappings.get("pi_server_name", ""),
            login=tag_mappings.get("pi_login"),
            tags=tags_list,
            time_range=(_format_pi_time(start_time), _format_pi_time(now)),
            time_span="450s",
            authentication=tag_mappings.get("pi_auth_method", "kerberos"),
        )

        print(f"[fetch_pi_data_online] raw PI DataFrame:\n{session.df}")
        print(f"[fetch_pi_data_online] raw dtypes:\n{session.df.dtypes}")
        df = session.df.rename(columns=rename_map)
        df = _sanitize_pi_dataframe(df)
        print(f"[fetch_pi_data_online] sanitized DataFrame:\n{df}")
        print(f"[fetch_pi_data_online] sanitized dtypes:\n{df.dtypes}")
        df = _apply_fluid_unit_conversions(df, tag_mappings)
        return df


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

    # Check pandaspi availability — required for real PI data
    if not HAS_PANDASPI and not TESTING_MODE:
        st.error(
            "**pandaspi** is required for online monitoring with real PI data. "
            "This library is only available inside Petrobras. "
            "To run with mock data for testing, start with: "
            "`streamlit run ccp/app/ccp_app.py -- testing=True`"
        )
        st.stop()

    # Show testing mode alert at top of page
    if TESTING_MODE:
        st.warning(
            "**Testing Mode**: Running with mock data from test files. "
            "To run with real PI data, start without the `testing=True` argument."
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

        # Initialize PI server name
        if "pi_server_name" not in st.session_state:
            st.session_state.pi_server_name = ""

        # Initialize evaluation
        if "evaluation" not in st.session_state:
            st.session_state.evaluation = None

        # Initialize monitoring results
        if "monitoring_results" not in st.session_state:
            st.session_state.monitoring_results = None

    get_session()

    def load_ccp_file(file_path):
        """Load a .ccp session file and update session state.

        Parameters
        ----------
        file_path : Path
            Path to the .ccp file to load.

        Returns
        -------
        bool
            True if file was loaded successfully, False otherwise.
        """
        try:
            with zipfile.ZipFile(file_path) as my_zip:
                # get the ccp version
                try:
                    version = my_zip.read("ccp.version").decode("utf-8")
                except KeyError:
                    version = "0.3.5"

                session_state_data = {}
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
                            "start_monitoring",
                            "stop_monitoring",
                        )
                    ):
                        del session_state_data_copy[key]
                st.session_state.update(session_state_data_copy)
                st.session_state.session_name = file_path.stem
                st.session_state.expander_state = True
                return True
        except Exception as e:
            logging.error(f"Error loading .ccp file: {e}")
            return False

    # Auto-load example file in testing mode
    if TESTING_MODE and "test_file_loaded" not in st.session_state:
        example_file = Path(__file__).parent.parent / "example_online.ccp"
        if example_file.exists():
            if load_ccp_file(example_file):
                st.session_state.test_file_loaded = True
                st.rerun()
        else:
            st.warning(f"Testing mode: example file not found at {example_file}")
            st.session_state.test_file_loaded = True  # Prevent repeated warnings

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
                        (
                            bytes,
                            st.runtime.uploaded_file_manager.UploadedFile,
                            datetime,
                            timedelta,
                        ),
                    ) or type(value).__name__ in ("date", "time"):
                        keys_to_remove.append(key)
                    # Also catch dicts containing bytes (like curves_file entries)
                    elif isinstance(value, dict) and any(
                        isinstance(v, bytes) for v in value.values()
                    ):
                        keys_to_remove.append(key)

                # Also remove evaluation and monitoring_results as they can't be serialized
                # Remove pi_password so credentials are never persisted to disk
                for key in [
                    "evaluation",
                    "monitoring_results",
                    "last_fetch",
                    "pi_password",
                ]:
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
        st.markdown("### PI Server")
        server_row = st.columns([3, 2, 2, 2])
        with server_row[0]:
            st.text_input("PI Server Name", key="pi_server_name")
        with server_row[1]:
            st.radio(
                "Authentication",
                options=["kerberos", "basic"],
                key="pi_auth_method",
                horizontal=True,
            )
        if st.session_state.get("pi_auth_method") == "basic":
            with server_row[2]:
                st.text_input("Username", key="pi_username")
            with server_row[3]:
                st.text_input("Password", key="pi_password", type="password")

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
            st.markdown("Configure tags for each component.")
            fluid_unit_options = ["mol_frac", "percent", "ppm"]
            # Create 3 rows with 3 component+tag+unit groups per row (9 total)
            for row_idx in range(3):
                fluid_row = st.columns([1, 2, 1] * 3)
                for col_idx in range(3):
                    comp_idx = row_idx * 3 + col_idx
                    base = col_idx * 3
                    with fluid_row[base]:
                        st.selectbox(
                            "Component",
                            options=fluid_list,
                            key=f"fluid_component_{comp_idx}",
                        )
                    with fluid_row[base + 1]:
                        st.text_input("Tag", key=f"fluid_tag_{comp_idx}")
                    with fluid_row[base + 2]:
                        st.selectbox(
                            "Unit",
                            options=fluid_unit_options,
                            key=f"fluid_unit_{comp_idx}",
                        )

    # Online Monitoring Expander
    with st.expander("Online Monitoring", expanded=True):
        st.markdown("### Real-Time Performance Monitoring")

        # Get available cases (those with loaded impellers)
        available_cases = []
        impellers_list = []
        for case in ["A", "B", "C", "D"]:
            if st.session_state.get(f"impeller_case_{case}") is not None:
                available_cases.append(case)
                impellers_list.append(st.session_state[f"impeller_case_{case}"])

        if not available_cases:
            st.warning(
                "No design cases loaded. Please upload performance curves for at least one case."
            )
        else:
            # Initialize monitoring state
            if "monitoring_active" not in st.session_state:
                st.session_state.monitoring_active = False
            if "accumulated_results" not in st.session_state:
                st.session_state.accumulated_results = None

            # First row: Start date, Start time, Start/Stop Monitoring button
            control_row1 = st.columns([1, 1, 1, 1])
            with control_row1[0]:
                default_start = datetime.now() - timedelta(hours=1)
                start_date = st.date_input(
                    "Start Date",
                    value=default_start.date(),
                    key="start_date",
                    disabled=st.session_state.monitoring_active,
                )
            with control_row1[1]:
                start_time_input = st.time_input(
                    "Start Time",
                    value=default_start.time(),
                    key="start_time",
                    disabled=st.session_state.monitoring_active,
                )
            with control_row1[2]:
                refresh_interval = st.slider(
                    "Refresh interval (s)",
                    min_value=5,
                    max_value=60,
                    value=30,
                    key="refresh_interval",
                    disabled=st.session_state.monitoring_active,
                )
            with control_row1[3]:
                if not st.session_state.monitoring_active:
                    start_button = st.button(
                        "Start Monitoring",
                        key="start_monitoring",
                        type="primary",
                    )
                else:
                    stop_button = st.button(
                        "Stop Monitoring",
                        key="stop_monitoring",
                        type="secondary",
                    )

            # Data quality thresholds (collapsible)
            with st.expander("Data Quality Thresholds", expanded=False):
                st.caption(
                    "Points are marked as invalid if fluctuation exceeds these thresholds. "
                    "Fluctuation = (max - min) / mean × 100%"
                )
                threshold_cols = st.columns(3)
                with threshold_cols[0]:
                    temperature_fluctuation = st.number_input(
                        "Temperature (%)",
                        min_value=0.1,
                        max_value=10.0,
                        value=0.5,
                        step=0.1,
                        key="temperature_fluctuation",
                        disabled=st.session_state.monitoring_active,
                    )
                with threshold_cols[1]:
                    pressure_fluctuation = st.number_input(
                        "Pressure (%)",
                        min_value=0.1,
                        max_value=10.0,
                        value=2.0,
                        step=0.1,
                        key="pressure_fluctuation",
                        disabled=st.session_state.monitoring_active,
                    )
                with threshold_cols[2]:
                    speed_fluctuation = st.number_input(
                        "Speed (%)",
                        min_value=0.1,
                        max_value=10.0,
                        value=0.5,
                        step=0.1,
                        key="speed_fluctuation",
                        disabled=st.session_state.monitoring_active,
                    )

            # Build tag mappings
            tag_mappings = {
                "pi_server_name": st.session_state.get("pi_server_name", ""),
                "pi_auth_method": st.session_state.get(
                    "pi_auth_method", "kerberos"
                ),
                "suc_p_tag": st.session_state.get("suc_p_tag", ""),
                "suc_T_tag": st.session_state.get("suc_T_tag", ""),
                "disch_p_tag": st.session_state.get("disch_p_tag", ""),
                "disch_T_tag": st.session_state.get("disch_T_tag", ""),
                "speed_tag": st.session_state.get("speed_tag", ""),
            }

            # Add login credentials for basic auth
            if tag_mappings["pi_auth_method"] == "basic":
                username = st.session_state.get("pi_username", "")
                password = st.session_state.get("pi_password", "")
                tag_mappings["pi_login"] = (username, password)
            else:
                tag_mappings["pi_login"] = None

            flow_method = st.session_state.get("flow_method", "Direct")
            if flow_method == "Direct":
                tag_mappings["flow_tag"] = st.session_state.get("flow_tag", "")
            else:
                tag_mappings["delta_p_tag"] = st.session_state.get("delta_p_tag", "")
                tag_mappings["p_downstream_tag"] = st.session_state.get(
                    "p_downstream_tag", ""
                )

            # Build fluid component tag mappings and units
            fluid_source = st.session_state.get(
                "fluid_source", "Fixed Operation Fluid"
            )
            if fluid_source == "Inform Component Tags":
                fluid_tags = {}
                fluid_units = {}
                for i in range(9):
                    comp = st.session_state.get(f"fluid_component_{i}", "")
                    tag = st.session_state.get(f"fluid_tag_{i}", "")
                    unit = st.session_state.get(f"fluid_unit_{i}", "mol_frac")
                    if comp and tag:
                        fluid_tags[comp] = tag
                        fluid_units[comp] = unit
                tag_mappings["fluid_tags"] = fluid_tags
                tag_mappings["fluid_units"] = fluid_units

            # Handle Start Monitoring button
            if (
                not st.session_state.monitoring_active
                and "start_monitoring" in st.session_state
                and st.session_state.start_monitoring
            ):
                try:
                    # Combine date and time inputs into a datetime
                    start_datetime = datetime.combine(start_date, start_time_input)

                    # Fetch initial historical data
                    df_raw = fetch_pi_data(
                        tag_mappings, start_time=start_datetime, testing=TESTING_MODE
                    )

                    # Get gas composition (only for fixed fluid mode)
                    operation_fluid = None
                    if fluid_source != "Inform Component Tags":
                        gas_name = st.session_state.get(
                            f"gas_case_{available_cases[0]}"
                        )
                        if "gas_compositions_table" in st.session_state:
                            operation_fluid = get_gas_composition(
                                gas_name,
                                st.session_state["gas_compositions_table"],
                                default_components,
                            )

                    # Build data units from per-tag unit selections
                    data_units = {
                        "ps": st.session_state.get("suc_p_unit", "bar"),
                        "Ts": st.session_state.get("suc_T_unit", "degC"),
                        "pd": st.session_state.get("disch_p_unit", "bar"),
                        "Td": st.session_state.get("disch_T_unit", "degC"),
                        "speed": st.session_state.get("speed_unit", "rpm"),
                    }

                    # Add fluid component units to data_units
                    # (percent columns are already converted to mol_frac
                    #  by _apply_fluid_unit_conversions; ppm is handled by
                    #  ccp.Evaluation internally)
                    fluid_units_map = tag_mappings.get("fluid_units", {})
                    for comp_name, unit in fluid_units_map.items():
                        col = f"fluid_{comp_name}"
                        if unit == "ppm":
                            data_units[col] = "ppm"

                    evaluation_kwargs = {
                        "data": df_raw,
                        "operation_fluid": operation_fluid,
                        "data_units": data_units,
                        "impellers": impellers_list,
                        "n_clusters": len(impellers_list),
                        "calculate_points": False,
                        "parallel": not TESTING_MODE,  # Sequential for debugging
                        "temperature_fluctuation": st.session_state.get(
                            "temperature_fluctuation", 0.5
                        ),
                        "pressure_fluctuation": st.session_state.get(
                            "pressure_fluctuation", 2.0
                        ),
                        "speed_fluctuation": st.session_state.get(
                            "speed_fluctuation", 0.5
                        ),
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

                    # Create Evaluation with all impellers
                    with st.spinner("Initializing monitoring..."):
                        # Debug: show Evaluation kwargs
                        if TESTING_MODE:
                            display_debug_data(
                                "ccp.Evaluation kwargs",
                                evaluation_kwargs,
                                expanded=True,
                            )

                        evaluation = ccp.Evaluation(**evaluation_kwargs)

                        # Debug: show calculate_points input data
                        if TESTING_MODE:
                            display_debug_data(
                                "evaluation.calculate_points() input",
                                {"data": df_raw.tail(5), "drop_invalid_values": False},
                                expanded=True,
                            )

                        # Calculate initial points for last 5 points
                        df_results = evaluation.calculate_points(
                            df_raw.tail(5),
                            drop_invalid_values=False,
                            parallel=not TESTING_MODE,
                        )

                        # Debug: show calculate_points results
                        if TESTING_MODE:
                            display_debug_data(
                                "evaluation.calculate_points() results",
                                df_results,
                                expanded=True,
                            )
                            # Show calculation errors if any
                            errors = df_results[df_results["error"].notna()]
                            if not errors.empty:
                                display_debug_data(
                                    "Calculation Errors",
                                    errors[
                                        [
                                            "error",
                                            "error_type",
                                            "expected_error",
                                            "expected_error_type",
                                        ]
                                    ],
                                    expanded=True,
                                )

                    st.session_state.evaluation = evaluation
                    # Filter for successfully calculated points (head > 0)
                    valid_calculated = df_results[df_results["head"] > 0]
                    if valid_calculated.empty:
                        st.warning(
                            "No points could be calculated. Check data quality thresholds."
                        )
                    else:
                        st.session_state.monitoring_results = valid_calculated
                        st.session_state.accumulated_results = valid_calculated.tail(5)
                        st.session_state.monitoring_active = True
                        st.session_state.last_fetch = time.time()
                        st.rerun()

                except Exception as e:
                    import traceback

                    error_trace = traceback.format_exc()
                    st.error(f"Error starting monitoring: {str(e)}")
                    logging.error(f"Error in online monitoring: {e}")
                    if TESTING_MODE:
                        st.code(error_trace, language="python")

            # Handle Stop Monitoring button
            if (
                st.session_state.monitoring_active
                and "stop_monitoring" in st.session_state
                and st.session_state.stop_monitoring
            ):
                st.session_state.monitoring_active = False
                st.rerun()

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

                # Get expected point values from latest results
                # Convert flow_v from data units to plot units
                flow_v_data_units = st.session_state.get("flow_unit", "m³/h")
                expected_flow = (
                    Q_(latest.flow_v, flow_v_data_units).to(plot_flow_units).m
                )
                # Convert head from J/kg to kJ/kg using pint
                expected_head = Q_(latest.expected_head, "J/kg").to(plot_head_units).m
                # Efficiency is dimensionless
                expected_eff = latest.expected_eff
                # Convert power from W to kW using pint
                expected_power = Q_(latest.expected_power, "W").to(plot_power_units).m
                # Convert discharge pressure to plot units using pint
                expected_p_disch = Q_(latest.expected_p_disch, "bar").to(plot_p_units).m
                # Get speed with units for plotting the current speed curve
                speed_data_units = st.session_state.get("speed_unit", "rpm")
                current_speed = Q_(latest.speed, speed_data_units)

                # Get last 5 operational points for plotting with varying opacity
                df_history = st.session_state.get(
                    "accumulated_results", df_results
                ).tail(5)
                n_points = len(df_history)

                # Prepare operational points data with opacity (older = more transparent)
                op_points = []
                for i, (idx, row) in enumerate(df_history.iterrows()):
                    # Opacity from 0.3 (oldest) to 1.0 (newest)
                    opacity = 0.3 + (0.7 * i / max(n_points - 1, 1))
                    op_flow = Q_(row["flow_v"], flow_v_data_units).to(plot_flow_units).m
                    op_head = (
                        Q_(row["head"], "J/kg").to(plot_head_units).m
                        if row["head"] > 0
                        else None
                    )
                    op_eff = row["eff"] if row["eff"] > 0 else None
                    op_power = (
                        Q_(row["power"], "W").to(plot_power_units).m
                        if row["power"] > 0
                        else None
                    )
                    op_p_disch = (
                        Q_(row["p_disch"], "bar").to(plot_p_units).m
                        if row["p_disch"] > 0
                        else None
                    )
                    op_points.append(
                        {
                            "flow": op_flow,
                            "head": op_head,
                            "eff": op_eff,
                            "power": op_power,
                            "p_disch": op_p_disch,
                            "opacity": opacity,
                            "is_latest": i == n_points - 1,
                        }
                    )

                # Create plots
                plot_col1, plot_col2 = st.columns(2)

                with plot_col1:
                    # Head plot
                    try:
                        head_fig = converted_impeller.head_plot(
                            speed=current_speed,
                            flow_v_units=plot_flow_units,
                            head_units=plot_head_units,
                        )
                        # Add expected point
                        if expected_head > 0:
                            head_fig.add_trace(
                                go.Scatter(
                                    x=[expected_flow],
                                    y=[expected_head],
                                    mode="markers",
                                    marker=dict(
                                        color="green", size=10, symbol="diamond"
                                    ),
                                    name="Expected Point",
                                    showlegend=True,
                                )
                            )
                        # Add operational points with varying opacity
                        for op in op_points:
                            if op["head"] is not None:
                                head_fig.add_trace(
                                    go.Scatter(
                                        x=[op["flow"]],
                                        y=[op["head"]],
                                        mode="markers",
                                        marker=dict(
                                            color="black", size=8, symbol="circle"
                                        ),
                                        opacity=op["opacity"],
                                        name="Operational Point"
                                        if op["is_latest"]
                                        else None,
                                        showlegend=op["is_latest"],
                                    )
                                )
                        st.plotly_chart(head_fig, width="stretch")
                    except Exception as e:
                        st.error(f"Error creating head plot: {e}")

                    # Power plot
                    try:
                        power_fig = converted_impeller.power_plot(
                            speed=current_speed,
                            flow_v_units=plot_flow_units,
                            power_units=plot_power_units,
                        )
                        # Add expected point
                        if expected_power > 0:
                            power_fig.add_trace(
                                go.Scatter(
                                    x=[expected_flow],
                                    y=[expected_power],
                                    mode="markers",
                                    marker=dict(
                                        color="green", size=10, symbol="diamond"
                                    ),
                                    name="Expected Point",
                                    showlegend=True,
                                )
                            )
                        # Add operational points with varying opacity
                        for op in op_points:
                            if op["power"] is not None:
                                power_fig.add_trace(
                                    go.Scatter(
                                        x=[op["flow"]],
                                        y=[op["power"]],
                                        mode="markers",
                                        marker=dict(
                                            color="black", size=8, symbol="circle"
                                        ),
                                        opacity=op["opacity"],
                                        name="Operational Point"
                                        if op["is_latest"]
                                        else None,
                                        showlegend=op["is_latest"],
                                    )
                                )
                        st.plotly_chart(power_fig, width="stretch")
                    except Exception as e:
                        st.error(f"Error creating power plot: {e}")

                with plot_col2:
                    # Efficiency plot
                    try:
                        eff_fig = converted_impeller.eff_plot(
                            speed=current_speed,
                            flow_v_units=plot_flow_units,
                        )
                        # Add expected point
                        if expected_eff > 0:
                            eff_fig.add_trace(
                                go.Scatter(
                                    x=[expected_flow],
                                    y=[expected_eff],
                                    mode="markers",
                                    marker=dict(
                                        color="green", size=10, symbol="diamond"
                                    ),
                                    name="Expected Point",
                                    showlegend=True,
                                )
                            )
                        # Add operational points with varying opacity
                        for op in op_points:
                            if op["eff"] is not None:
                                eff_fig.add_trace(
                                    go.Scatter(
                                        x=[op["flow"]],
                                        y=[op["eff"]],
                                        mode="markers",
                                        marker=dict(
                                            color="black", size=8, symbol="circle"
                                        ),
                                        opacity=op["opacity"],
                                        name="Operational Point"
                                        if op["is_latest"]
                                        else None,
                                        showlegend=op["is_latest"],
                                    )
                                )
                        st.plotly_chart(eff_fig, width="stretch")
                    except Exception as e:
                        st.error(f"Error creating efficiency plot: {e}")

                    # Discharge Pressure plot
                    try:
                        disch_p_fig = converted_impeller.disch.p_plot(
                            speed=current_speed,
                            flow_v_units=plot_flow_units,
                            p_units=plot_p_units,
                        )
                        # Add expected point
                        if expected_p_disch > 0:
                            disch_p_fig.add_trace(
                                go.Scatter(
                                    x=[expected_flow],
                                    y=[expected_p_disch],
                                    mode="markers",
                                    marker=dict(
                                        color="green", size=10, symbol="diamond"
                                    ),
                                    name="Expected Point",
                                    showlegend=True,
                                )
                            )
                        # Add operational points with varying opacity
                        for op in op_points:
                            if op["p_disch"] is not None:
                                disch_p_fig.add_trace(
                                    go.Scatter(
                                        x=[op["flow"]],
                                        y=[op["p_disch"]],
                                        mode="markers",
                                        marker=dict(
                                            color="black", size=8, symbol="circle"
                                        ),
                                        opacity=op["opacity"],
                                        name="Operational Point"
                                        if op["is_latest"]
                                        else None,
                                        showlegend=op["is_latest"],
                                    )
                                )
                        st.plotly_chart(disch_p_fig, width="stretch")
                    except Exception as e:
                        st.error(f"Error creating discharge pressure plot: {e}")

                # Current Point Info
                st.markdown("### Current Point Information")
                info_cols = st.columns(4)

                # Convert values to display units using pint
                display_eff = latest.eff * 100 if latest.eff > 0 else None
                display_head = (
                    Q_(latest["head"], "J/kg").to("kJ/kg").m
                    if latest["head"] > 0
                    else None
                )
                display_power = (
                    Q_(latest.power, "W").to("kW").m if latest.power > 0 else None
                )
                display_p_disch = (
                    Q_(latest.p_disch, "bar").to("bar").m
                    if latest.p_disch > 0
                    else None
                )

                with info_cols[0]:
                    st.metric(
                        "Efficiency (%)",
                        f"{display_eff:.2f}" if display_eff else "N/A",
                        f"{latest.delta_eff:.2f} %" if latest.delta_eff != -1 else None,
                    )
                with info_cols[1]:
                    st.metric(
                        "Head (kJ/kg)",
                        f"{display_head:.2f}" if display_head else "N/A",
                        f"{latest['delta_head']:.2f} %"
                        if latest["delta_head"] != -1
                        else None,
                    )
                with info_cols[2]:
                    st.metric(
                        "Power (kW)",
                        f"{display_power:.2f}" if display_power else "N/A",
                        f"{latest.delta_power:.2f} %"
                        if latest.delta_power != -1
                        else None,
                    )
                with info_cols[3]:
                    st.metric(
                        "Disch. Pressure (bar)",
                        f"{display_p_disch:.2f}" if display_p_disch else "N/A",
                        f"{latest.delta_p_disch:.2f} %"
                        if latest.delta_p_disch != -1
                        else None,
                    )

                # Historical Table - show last 5 accumulated points
                st.markdown("### Recent Points History (Last 5)")
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

                # Use accumulated results if available
                df_display = st.session_state.get("accumulated_results", df_results)
                available_cols = [c for c in display_cols if c in df_display.columns]

                # Style function to apply row opacity (older rows more transparent)
                def style_rows_by_age(df):
                    n_rows = len(df)
                    styles = []
                    for i in range(n_rows):
                        # Opacity from 0.4 (oldest) to 1.0 (newest)
                        opacity = 0.4 + (0.6 * i / max(n_rows - 1, 1))
                        styles.append(f"opacity: {opacity}")
                    return styles

                styled_df = (
                    df_display[available_cols]
                    .style.format(
                        {col: "{:.2f}" for col in available_cols if col != "valid"}
                    )
                    .apply(lambda _: style_rows_by_age(df_display), axis=0)
                )

                st.dataframe(styled_df, width="stretch")

                # Display debug data from last fetch (testing mode)
                if (
                    TESTING_MODE
                    and st.session_state.get("debug_last_fetch_input") is not None
                ):
                    display_debug_data(
                        "Last fetch - calculate_points() input",
                        {"data": st.session_state.debug_last_fetch_input},
                    )
                    df_debug = st.session_state.debug_last_fetch_results
                    display_debug_data(
                        "Last fetch - calculate_points() results",
                        df_debug,
                    )
                    # Show invalid data explanation
                    invalid_count = (
                        (~df_debug["valid"]).sum() if "valid" in df_debug.columns else 0
                    )
                    if invalid_count > 0:
                        temp_thresh = st.session_state.get(
                            "temperature_fluctuation", 0.5
                        )
                        pres_thresh = st.session_state.get("pressure_fluctuation", 2.0)
                        speed_thresh = st.session_state.get("speed_fluctuation", 0.5)
                        st.info(
                            f"**{invalid_count} point(s) marked as invalid** (valid=False). "
                            f"Data exceeded fluctuation thresholds:\n"
                            f"- Temperature: {temp_thresh}%\n"
                            f"- Pressure: {pres_thresh}%\n"
                            f"- Speed: {speed_thresh}%\n\n"
                            "Points with valid=False are not calculated (shown as -1). "
                            "Adjust thresholds in 'Data Quality Thresholds' section."
                        )
                    # Display actual calculation errors if any
                    if st.session_state.get("debug_last_fetch_errors") is not None:
                        display_debug_data(
                            "Last fetch - Calculation Errors",
                            st.session_state.debug_last_fetch_errors,
                        )

            # Auto-refresh logic when monitoring is active
            if (
                st.session_state.monitoring_active
                and st.session_state.get("evaluation") is not None
            ):
                # Wait for refresh interval
                time.sleep(refresh_interval)

                # Fetch new 3 points after waiting
                try:
                    df_new = fetch_pi_data_online(tag_mappings, testing=TESTING_MODE)

                    # Calculate points for new data
                    evaluation = st.session_state.evaluation
                    df_new_results = evaluation.calculate_points(
                        df_new,
                        drop_invalid_values=False,
                        parallel=not TESTING_MODE,
                    )

                    # Store debug data for display after rerun
                    if TESTING_MODE:
                        st.session_state.debug_last_fetch_input = df_new
                        st.session_state.debug_last_fetch_results = df_new_results
                        # Store errors if any
                        errors = df_new_results[df_new_results["error"].notna()]
                        if not errors.empty:
                            st.session_state.debug_last_fetch_errors = errors[
                                [
                                    "error",
                                    "error_type",
                                    "expected_error",
                                    "expected_error_type",
                                ]
                            ]
                        else:
                            st.session_state.debug_last_fetch_errors = None

                    # Filter for successfully calculated points (head > 0)
                    valid_new = df_new_results[df_new_results["head"] > 0]

                    # Accumulate results (keep last 5, only successfully calculated points)
                    if st.session_state.accumulated_results is not None:
                        accumulated = pd.concat(
                            [st.session_state.accumulated_results, valid_new]
                        )
                        st.session_state.accumulated_results = accumulated.tail(5)
                    elif not valid_new.empty:
                        st.session_state.accumulated_results = valid_new.tail(5)

                    # Update monitoring_results only if there are valid points
                    if not valid_new.empty:
                        st.session_state.monitoring_results = valid_new
                    st.session_state.last_fetch = time.time()

                except Exception as e:
                    st.error(f"Error fetching data: {str(e)}")
                    logging.error(f"Error in online monitoring refresh: {e}")

                st.rerun()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.info("app: online_monitoring")
        logging.info(f"session state: {st.session_state}")
        logging.error(e)
        raise e
