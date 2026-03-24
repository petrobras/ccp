import io
import json
import logging
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import toml
from scipy import stats

import ccp
from ccp.app.common import (
    build_data_units,
    build_evaluation_kwargs,
    build_tag_mappings,
    curves_upload_section,
    design_cases_section,
    display_debug_data,
    fetch_pi_data,
    gas_selection_ui,
    get_available_impellers,
    init_sentry,
    run_app,
    setup_page,
    tags_config_section,
    to_excel,
)
from ccp.app.ai_analysis import generate_ai_analysis, get_provider
from ccp.app.report import generate_html_report

# Parse command line arguments for testing mode
# Usage: streamlit run app.py -- testing=True
TESTING_MODE = "testing=True" in sys.argv

# pandaspi is only available inside Petrobras network.
# Guard the import so the rest of the app still works without it.
try:
    import pandaspi  # noqa: F401

    HAS_PANDASPI = True
except ImportError:
    HAS_PANDASPI = False

init_sentry()


def main():
    """The code has to be inside this main function to allow sentry to work."""
    Q_ = ccp.Q_

    setup_page(page_title="ccp - Performance Evaluation")
    st.markdown(
        """
    ## Performance Evaluation
    """
    )

    # Check pandaspi availability — required for real PI data
    if not HAS_PANDASPI and not TESTING_MODE:
        st.error(
            "**pandaspi** is required for performance evaluation with real PI data. "
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

    def align_timestamp_to_reference(ts, reference_ts):
        """Align timestamp timezone to match a reference timestamp."""
        ts = pd.Timestamp(ts)
        reference_ts = pd.Timestamp(reference_ts)

        if reference_ts.tz is None and ts.tz is not None:
            return ts.tz_localize(None)
        if reference_ts.tz is not None and ts.tz is None:
            return ts.tz_localize(reference_ts.tz)
        if reference_ts.tz is not None and ts.tz is not None:
            return ts.tz_convert(reference_ts.tz)
        return ts

    def get_session():
        # Initialize session state variables
        if "session_name" not in st.session_state:
            st.session_state.session_name = ""
        if "expander_state" not in st.session_state:
            st.session_state.expander_state = True
        if "ccp_version" not in st.session_state:
            st.session_state.ccp_version = ccp.__version__
        if "app_type" not in st.session_state:
            st.session_state.app_type = "performance_evaluation"

        # Initialize impellers for each case
        for case in ["A", "B", "C", "D", "E"]:
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

        # Initialize historical evaluation
        if "hist_evaluation" not in st.session_state:
            st.session_state.hist_evaluation = None

        # Initialize AI analysis options
        if "ai_enabled" not in st.session_state:
            st.session_state.ai_enabled = False
        if "ai_provider" not in st.session_state:
            st.session_state.ai_provider = "gemini"
        if "ai_api_key" not in st.session_state:
            st.session_state.ai_api_key = ""
        if "ai_azure_endpoint" not in st.session_state:
            st.session_state.ai_azure_endpoint = ""
        if "ai_azure_deployment" not in st.session_state:
            st.session_state.ai_azure_deployment = ""

    get_session()

    def load_ccp_file(file_path_or_obj):
        """Load a .ccp session file and update session state.

        Parameters
        ----------
        file_path_or_obj : Path or file-like
            Path to the .ccp file or uploaded file object.

        Returns
        -------
        bool
            True if file was loaded successfully, False otherwise.
        """
        try:
            with zipfile.ZipFile(file_path_or_obj) as my_zip:
                try:
                    my_zip.read("ccp.version").decode("utf-8")
                except KeyError:
                    pass

                session_state_data = {}
                for name in my_zip.namelist():
                    if name.endswith(".json"):
                        session_state_data = json.loads(my_zip.read(name))
                        session_state_data["app_type"] = "performance_evaluation"

                # extract CSV files and impeller objects
                for name in my_zip.namelist():
                    if name.endswith(".csv"):
                        if "curves_file_" in name:
                            parts = name.replace(".csv", "").split("_")
                            file_num = parts[2]
                            case = parts[-1]
                            session_state_data[
                                f"curves_file_{file_num}_case_{case}"
                            ] = {
                                "name": name,
                                "content": my_zip.read(name),
                            }
                    if name.endswith(".toml"):
                        impeller_file = io.StringIO(my_zip.read(name).decode("utf-8"))
                        if name.startswith("impeller_case_"):
                            case = name.replace("impeller_case_", "").replace(
                                ".toml", ""
                            )
                            session_state_data[f"impeller_case_{case}"] = (
                                ccp.Impeller.load(impeller_file)
                            )

                # Load evaluation if present
                if "evaluation.zip" in my_zip.namelist():
                    eval_bytes = my_zip.read("evaluation.zip")
                    eval_tmp = tempfile.NamedTemporaryFile(
                        suffix=".zip", delete=False
                    )
                    eval_tmp.write(eval_bytes)
                    eval_tmp.close()
                    loaded_eval = ccp.Evaluation.load(eval_tmp.name)
                    session_state_data["hist_evaluation"] = loaded_eval
                    Path(eval_tmp.name).unlink()

                    # Set date/time widget keys to match the evaluation data range
                    # so widgets reflect the saved time range instead of datetime.now()
                    if (
                        hasattr(loaded_eval, "data")
                        and loaded_eval.data is not None
                        and not loaded_eval.data.empty
                    ):
                        eval_start = pd.Timestamp(
                            loaded_eval.data.index.min()
                        ).to_pydatetime()
                        eval_end = pd.Timestamp(
                            loaded_eval.data.index.max()
                        ).to_pydatetime()
                        if eval_start.tzinfo is not None:
                            eval_start = eval_start.replace(tzinfo=None)
                        if eval_end.tzinfo is not None:
                            eval_end = eval_end.replace(tzinfo=None)
                        session_state_data["eval_start_date"] = eval_start.date()
                        session_state_data["eval_start_time"] = eval_start.time()
                        session_state_data["eval_end_date"] = eval_end.date()
                        session_state_data["eval_end_time"] = eval_end.time()

                session_state_data_copy = session_state_data.copy()
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
                            "run_evaluation",
                            "full_rebuild_evaluation",
                        )
                    ):
                        del session_state_data_copy[key]
                st.session_state.update(session_state_data_copy)
                if isinstance(file_path_or_obj, Path):
                    st.session_state.session_name = file_path_or_obj.stem
                else:
                    st.session_state.session_name = getattr(
                        file_path_or_obj, "name", ""
                    ).replace(".ccp", "")
                st.session_state.expander_state = True
                return True
        except Exception as e:
            logging.error(f"Error loading .ccp file: {e}")
            return False

    # Auto-load example file in testing mode
    if TESTING_MODE and "test_file_loaded_eval" not in st.session_state:
        example_file = Path(__file__).parent.parent / "example_online.ccp"
        if example_file.exists():
            if load_ccp_file(example_file):
                st.session_state.test_file_loaded_eval = True
                st.rerun()
        else:
            st.warning(f"Testing mode: example file not found at {example_file}")
            st.session_state.test_file_loaded_eval = True

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
            if load_ccp_file(file):
                st.rerun()

        if save_button:
            session_state_dict = dict(st.session_state)

            file_name = f"{st.session_state.session_name}.ccp"
            app_dir = Path(__file__).resolve().parent.parent
            file_path = app_dir / file_name
            session_state_dict_copy = session_state_dict.copy()
            with zipfile.ZipFile(file_path, "w") as my_zip:
                my_zip.writestr("ccp.version", ccp.__version__)

                # Save impeller objects for each case
                for key, value in session_state_dict.items():
                    if isinstance(value, ccp.Impeller):
                        my_zip.writestr(
                            f"{key}.toml",
                            toml.dumps(value._dict_to_save()),
                        )
                        del session_state_dict_copy[key]
                    if key.startswith("curves_file_") and "_case_" in key:
                        if session_state_dict[key] is not None:
                            parts = key.split("_")
                            file_num = parts[2]
                            case = parts[-1]
                            my_zip.writestr(
                                f"curves_file_{file_num}_case_{case}.csv",
                                session_state_dict[key]["content"],
                            )
                        if key in session_state_dict_copy:
                            del session_state_dict_copy[key]

                # Save Evaluation object if present
                hist_eval = st.session_state.get("hist_evaluation")
                if hist_eval is not None:
                    eval_tmp = tempfile.NamedTemporaryFile(
                        suffix=".zip", delete=False
                    )
                    eval_tmp.close()
                    hist_eval.save(eval_tmp.name)
                    with open(eval_tmp.name, "rb") as ef:
                        my_zip.writestr("evaluation.zip", ef.read())
                    Path(eval_tmp.name).unlink()

                session_state_dict_copy["app_type"] = "performance_evaluation"

                # Remove non-serializable keys
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
                            "run_evaluation",
                            "full_rebuild_evaluation",
                        )
                    ) or isinstance(
                        value,
                        (
                            bytes,
                            pd.DataFrame,
                            st.runtime.uploaded_file_manager.UploadedFile,
                            datetime,
                            timedelta,
                        ),
                    ) or type(value).__name__ in ("date", "time"):
                        keys_to_remove.append(key)
                    elif isinstance(value, dict) and any(
                        isinstance(v, (bytes, pd.DataFrame))
                        for v in value.values()
                    ):
                        keys_to_remove.append(key)

                for key in [
                    "hist_evaluation",
                    "pi_password",
                    "ai_api_key",
                    "ai_api_key_input",
                    "ai_azure_endpoint",
                    "ai_azure_endpoint_input",
                    "ai_azure_deployment",
                    "ai_azure_deployment_input",
                    "_report_html",
                ]:
                    if key in session_state_dict_copy:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    if key in session_state_dict_copy:
                        del session_state_dict_copy[key]

                # Also remove any remaining non-serializable values
                for key in list(session_state_dict_copy.keys()):
                    value = session_state_dict_copy[key]
                    try:
                        json.dumps(value)
                    except (TypeError, ValueError):
                        del session_state_dict_copy[key]

                session_state_json = json.dumps(session_state_dict_copy)
                my_zip.writestr("session_state.json", session_state_json)

            with open(file_path, "rb") as file:
                st.download_button(
                    label="💾 Save As",
                    data=file,
                    file_name=file_name,
                    mime="application/json",
                )

    # Options sidebar
    with st.sidebar.expander("⚙️ Options"):
        st.session_state.ai_enabled = st.checkbox(
            "AI Analysis in Report",
            value=st.session_state.ai_enabled,
            help="Use AI to generate analysis text in the performance report.",
        )

        if st.session_state.ai_enabled:
            st.session_state.ai_provider = st.selectbox(
                "AI Provider",
                options=["gemini", "azure"],
                index=["gemini", "azure"].index(st.session_state.ai_provider),
                format_func=lambda x: {
                    "gemini": "Google Gemini",
                    "azure": "Azure OpenAI",
                }[x],
                key="ai_provider_select",
            )

            st.session_state.ai_api_key = st.text_input(
                "API Key",
                value=st.session_state.ai_api_key,
                type="password",
                key="ai_api_key_input",
            )

            if st.session_state.ai_provider == "azure":
                st.session_state.ai_azure_endpoint = st.text_input(
                    "Azure Endpoint",
                    value=st.session_state.ai_azure_endpoint,
                    key="ai_azure_endpoint_input",
                    placeholder="https://your-resource.openai.azure.com/",
                )
                st.session_state.ai_azure_deployment = st.text_input(
                    "Azure Deployment",
                    value=st.session_state.ai_azure_deployment,
                    key="ai_azure_deployment_input",
                    placeholder="gpt-4o",
                )

    # Shared UI sections
    fluid_list, gas_compositions_table = gas_selection_ui()
    design_cases_section()
    curves_upload_section()
    tags_config_section(fluid_list)

    # =========================================================================
    # Performance Evaluation Section (unique to this page)
    # =========================================================================
    with st.expander("Performance Evaluation Results", expanded=True):
        st.markdown("### Historical Performance Evaluation")

        # Get available cases (those with loaded impellers)
        available_cases, impellers_list = get_available_impellers()

        if not available_cases:
            st.warning(
                "No design cases loaded. Please upload performance curves for at least one case."
            )
        else:
            # Derive default date/time range from saved evaluation if available
            existing_eval = st.session_state.get("hist_evaluation")
            if (
                existing_eval is not None
                and hasattr(existing_eval, "data")
                and getattr(existing_eval, "data", None) is not None
                and not existing_eval.data.empty
            ):
                default_start_dt = pd.Timestamp(
                    existing_eval.data.index.min()
                ).to_pydatetime()
                default_end_dt = pd.Timestamp(
                    existing_eval.data.index.max()
                ).to_pydatetime()
                # Strip timezone info for date/time widgets
                if default_start_dt.tzinfo is not None:
                    default_start_dt = default_start_dt.replace(tzinfo=None)
                if default_end_dt.tzinfo is not None:
                    default_end_dt = default_end_dt.replace(tzinfo=None)
            else:
                default_start_dt = datetime.now() - timedelta(days=30)
                default_end_dt = datetime.now()

            # Data input controls
            control_row = st.columns([1, 1, 1, 1])
            with control_row[0]:
                start_date = st.date_input(
                    "Start Date",
                    value=default_start_dt.date(),
                    key="eval_start_date",
                )
            with control_row[1]:
                start_time_input = st.time_input(
                    "Start Time",
                    value=default_start_dt.time(),
                    key="eval_start_time",
                )
            with control_row[2]:
                end_date = st.date_input(
                    "End Date",
                    value=default_end_dt.date(),
                    key="eval_end_date",
                )
            with control_row[3]:
                end_time_input = st.time_input(
                    "End Time",
                    value=default_end_dt.time(),
                    key="eval_end_time",
                )

            # Data quality thresholds
            with st.expander("Data Quality Thresholds", expanded=False):
                st.caption(
                    "Points are marked as invalid if fluctuation exceeds these thresholds. "
                    "Fluctuation = (max - min) / mean × 100%"
                )
                threshold_cols = st.columns(3)
                with threshold_cols[0]:
                    st.number_input(
                        "Temperature (%)",
                        min_value=0.1,
                        max_value=10.0,
                        value=0.5,
                        step=0.1,
                        key="temperature_fluctuation",
                    )
                with threshold_cols[1]:
                    st.number_input(
                        "Pressure (%)",
                        min_value=0.1,
                        max_value=10.0,
                        value=2.0,
                        step=0.1,
                        key="pressure_fluctuation",
                    )
                with threshold_cols[2]:
                    st.number_input(
                        "Speed (%)",
                        min_value=0.1,
                        max_value=10.0,
                        value=0.5,
                        step=0.1,
                        key="speed_fluctuation",
                    )

            button_cols = st.columns(3)
            with button_cols[0]:
                run_button = st.button(
                    "Run Evaluation",
                    key="run_evaluation",
                    type="primary",
                    on_click=lambda: st.session_state.update(
                        _trigger_evaluation="run"
                    ),
                    use_container_width=True,
                )
            with button_cols[1]:
                full_rebuild_button = st.button(
                    "Full Rebuild",
                    key="full_rebuild_evaluation",
                    type="primary",
                    help=(
                        "Re-run full clustering and impeller conversion over "
                        "the selected range."
                    ),
                    on_click=lambda: st.session_state.update(
                        _trigger_evaluation="full_rebuild"
                    ),
                    use_container_width=True,
                )
            with button_cols[2]:
                report_figs = st.session_state.get("_report_figures")
                report_html = st.session_state.get("_report_html")
                if report_figs is not None and report_html is not None:
                    # Report is ready — show download button
                    st.download_button(
                        "Download Report",
                        data=report_html,
                        file_name="ccp_performance_report.html",
                        mime="text/html",
                        type="primary",
                        use_container_width=True,
                    )
                elif report_figs is not None:
                    # Evaluation done but report not yet generated
                    st.button(
                        "Create Report",
                        type="primary",
                        use_container_width=True,
                        on_click=lambda: st.session_state.update(
                            _trigger_report=True
                        ),
                    )
                else:
                    st.button(
                        "Create Report",
                        type="primary",
                        use_container_width=True,
                        disabled=True,
                        help="Run an evaluation first to generate a report.",
                    )

            # Handle report generation trigger
            if st.session_state.pop("_trigger_report", False):
                report_figs = st.session_state.get("_report_figures")
                if report_figs is not None:
                    ai_analysis = None
                    ai_error = None
                    if (
                        st.session_state.get("ai_enabled")
                        and st.session_state.get("ai_api_key")
                    ):
                        try:
                            with st.spinner("Generating AI analysis..."):
                                provider = get_provider(
                                    provider_name=st.session_state.ai_provider,
                                    api_key=st.session_state.ai_api_key,
                                    azure_endpoint=st.session_state.get(
                                        "ai_azure_endpoint", ""
                                    ),
                                    azure_deployment=st.session_state.get(
                                        "ai_azure_deployment", ""
                                    ),
                                )
                                ai_analysis = generate_ai_analysis(
                                    provider=provider,
                                    trend_regression=report_figs.get(
                                        "trend_regression", {}
                                    ),
                                    summary_stats_df=report_figs[
                                        "summary_stats"
                                    ],
                                    session_name=report_figs.get(
                                        "session_name", ""
                                    ),
                                )
                        except Exception as e:
                            ai_error = str(e)

                    st.session_state["_report_html"] = generate_html_report(
                        trend_figs=report_figs["trend"],
                        perf_figs=report_figs["perf"],
                        summary_stats_df=report_figs["summary_stats"],
                        session_name=report_figs.get("session_name", ""),
                        ai_analysis=ai_analysis,
                    )
                    if ai_error:
                        st.session_state["_ai_error"] = ai_error
                    st.rerun()

            # Show AI error from previous report generation
            ai_error = st.session_state.pop("_ai_error", None)
            if ai_error:
                st.error(
                    f"AI analysis failed (report generated without AI): {ai_error}"
                )

            trigger = st.session_state.pop("_trigger_evaluation", None)
            if trigger is not None:
                try:
                    tag_mappings = build_tag_mappings()
                    data_units = build_data_units(tag_mappings)

                    start_datetime = datetime.combine(start_date, start_time_input)
                    end_datetime = datetime.combine(end_date, end_time_input)

                    existing_eval = st.session_state.get("hist_evaluation")
                    can_incremental = (
                        trigger != "full_rebuild"
                        and existing_eval is not None
                        and hasattr(existing_eval, "data")
                        and getattr(existing_eval, "data", None) is not None
                        and not existing_eval.data.empty
                    )

                    if can_incremental:
                        existing_start = pd.Timestamp(existing_eval.data.index.min())
                        existing_end = pd.Timestamp(existing_eval.data.index.max())
                        start_ts = align_timestamp_to_reference(
                            start_datetime, existing_start
                        )
                        end_ts = align_timestamp_to_reference(end_datetime, existing_end)
                        append_only_window = (
                            start_ts <= existing_start and end_ts > existing_end
                        )
                        if append_only_window:
                            with st.spinner("Fetching new data from PI..."):
                                # append_new_data keeps strict > last index.
                                df_new = fetch_pi_data(
                                    tag_mappings,
                                    start_time=existing_end,
                                    end_time=end_ts,
                                    testing=TESTING_MODE,
                                )

                            with st.spinner("Running incremental evaluation..."):
                                df_added = existing_eval.append_new_data(
                                    df_new,
                                    drop_invalid_values=False,
                                )

                            st.session_state.hist_evaluation = existing_eval
                            st.session_state.hist_df_raw = existing_eval.data
                            st.success(
                                "Incremental update completed! "
                                f"Added {len(df_added)} new rows."
                            )
                        elif end_datetime <= existing_end:
                            st.info(
                                "No new data in selected end time. "
                                "Evaluation kept unchanged."
                            )
                        else:
                            st.info(
                                "Date range changed (not append-only). "
                                "Use Full Rebuild for this selection."
                            )
                    else:
                        with st.spinner("Fetching data from PI..."):
                            df_raw = fetch_pi_data(
                                tag_mappings,
                                start_time=start_datetime,
                                end_time=end_datetime,
                                testing=TESTING_MODE,
                            )

                        evaluation_kwargs = build_evaluation_kwargs(
                            tag_mappings, data_units, impellers_list, df_raw,
                            testing=TESTING_MODE,
                        )
                        evaluation_kwargs["calculate_points"] = True

                        if TESTING_MODE:
                            display_debug_data(
                                "ccp.Evaluation kwargs",
                                evaluation_kwargs,
                                expanded=True,
                            )

                        with st.spinner("Running full evaluation..."):
                            evaluation = ccp.Evaluation(**evaluation_kwargs)

                        st.session_state.hist_evaluation = evaluation
                        st.success("Full evaluation completed!")

                except Exception as e:
                    import re
                    import traceback

                    error_trace = traceback.format_exc()
                    error_str = str(e)

                    # Check for PI tag not found (404) errors
                    tag_match = re.search(
                        r"Not found:\s*'([^']+)'", error_str
                    )
                    if "(404)" in error_str and tag_match:
                        tag_name = tag_match.group(1)
                        st.error(
                            f"PI tag not found: **{tag_name}**. "
                            "Please verify that the tag name is correct "
                            "and exists on the PI server."
                        )
                    else:
                        st.error(f"Error running evaluation: {error_str}")

                    logging.error(f"Error in performance evaluation: {e}")
                    if TESTING_MODE:
                        st.code(error_trace, language="python")

            # Display results if evaluation exists
            evaluation = st.session_state.get("hist_evaluation")
            if evaluation is not None and hasattr(evaluation, "df"):
                df_results = evaluation.df
                trend_figs = []
                trend_regression = {}
                perf_figs = []
                summary_stats_df = None

                tab_trend, tab_perf, tab_data = st.tabs(
                    ["Trend Analysis", "Performance Plots", "Data Table"]
                )

                # ---- Tab 1: Trend Analysis ----
                with tab_trend:
                    st.markdown("### Performance Trends Over Time")

                    # Filter for valid calculated points
                    df_valid = df_results[
                        (df_results.get("valid", True) == True)  # noqa: E712
                        & (df_results.get("head", 0) > 0)
                    ].copy()

                    if df_valid.empty:
                        st.warning("No valid calculated points to display.")
                    else:
                        trend_plots = {
                            "Delta Efficiency (%)": "delta_eff",
                            "Delta Head (%)": "delta_head",
                            "Delta Power (%)": "delta_power",
                            "Delta Discharge Pressure (%)": "delta_p_disch",
                        }

                        plot_row1 = st.columns(2)
                        plot_row2 = st.columns(2)
                        plot_positions = [
                            plot_row1[0],
                            plot_row1[1],
                            plot_row2[0],
                            plot_row2[1],
                        ]

                        @st.cache_data
                        def generate_trend_plot(y_data, title):
                            fig = go.Figure()
                            fig.add_trace(
                                go.Scattergl(
                                    x=y_data.index,
                                    y=y_data,
                                    mode="markers",
                                    marker=dict(
                                        color="#1f77b4",
                                        size=6,
                                    ),
                                    name=title,
                                )
                            )
                            fig.add_hline(
                                y=0,
                                line_dash="dash",
                                line_color="red",
                                line_width=1,
                            )

                            regression_info = None
                            # Linear regression with confidence band
                            if len(y_data) >= 3:
                                x_num = (
                                    y_data.index.astype("int64").values
                                    / 1e9
                                )
                                slope, intercept, r, p, se = (
                                    stats.linregress(x_num, y_data)
                                )
                                y_fit = slope * x_num + intercept

                                # 95% confidence interval
                                n = len(x_num)
                                x_mean = x_num.mean()
                                ss_x = ((x_num - x_mean) ** 2).sum()
                                residuals = y_data - y_fit
                                s_err = np.sqrt(
                                    (residuals**2).sum() / (n - 2)
                                )
                                t_val = stats.t.ppf(0.975, n - 2)
                                ci = t_val * s_err * np.sqrt(
                                    1 / n
                                    + (x_num - x_mean) ** 2 / ss_x
                                )

                                # Sort for proper band rendering
                                sort_idx = np.argsort(x_num)
                                x_sorted = y_data.index[sort_idx]
                                y_fit_sorted = y_fit[sort_idx]
                                ci_sorted = ci[sort_idx]

                                fig.add_trace(
                                    go.Scatter(
                                        x=x_sorted,
                                        y=y_fit_sorted,
                                        mode="lines",
                                        line=dict(
                                            color="orange", width=2
                                        ),
                                        name="Trend",
                                    )
                                )
                                fig.add_trace(
                                    go.Scatter(
                                        x=np.concatenate(
                                            [x_sorted, x_sorted[::-1]]
                                        ),
                                        y=np.concatenate(
                                            [
                                                y_fit_sorted
                                                + ci_sorted,
                                                (
                                                    y_fit_sorted
                                                    - ci_sorted
                                                )[::-1],
                                            ]
                                        ),
                                        fill="toself",
                                        fillcolor="rgba(255,165,0,0.15)",
                                        line=dict(width=0),
                                        name="95% CI",
                                        hoverinfo="skip",
                                    )
                                )

                                # Slope as %/month
                                slope_per_month = (
                                    slope * 30.44 * 24 * 3600
                                )
                                regression_info = {
                                    "slope_per_month": slope_per_month,
                                    "r_squared": r**2,
                                    "p_value": p,
                                    "n_points": n,
                                }
                                fig.add_annotation(
                                    text=(
                                        f"slope: {slope_per_month:.3f} %/mo"
                                        f" · R²={r**2:.3f}"
                                        f" · p={p:.2e}"
                                    ),
                                    xref="paper",
                                    yref="paper",
                                    x=0.02,
                                    y=0.98,
                                    showarrow=False,
                                    font=dict(size=11),
                                    bgcolor="rgba(255,255,255,0.8)",
                                    bordercolor="#ccc",
                                    borderwidth=1,
                                )

                            fig.update_layout(
                                title=title,
                                xaxis_title="Time",
                                yaxis_title=title,
                                showlegend=False,
                            )
                            return fig, regression_info

                        trend_figs = []
                        trend_regression = {}
                        for (title, col_name), container in zip(
                            trend_plots.items(), plot_positions
                        ):
                            with container:
                                if col_name in df_valid.columns:
                                    y_data = df_valid[col_name].dropna()
                                    if y_data.empty:
                                        st.info(
                                            f"Column '{col_name}' has no data."
                                        )
                                        continue

                                    fig, regression_info = generate_trend_plot(
                                        y_data, title
                                    )
                                    if regression_info is not None:
                                        trend_regression[col_name] = regression_info
                                    trend_figs.append(fig)
                                    st.plotly_chart(fig, width="stretch")
                                else:
                                    st.info(f"Column '{col_name}' not available.")

                # ---- Tab 2: Performance Plots ----
                with tab_perf:

                    @st.fragment
                    def display_perf_plots():
                        st.markdown("### Performance Curves with Historical Points")

                        df_valid_perf = df_results[
                            (df_results.get("valid", True) == True)  # noqa: E712
                            & (df_results.get("head", 0) > 0)
                        ].copy()

                        if df_valid_perf.empty:
                            st.warning("No valid calculated points to display.")
                            return

                        perf_controls = st.columns([1, 1, 4])
                        with perf_controls[0]:
                            cluster_options = list(range(len(evaluation.impellers_new)))
                            cluster_idx = st.selectbox(
                                "Converted Curve",
                                options=cluster_options,
                                format_func=lambda x: f"Converted Curve {x + 1}",
                                key="eval_cluster_idx",
                            )
                        with perf_controls[1]:
                            show_similarity = st.checkbox(
                                "Show similarity",
                                value=False,
                                key="eval_show_similarity",
                            )

                        converted_impeller = evaluation.impellers_new[cluster_idx]

                        # Filter historical points to the selected cluster
                        if "cluster" in df_valid_perf.columns:
                            df_cluster = df_valid_perf[
                                df_valid_perf["cluster"] == cluster_idx
                            ].copy()
                        else:
                            df_cluster = df_valid_perf

                        if df_cluster.empty:
                            st.warning(
                                f"No valid points for Converted Curve {cluster_idx + 1}."
                            )
                            return

                        # Plot units
                        plot_flow_units = st.session_state.get(
                            "loaded_curves_flow_units", "m³/s"
                        )
                        plot_head_units = "kJ/kg"
                        plot_power_units = "kW"
                        plot_p_units = "bar"

                        # Prepare historical points with timescale coloring
                        if "timescale" not in df_cluster.columns:
                            idx_num = pd.to_numeric(
                                df_cluster.index.astype("int64")
                            )
                            df_cluster["timescale"] = (
                                (idx_num - idx_num.min())
                                / max(idx_num.max() - idx_num.min(), 1)
                            )

                        # Evaluation results are in ccp internal units (flow_v: m³/s)
                        flow_v_data_units = "m³/s"
                        hist_flow = df_cluster["flow_v"].apply(
                            lambda v: Q_(v, flow_v_data_units)
                            .to(plot_flow_units)
                            .m
                        )
                        hist_head = df_cluster["head"].apply(
                            lambda v: Q_(v, "J/kg").to(plot_head_units).m
                        )
                        hist_eff = df_cluster["eff"]
                        hist_power = df_cluster["power"].apply(
                            lambda v: Q_(v, "W").to(plot_power_units).m
                        )
                        hist_p_disch = df_cluster.get("p_disch")
                        if hist_p_disch is not None:
                            hist_p_disch = hist_p_disch.apply(
                                lambda v: Q_(v, "bar").to(plot_p_units).m
                            )

                        # Use median speed for the design curve
                        speed_data_units = st.session_state.get(
                            "speed_unit", "rpm"
                        )
                        median_speed = Q_(
                            df_cluster["speed"].median(), speed_data_units
                        )

                        # Build colorbar with date tick labels
                        n_ticks = min(5, len(df_cluster))
                        tick_positions = [
                            i / max(n_ticks - 1, 1)
                            for i in range(n_ticks)
                        ]
                        tick_indices = [
                            int(p * max(len(df_cluster) - 1, 0))
                            for p in tick_positions
                        ]
                        tick_labels = [
                            df_cluster.index[i].strftime("%Y-%m-%d")
                            for i in tick_indices
                        ]
                        colorbar_cfg = dict(
                            title=dict(text="Date", side="right"),
                            tickvals=tick_positions,
                            ticktext=tick_labels,
                            orientation="h",
                            yanchor="top",
                            y=-0.2,
                            xanchor="center",
                            x=0.5,
                            thickness=12,
                            len=0.8,
                        )

                        @st.cache_data
                        def generate_eval_base_curves(
                            _impeller,
                            impeller_hash,
                            speed_m,
                            speed_units,
                            flow_v_units,
                            head_units,
                            power_units,
                            p_units,
                            similarity,
                        ):
                            _speed = ccp.Q_(speed_m, speed_units)
                            head_fig = _impeller.head_plot(
                                speed=_speed,
                                flow_v_units=flow_v_units,
                                head_units=head_units,
                                similarity=similarity,
                            )
                            power_fig = _impeller.power_plot(
                                speed=_speed,
                                flow_v_units=flow_v_units,
                                power_units=power_units,
                                similarity=similarity,
                            )
                            eff_fig = _impeller.eff_plot(
                                speed=_speed,
                                flow_v_units=flow_v_units,
                                similarity=similarity,
                            )
                            disch_p_fig = _impeller.disch.p_plot(
                                speed=_speed,
                                flow_v_units=flow_v_units,
                                p_units=p_units,
                                similarity=similarity,
                            )
                            return head_fig, power_fig, eff_fig, disch_p_fig

                        try:
                            head_fig, power_fig, eff_fig, disch_p_fig = (
                                generate_eval_base_curves(
                                    converted_impeller,
                                    hash(converted_impeller),
                                    median_speed.m,
                                    str(median_speed.units),
                                    plot_flow_units,
                                    plot_head_units,
                                    plot_power_units,
                                    plot_p_units,
                                    show_similarity,
                                )
                            )
                        except Exception as e:
                            st.error(f"Error creating base curve plots: {e}")
                            head_fig = power_fig = eff_fig = disch_p_fig = None

                        # Add historical point overlays (not cached - data changes)
                        if head_fig is not None:
                            head_fig.add_trace(
                                go.Scatter(
                                    x=hist_flow,
                                    y=hist_head,
                                    mode="markers",
                                    marker=dict(
                                        color=df_cluster["timescale"],
                                        colorscale="Viridis",
                                        size=6,
                                        colorbar=colorbar_cfg,
                                    ),
                                    name="Historical Points",
                                )
                            )
                        if power_fig is not None:
                            power_fig.add_trace(
                                go.Scatter(
                                    x=hist_flow,
                                    y=hist_power,
                                    mode="markers",
                                    marker=dict(
                                        color=df_cluster["timescale"],
                                        colorscale="Viridis",
                                        size=6,
                                    ),
                                    name="Historical Points",
                                    showlegend=True,
                                )
                            )
                        if eff_fig is not None:
                            eff_fig.add_trace(
                                go.Scatter(
                                    x=hist_flow,
                                    y=hist_eff,
                                    mode="markers",
                                    marker=dict(
                                        color=df_cluster["timescale"],
                                        colorscale="Viridis",
                                        size=6,
                                    ),
                                    name="Historical Points",
                                    showlegend=True,
                                )
                            )
                        if disch_p_fig is not None and hist_p_disch is not None:
                            disch_p_fig.add_trace(
                                go.Scatter(
                                    x=hist_flow,
                                    y=hist_p_disch,
                                    mode="markers",
                                    marker=dict(
                                        color=df_cluster["timescale"],
                                        colorscale="Viridis",
                                        size=6,
                                    ),
                                    name="Historical Points",
                                    showlegend=True,
                                )
                            )

                        plot_col1, plot_col2 = st.columns(2)
                        with plot_col1:
                            if head_fig is not None:
                                st.plotly_chart(head_fig, width="stretch")
                            if power_fig is not None:
                                st.plotly_chart(power_fig, width="stretch")
                        with plot_col2:
                            if eff_fig is not None:
                                st.plotly_chart(eff_fig, width="stretch")
                            if disch_p_fig is not None:
                                st.plotly_chart(disch_p_fig, width="stretch")

                        # Store perf_figs in session state for report generation
                        st.session_state["_perf_figs"] = [
                            fig
                            for fig in [
                                head_fig,
                                power_fig,
                                eff_fig,
                                disch_p_fig,
                            ]
                            if fig is not None
                        ]

                    display_perf_plots()
                    perf_figs = st.session_state.get("_perf_figs", [])

                # ---- Tab 3: Data Table ----
                with tab_data:
                    st.markdown("### Evaluation Results Data")

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
                        "p_disch",
                        "expected_p_disch",
                        "delta_p_disch",
                        "valid",
                        "cluster",
                    ]
                    available_cols = [
                        c for c in display_cols if c in df_results.columns
                    ]

                    st.dataframe(
                        df_results[available_cols],
                        width="stretch",
                    )

                    # Summary statistics for delta columns
                    delta_cols = [
                        c
                        for c in [
                            "delta_eff",
                            "delta_head",
                            "delta_power",
                            "delta_p_disch",
                        ]
                        if c in df_results.columns
                    ]
                    if delta_cols:
                        df_valid_deltas = df_results[
                            (df_results.get("valid", True) == True)  # noqa: E712
                            & (df_results.get("head", 0) > 0)
                        ]
                        if not df_valid_deltas.empty:
                            summary_stats_df = df_valid_deltas[
                                delta_cols
                            ].describe()
                            st.markdown("### Summary Statistics (Delta Columns)")
                            st.dataframe(
                                summary_stats_df,
                                width="stretch",
                            )

                    # Download as Excel
                    excel_data = to_excel(df_results[available_cols])
                    st.download_button(
                        label="📥 Download as Excel",
                        data=excel_data,
                        file_name="evaluation_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                # Store figures in session state for report generation
                # Clear cached report so user must click "Create Report" again
                st.session_state["_report_figures"] = {
                    "trend": trend_figs,
                    "perf": perf_figs,
                    "summary_stats": summary_stats_df,
                    "trend_regression": trend_regression,
                    "session_name": st.session_state.get("session_name", ""),
                }
                st.session_state.pop("_report_html", None)


if __name__ == "__main__":
    run_app(main, "performance_evaluation")
