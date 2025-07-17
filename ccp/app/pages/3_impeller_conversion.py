import ccp
import streamlit as st
import pandas as pd
import base64
import time
import sentry_sdk
import logging
from pathlib import Path

# import everything that is common to ccp_app_straight_through and ccp_app_back_to_back
from ccp.app.common import (
    pressure_units,
    temperature_units,
    flow_units,
    speed_units,
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
        page_title="ccp - Impeller Conversion",
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
    ## Impeller Conversion
    """
    )

    def get_session():
        # Initialize session state variables
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

    get_session()

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
        "Original Impeller Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Original Suction Conditions")
        st.markdown("Define the suction conditions for the original impeller data.")

        # Gas selection for original impeller
        gas_options = [st.session_state[f"gas_{i}"] for i in range(6)]

        # Gas selection container
        gas_container = st.container()
        gas_col1, gas_col2, gas_col3 = gas_container.columns(3)

        gas_col1.markdown("Gas Selection")
        gas_col2.markdown("")
        original_gas = gas_col3.selectbox(
            "Gas for Original Impeller",
            options=gas_options,
            key="original_gas_selection",
            label_visibility="collapsed",
            help="Select the gas composition for the original impeller",
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
            help="Suction pressure for the original impeller data",
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
            help="Suction temperature for the original impeller data",
        )

        # Impeller geometry parameters
        st.markdown("### Impeller Geometry")

        # Impeller Width
        width_container = st.container()
        width_col1, width_col2, width_col3 = width_container.columns(3)

        width_col1.markdown("Impeller Width (b)")
        b_unit = width_col2.selectbox(
            "Width Unit",
            options=["m", "mm", "ft", "in"],
            key="b_unit",
            label_visibility="collapsed",
            index=0,
        )
        b_value = width_col3.number_input(
            "Impeller Width (b)",
            key="b_value",
            label_visibility="collapsed",
            help="Impeller width at discharge",
        )

        # Impeller Diameter
        diameter_container = st.container()
        diameter_col1, diameter_col2, diameter_col3 = diameter_container.columns(3)

        diameter_col1.markdown("Impeller Diameter (D)")
        d_unit = diameter_col2.selectbox(
            "Diameter Unit",
            options=["m", "mm", "ft", "in"],
            key="d_unit",
            label_visibility="collapsed",
            index=0,
        )
        d_value = diameter_col3.number_input(
            "Impeller Diameter (D)",
            key="d_value",
            label_visibility="collapsed",
            help="Impeller diameter",
        )

    # Original Impeller Curves
    with st.expander(
        "Original Impeller Curves", expanded=st.session_state.expander_state
    ):
        st.markdown("### Upload Engauge Digitized Files")
        st.markdown(
            "Upload CSV files from Engauge Digitizer containing the original impeller performance curves."
        )

        # File upload areas
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Performance Curves File 1")
            curves_file_1 = st.file_uploader(
                "Upload first curves file",
                type=["csv"],
                key="curves_file_1",
                help="CSV file from Engauge Digitizer with performance curve data",
            )

        with col2:
            st.markdown("#### Performance Curves File 2")
            curves_file_2 = st.file_uploader(
                "Upload second curves file",
                type=["csv"],
                key="curves_file_2",
                help="CSV file from Engauge Digitizer with performance curve data (optional)",
            )

        # Load impeller button
        load_impeller_button = st.button(
            "Load Original Impeller",
            type="secondary",
            help="Load the original impeller from the uploaded files",
        )

        # Process uploaded files
        if load_impeller_button:
            if curves_file_1 is None:
                st.error("Please upload at least one curves file")
            else:
                try:
                    # Create temporary directory for files
                    import tempfile
                    import os
                    import shutil

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

                    # Get curve name from first file
                    curve_name = extract_curve_name(curves_file_1.name)

                    # Save uploaded files to temporary directory
                    file_1_path = temp_path / curves_file_1.name
                    with open(file_1_path, "w") as f:
                        f.write(curves_file_1.getvalue().decode("utf-8"))

                    if curves_file_2 is not None:
                        file_2_path = temp_path / curves_file_2.name
                        with open(file_2_path, "w") as f:
                            f.write(curves_file_2.getvalue().decode("utf-8"))

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
                    progress_bar = st.progress(0, text="Loading impeller from files...")

                    original_impeller = ccp.Impeller.load_from_engauge_csv(
                        suc=original_suc_state,
                        curve_name=curve_name,
                        curve_path=temp_path,
                        b=Q_(b_value, b_unit),
                        D=Q_(d_value, d_unit),
                    )

                    progress_bar.progress(100, text="Impeller loaded successfully!")
                    time.sleep(0.5)
                    progress_bar.empty()

                    # Store in session state
                    st.session_state.original_impeller = original_impeller

                    # Clean up temporary files
                    shutil.rmtree(temp_dir)

                    st.success(
                        f"Original impeller loaded successfully with {len(original_impeller.points)} points!"
                    )

                    # Display basic info
                    st.markdown("#### Loaded Impeller Information")
                    st.write(f"Curve name: {curve_name}")
                    st.write(f"Number of points: {len(original_impeller.points)}")
                    st.write(f"Number of curves: {len(original_impeller.curves)}")
                    if original_impeller.points:
                        speeds = [p.speed.to("rpm").m for p in original_impeller.points]
                        st.write(
                            f"Speed range: {min(speeds):.0f} - {max(speeds):.0f} RPM"
                        )
                        flows = [
                            p.flow_v.to("m³/h").m for p in original_impeller.points
                        ]
                        st.write(
                            f"Flow range: {min(flows):.2f} - {max(flows):.2f} m³/h"
                        )

                except Exception as e:
                    st.error(f"Error loading impeller: {str(e)}")
                    logging.error(f"Error loading impeller: {e}")

                    # Clean up temporary directory on error
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass

    # New Suction Conditions
    with st.expander(
        "New Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Target Suction Conditions")
        st.markdown("Define the new suction conditions for the impeller conversion.")

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
            if find_method == "volume_ratio":
                new_speed = st.number_input(
                    "New Speed", help="Desired speed for conversion"
                )
                new_speed_unit = st.selectbox(
                    "New Speed Unit", options=speed_units, index=0
                )
            else:
                speed_option = st.selectbox(
                    "Speed Option",
                    options=["same", "calculate"],
                    help="Keep same speed or calculate new speed",
                )
                if speed_option == "calculate":
                    new_speed = st.number_input(
                        "New Speed", help="Desired speed for conversion"
                    )
                    new_speed_unit = st.selectbox(
                        "New Speed Unit", options=speed_units, index=0
                    )
                else:
                    new_speed = "same"

    # Convert Button
    convert_button = st.button(
        "Convert Impeller",
        type="primary",
        use_container_width=True,
        help="Convert the impeller to new suction conditions",
    )

    # Conversion Process
    if convert_button:
        # Validate inputs
        if st.session_state.original_impeller is None:
            st.error(
                "Please load the original impeller first using the 'Load Original Impeller' button"
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

            progress_bar.progress(60, text="Converting impeller...")

            # Convert impeller
            conversion_kwargs = {
                "original_impeller": original_impeller,
                "suc": new_suc_state,
                "find": find_method,
            }

            if find_method == "volume_ratio":
                conversion_kwargs["speed"] = Q_(new_speed, new_speed_unit)
            elif find_method == "speed" and new_speed != "same":
                conversion_kwargs["speed"] = Q_(new_speed, new_speed_unit)
            else:
                conversion_kwargs["speed"] = new_speed

            converted_impeller = ccp.Impeller.convert_from(**conversion_kwargs)
            st.session_state.converted_impeller = converted_impeller

            progress_bar.progress(100, text="Conversion complete!")
            time.sleep(0.5)
            progress_bar.empty()

            st.success("Impeller conversion completed successfully!")

        except Exception as e:
            st.error(f"Error during conversion: {str(e)}")
            logging.error(f"Conversion error: {e}")
            progress_bar.empty()
            return

    # Results Display
    if st.session_state.converted_impeller is not None:
        with st.expander("Conversion Results", expanded=True):
            st.markdown("### Converted Impeller Performance")

            original_imp = st.session_state.original_impeller
            converted_imp = st.session_state.converted_impeller

            # Display summary
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Original Impeller")
                st.write(f"Number of points: {len(original_imp.points)}")
                st.write(
                    f"Speed range: {min(p.speed.to('rpm').m for p in original_imp.points):.0f} - {max(p.speed.to('rpm').m for p in original_imp.points):.0f} RPM"
                )
                st.write(
                    f"Flow range: {min(p.flow_v.to('m³/h').m for p in original_imp.points):.2f} - {max(p.flow_v.to('m³/h').m for p in original_imp.points):.2f} m³/h"
                )

            with col2:
                st.markdown("#### Converted Impeller")
                st.write(f"Number of points: {len(converted_imp.points)}")
                st.write(
                    f"Speed range: {min(p.speed.to('rpm').m for p in converted_imp.points):.0f} - {max(p.speed.to('rpm').m for p in converted_imp.points):.0f} RPM"
                )
                st.write(
                    f"Flow range: {min(p.flow_v.to('m³/h').m for p in converted_imp.points):.2f} - {max(p.flow_v.to('m³/h').m for p in converted_imp.points):.2f} m³/h"
                )

            # Performance curves
            st.markdown("#### Performance Curves")

            # Head curve
            try:
                fig_head = converted_imp.head_plot(
                    flow_v_units="m³/h", head_units="kJ/kg", show_points=True
                )
                fig_head.update_layout(title="Head vs Flow")
                st.plotly_chart(fig_head, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate head plot: {str(e)}")

            # Efficiency curve
            try:
                fig_eff = converted_imp.eff_plot(flow_v_units="m³/h", show_points=True)
                fig_eff.update_layout(title="Efficiency vs Flow")
                st.plotly_chart(fig_eff, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate efficiency plot: {str(e)}")

            # Power curve
            try:
                fig_power = converted_imp.power_plot(
                    flow_v_units="m³/h", power_units="kW", show_points=True
                )
                fig_power.update_layout(title="Power vs Flow")
                st.plotly_chart(fig_power, use_container_width=True)
            except Exception as e:
                st.error(f"Could not generate power plot: {str(e)}")

            # Detailed results table
            st.markdown("#### Detailed Results")

            results_data = []
            for i, point in enumerate(converted_imp.points):
                results_data.append(
                    {
                        "Point": i + 1,
                        "Flow (m³/h)": f"{point.flow_v.to('m³/h').m:.2f}",
                        "Suction P (bar)": f"{point.suc.p.to('bar').m:.2f}",
                        "Suction T (°C)": f"{point.suc.T.to('degC').m:.1f}",
                        "Discharge P (bar)": f"{point.disch.p.to('bar').m:.2f}",
                        "Discharge T (°C)": f"{point.disch.T.to('degC').m:.1f}",
                        "Speed (RPM)": f"{point.speed.to('rpm').m:.0f}",
                        "Head (kJ/kg)": f"{point.head.to('kJ/kg').m:.2f}",
                        "Efficiency": f"{point.eff.m:.3f}",
                        "Power (kW)": f"{point.power.to('kW').m:.2f}",
                    }
                )

            results_df = pd.DataFrame(results_data)
            st.dataframe(results_df, use_container_width=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.info("app: impeller_conversion")
        logging.info(f"session state: {st.session_state}")
        logging.error(e)
        raise e
