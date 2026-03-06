"""Module to keep everything that is common to ccp_app_straight_through and ccp_app_back_to_back."""

import base64
import io
import json
import logging
import os
import zipfile

import numpy as np
import pandas as pd
import sentry_sdk
import streamlit as st
import toml
from packaging.version import Version
from pathlib import Path

import ccp
from ccp import Q_

# parameters with name and label
flow_m_units = ["kg/h", "kg/min", "kg/s", "lbm/h", "lbm/min", "lbm/s"]
flow_v_units = ["m³/h", "m³/min", "m³/s"]
flow_units = flow_m_units + flow_v_units
pressure_units = ["bar", "kgf/cm²", "barg", "Pa", "kPa", "MPa", "psi", "mm*H2O*g0"]
temperature_units = ["degK", "degC", "degF", "degR"]
head_units = ["kJ/kg", "J/kg", "m*g0", "ft"]
power_units = ["kW", "hp", "W", "Btu/h", "MW"]
speed_units = ["rpm", "Hz"]
length_units = ["m", "mm", "ft", "in"]
specific_heat_units = ["kJ/kg/degK", "J/kg/degK", "cal/g/degC", "Btu/lb/degF"]
oil_iso_options = ["VG 32", "VG 46"]
oil_flow_units = ["l/min", "l/h", "gal/min", "m³/h", "m³/min", "m³/s"]
density_units = ["kg/m³", "g/cm³", "g/ml", "g/l"]

polytropic_methods = {
    "Sandberg-Colby": "sandberg_colby",
    "Sandberg-Colby Multistep": "sandberg_colby_multistep",
    "Huntington": "huntington",
    "Mallen-Saville": "mallen_saville",
    "Schultz": "schultz",
}

parameters_map = {
    "flow": {
        "label": "Flow",
        "units": flow_units,
        "help": "Flow can be mass flow or volumetric flow depending on the selected unit.",
    },
    "flow_v": {
        "label": "Volumetric Flow",
        "units": flow_v_units,
        "help": "Volumetric flow.",
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
        "help": "Temperature difference between the casing and the ambient temperature.",
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
        "help": "Second section suction pressure.",
    },
    "end_seal_upstream_temperature": {
        "label": "Temperature Upstream End Seal",
        "units": temperature_units,
        "help": "Second section suction temperature.",
    },
    "div_wall_flow_m": {
        "label": "Division Wall Flow",
        "units": flow_m_units,
        "help": "Flow through the division wall if measured. Otherwise it is calculated from the First Section Discharge Flow.",
    },
    "div_wall_upstream_pressure": {
        "label": "Pressure Upstream Division Wall",
        "units": pressure_units,
        "help": "Second section discharge pressure.",
    },
    "div_wall_upstream_temperature": {
        "label": "Temperature Upstream Division Wall",
        "units": temperature_units,
        "help": "Second section discharge temperature.",
    },
    "first_section_discharge_flow_m": {
        "label": "First Section Discharge Flow",
        "units": flow_m_units,
        "help": "If the Division Wall Flow is not measured, we use this value to calculate it.",
    },
    "seal_gas_flow_m": {
        "label": "Seal Gas Flow",
        "units": flow_m_units,
    },
    "seal_gas_temperature": {
        "label": "Seal Gas Temperature",
        "units": temperature_units,
    },
    "oil_flow_journal_bearing_de": {
        "label": "Oil Flow Journal Bearing DE",
        "units": oil_flow_units,
    },
    "oil_flow_journal_bearing_nde": {
        "label": "Oil Flow Journal Bearing NDE",
        "units": oil_flow_units,
    },
    "oil_flow_thrust_bearing_nde": {
        "label": "Oil Flow Thrust Bearing NDE",
        "units": oil_flow_units,
    },
    "oil_inlet_temperature": {
        "label": "Oil Inlet Temperature",
        "units": temperature_units,
    },
    "oil_outlet_temperature_de": {
        "label": "Oil Outlet Temperature DE",
        "units": temperature_units,
    },
    "oil_outlet_temperature_nde": {
        "label": "Oil Outlet Temperature NDE",
        "units": temperature_units,
    },
    "head": {
        "label": "Head",
        "units": head_units,
    },
    "eff": {
        "label": "Efficiency",
        "units": [""],
    },
    "power": {
        "label": "Gas Power",
        "units": power_units,
    },
    "power_shaft": {
        "label": "Shaft Power",
        "units": power_units,
    },
    "b": {
        "label": "First Impeller Width",
        "units": length_units,
    },
    "D": {
        "label": "First Impeller Diameter",
        "units": length_units,
    },
    "surface_roughness": {
        "label": "Surface Roughness",
        "units": length_units + ["microm"],
        "help": "Mean surface roughness of the gas path.",
    },
    "casing_area": {
        "label": "Casing Area",
        "units": ["m²", "mm²", "ft²", "in²"],
    },
    "outer_diameter_fo": {
        "label": "Outer Diameter",
        "units": ["mm", "m", "ft", "in"],
        "help": "Outer diameter of orifice plate.",
    },
    "inner_diameter_fo": {
        "label": "Inner Diameter",
        "units": ["mm", "m", "ft", "in"],
        "help": "Inner diameter of orifice plate.",
    },
    "upstream_pressure_fo": {
        "label": "Upstream Pressure",
        "units": pressure_units,
        "help": "Upstream pressure of orifice plate.",
    },
    "upstream_temperature_fo": {
        "label": "Upstream Temperature",
        "units": temperature_units,
        "help": "Upstream temperature of orifice plate.",
    },
    "pressure_drop_fo": {
        "label": "Pressure Drop",
        "units": pressure_units,
        "help": "Pressure drop across orifice plate.",
    },
    "tappings_fo": {
        "label": "Tappings",
        "units": ["flange", "corner", "D D/2"],
        "help": "Pressure tappings type.",
    },
    "mass_flow_fo": {
        "label": "Mass Flow (Result)",
        "units": ["kg/h", "lbm/h", "kg/s", "lbm/s"],
    },
    "oil_specific_heat": {
        "label": "Oil Specific Heat",
        "units": specific_heat_units,
    },
    "oil_density": {
        "label": "Oil Density",
        "units": density_units,
    },
}


def specific_heat_calculate(T_in, T_out, oil_iso_classification):
    T_in = T_in.to("degC").m
    T_out = T_out.to("degC").m

    if oil_iso_classification[3:] == "32":
        a = -0.0000019
        b = 0.0042
        c = 1.80
    else:
        a = -0.0000018
        b = 0.0040
        c = 1.83
    Cp = (
        a * (T_out**3 - T_in**3) / 3 + b * (T_out**2 - T_in**2) / 2 + c * (T_out - T_in)
    ) / (T_out - T_in)
    return Q_(Cp, "kJ/kg/degK")


def density_calculate(T_in, T_out, oil_iso_classification):
    T_in = T_in.to("degC").m
    T_out = T_out.to("degC").m
    beta = Q_(0.00075, "1/degC").m

    if oil_iso_classification[3:] == "32":
        rho_15 = Q_(870, "kg/m³").m
    else:
        rho_15 = Q_(876, "kg/m³").m

    density = (
        rho_15
        / (beta * (T_out - T_in))
        * (np.log(1 + beta * T_out - 15 * beta) - np.log(1 + beta * T_in - 15 * beta))
    )
    return Q_(density, "kg/m³")


def convert(data, version):
    version = Version(version)
    # previous than v0.3.6 and older
    if version < Version("0.3.6"):  # update
        if isinstance(data, io.StringIO):
            file = toml.load(data)
            new_file = {}
            for k, v in file.items():
                if k == "speed":
                    new_file["speed_operational"] = v
                else:
                    new_file[k] = v
            data = io.StringIO(toml.dumps(new_file))
    # previous than v0.3.7
    if version < Version("0.3.7"):
        if isinstance(data, dict):
            gas_compositions_table = {}
            gas_list = []
            for key in data:
                if key.startswith("gas"):
                    try:
                        gas_list.append(f"gas_{int(key.split('_')[1])}")
                    except ValueError:
                        continue

            gas_list = list(set(gas_list))
            gas_list.sort()

            data_copy = data.copy()

            for gas in gas_list:
                gas_compositions_table[gas] = {}
                for k, v in data_copy.items():
                    if k.startswith(gas) and "component" in k:
                        j = k.split("_")[-1]
                        gas_compositions_table[gas][f"component_{j}"] = v
                        del data[k]
                    elif k.startswith(gas) and "molar_fraction" in k:
                        j = k.split("_")[-1]
                        gas_compositions_table[gas][f"molar_fraction_{j}"] = v
                        del data[k]

            # check if nothing is found
            filled = [True if v else False for k, v in gas_compositions_table.items()]
            if all(filled):
                data["gas_compositions_table"] = gas_compositions_table

    return data


def get_gas_composition(gas_name, gas_compositions_table, default_components):
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
            for column in gas_compositions_table[gas]:
                if "component" in column:
                    idx = column.split("_")[1]
                    component = gas_compositions_table[gas][f"component_{idx}"]
                    molar_fraction = gas_compositions_table[gas][
                        f"molar_fraction_{idx}"
                    ]
                    if molar_fraction == "":
                        molar_fraction = 0
                    molar_fraction = float(molar_fraction)
                    if molar_fraction != 0:
                        gas_composition[component] = molar_fraction

    return gas_composition


def to_excel(df):
    """Function to convert pandas dataframe to excel file to be downloaded."""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1")
    writer.close()
    processed_data = output.getvalue()
    return processed_data


def gas_selection_form(fluid_list, default_components):
    """Formulary for gas selection."""
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
                    width="stretch",
                    column_config={
                        "component": st.column_config.SelectboxColumn(
                            "comp.",
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

    return gas_compositions_table


def display_debug_data(title, data, expanded=False):
    """Display debug data in an expandable section for testing mode.

    Parameters
    ----------
    title : str
        Title for the debug section.
    data : dict, pd.DataFrame, or any
        Data to display. Handles different types appropriately:
        - dict: displays each key-value pair, with special handling for
          DataFrames and pint Quantities
        - pd.DataFrame: displays as a dataframe
        - other: displays using st.write
    expanded : bool, optional
        Whether the expander should be initially expanded. Default False.
    """
    with st.expander(f"🔧 DEBUG: {title}", expanded=expanded):
        if isinstance(data, dict):
            for key, value in data.items():
                st.markdown(f"**{key}:**")
                if isinstance(value, pd.DataFrame):
                    st.dataframe(value, width="stretch")
                elif hasattr(value, "magnitude") and hasattr(value, "units"):
                    # Handle pint Quantity objects
                    st.code(f"{value.magnitude} {value.units}")
                elif isinstance(value, (list, tuple)):
                    # Handle lists (e.g., list of impellers)
                    st.write(f"List with {len(value)} items:")
                    for i, item in enumerate(value):
                        if hasattr(item, "__class__"):
                            st.text(f"  [{i}]: {item.__class__.__name__}")
                        else:
                            st.text(f"  [{i}]: {item}")
                elif isinstance(value, dict):
                    st.json(value)
                else:
                    st.write(value)
                st.divider()
        elif isinstance(data, pd.DataFrame):
            st.dataframe(data, width="stretch")
        else:
            st.write(data)


def image_base64(image_path):
    """Convert image file to base64-encoded HTML img tag."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    html_string = f"""
    <div style="text-align: center;">
        <img src="data:image/png;base64,{encoded_string}" width="250">
    </div>
    """
    return html_string


def init_sentry():
    """Initialize Sentry error tracking when not in standalone mode."""
    if not os.environ.get("CCP_STANDALONE"):
        sentry_sdk.init(
            dsn="https://8fd0e79dffa94dbb9747bf64e7e55047@o348313.ingest.sentry.io/4505046640623616",
            traces_sample_rate=1.0,
            auto_enabling_integrations=False,
        )


def setup_page(page_title="ccp"):
    """Initialize page config, load CSS, and render sidebar logo.

    Must be called at the start of main() in each page.
    """
    assets = Path(__file__).parent / "assets"
    ccp_ico = assets / "favicon.ico"
    ccp_logo = assets / "ccp.png"
    css_path = assets / "style.css"
    with open(css_path, "r") as f:
        css = f.read()

    st.set_page_config(
        page_title=page_title,
        page_icon=str(ccp_ico),
        layout="wide",
    )

    with st.sidebar.container():
        st.sidebar.markdown(image_base64(ccp_logo), unsafe_allow_html=True)

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    title_alignment = """
    <p style="text-align: center; font-weight: bold; font-size:20px;">
     ccp
    </p>
    """
    st.sidebar.markdown(title_alignment, unsafe_allow_html=True)


def get_fluid_list():
    """Get sorted fluid list and default gas components.

    Returns
    -------
    fluid_list : list
        Sorted list of available fluid names.
    default_components : list
        Default gas component names.
    """
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

    return fluid_list, default_components


def get_index_selected_gas(gas_options, gas_name):
    """Get the index of the selected gas in gas_options list.

    Parameters
    ----------
    gas_options : list
        List of available gas names.
    gas_name : str
        Session state key for the gas selection.
    """
    try:
        index_gas_name = gas_options.index(st.session_state[gas_name])
    except (KeyError, ValueError):
        index_gas_name = 0
    return index_gas_name


def highlight_cell(styled_df, df, row_index, col_index, lower_limit, higher_limit):
    """Apply conditional formatting to a specific cell in a DataFrame.

    Green (#C8E6C9) if value is within limits, red (#FFCDD2) otherwise.

    Parameters
    ----------
    styled_df : pandas.io.formats.style.Styler
        The styled DataFrame to apply formatting to.
    df : pandas.DataFrame
        The original DataFrame.
    row_index : int or str
        Row index of the cell.
    col_index : int or str
        Column index of the cell.
    lower_limit : float
        Lower limit of the acceptable range.
    higher_limit : float
        Upper limit of the acceptable range.

    Returns
    -------
    pandas.io.formats.style.Styler
        Styled DataFrame with the cell highlighted.
    """
    cell_value = df.loc[row_index, col_index]
    if cell_value >= lower_limit and cell_value <= higher_limit:
        styled_df = styled_df.map(
            lambda x: "background-color: #C8E6C9" if x == cell_value else ""
        ).map(lambda x: "font-color: #33691E" if x == cell_value else "")
    else:
        styled_df = styled_df.map(
            lambda x: "background-color: #FFCDD2" if x == cell_value else ""
        ).map(lambda x: "font-color: #FFCDD2" if x == cell_value else "")

    return styled_df


def oil_input_widgets():
    """Render oil parameter input widgets in the sidebar options.

    Renders checkboxes and inputs for oil specific heat, density,
    and ISO classification. Must be called inside a sidebar expander.

    Returns
    -------
    oil_specific_heat : bool
        Whether specific heat input is enabled.
    oil_specific_heat_value : pint.Quantity or None
        Oil specific heat value if enabled.
    oil_density_value : pint.Quantity or None
        Oil density value if enabled.
    oil_iso : bool
        Whether ISO classification is enabled.
    oil_iso_classification : str
        Selected ISO classification.
    """
    def on_oil_specific_heat_change():
        if st.session_state.oil_specific_heat:
            st.session_state.oil_iso = False

    def on_oil_iso_change():
        if st.session_state.oil_iso:
            st.session_state.oil_specific_heat = False

    st.text("Test Lube Oil")
    oil_specific_heat = st.checkbox(
        "Specific Heat",
        key="oil_specific_heat",
        value=False,
        on_change=on_oil_specific_heat_change,
        help="If marked, uses this oil specific heat "
        "and density for bearing mechanical losses calculation "
        "and disables ISO oil classification.",
    )
    oil_specific_heat_magnitude_col, oil_specific_heat_unit_col = st.columns(2)
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

    st.text("Density")
    oil_density_magnitude_col, oil_density_unit_col = st.columns(2)
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

    oil_specific_heat_value = None
    oil_density_value = None
    if oil_specific_heat:
        oil_specific_heat_value = Q_(
            float(oil_specific_heat_magnitude), oil_specific_heat_unit
        ).to("kJ/kg/kelvin")
        oil_density_value = Q_(float(oil_density_magnitude), oil_density_unit).to(
            "kg/m³"
        )

    oil_iso = st.checkbox(
        "Oil ISO Classification",
        key="oil_iso",
        on_change=on_oil_iso_change,
        help="If marked, uses the ISO oil classification "
        "for bearing mechanical losses calculation "
        "and disables specific heat and density input.",
    )
    oil_iso_classification = st.selectbox(
        "ISO",
        options=oil_iso_options,
        index=oil_iso_options.index("VG 32"),
        key="oil_iso_classification",
        label_visibility="collapsed",
        disabled=not st.session_state.oil_iso,
    )

    return oil_specific_heat, oil_specific_heat_value, oil_density_value, oil_iso, oil_iso_classification


def add_background_image(limits, fig, image):
    """Add a PNG image to a plotly figure background.

    Parameters
    ----------
    limits : dict
        Dict with "x" and "y" keys, each containing "lower_limit"
        and "upper_limit" values defining the image placement area.
    fig : plotly.graph_objects.Figure
        The figure to add the background image to.
    image : bytes
        The PNG image bytes.

    Returns
    -------
    plotly.graph_objects.Figure
        The figure with the background image added.
    """
    encoded_string = base64.b64encode(image).decode()
    encoded_image = "data:image/png;base64," + encoded_string
    fig.add_layout_image(
        dict(
            source=encoded_image,
            xref="x",
            yref="y",
            x=limits["x"]["lower_limit"],
            y=limits["y"]["upper_limit"],
            sizex=float(limits["x"]["upper_limit"])
            - float(limits["x"]["lower_limit"]),
            sizey=float(limits["y"]["upper_limit"])
            - float(limits["y"]["lower_limit"]),
            sizing="stretch",
            opacity=0.5,
            layer="below",
        )
    )
    return fig


def file_sidebar(load_from_zip, save_to_zip):
    """Render the file sidebar with Load/Save functionality.

    Parameters
    ----------
    load_from_zip : callable(my_zip, version) -> dict
        Called when loading a .ccp file. Receives the opened ZipFile and
        version string. Must return a session_state_data dict with all
        loaded data (JSON session state + deserialized objects).
    save_to_zip : callable(my_zip, session_state_dict_copy) -> dict
        Called when saving. Receives the ZipFile (already has ccp.version
        written) and a mutable copy of session_state_dict. Must write
        page-specific objects to the zip and delete those keys from the
        copy. Returns the remaining dict to be saved as JSON.
    """
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
            with zipfile.ZipFile(file) as my_zip:
                try:
                    version = my_zip.read("ccp.version").decode("utf-8")
                except KeyError:
                    version = "0.3.5"

                session_state_data = load_from_zip(my_zip, version)

            session_state_data_copy = session_state_data.copy()
            for key in list(session_state_data.keys()):
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

            file_name = f"{st.session_state.session_name}.ccp"
            session_state_dict_copy = session_state_dict.copy()
            with zipfile.ZipFile(file_name, "w") as my_zip:
                my_zip.writestr("ccp.version", ccp.__version__)
                session_state_dict_copy = save_to_zip(my_zip, session_state_dict_copy)
                session_state_json = json.dumps(session_state_dict_copy)
                my_zip.writestr("session_state.json", session_state_json)

            with open(file_name, "rb") as f:
                st.download_button(
                    label="💾 Save As",
                    data=f,
                    file_name=file_name,
                    mime="application/json",
                )


def run_app(main_func, app_name):
    """Run main app function with standardized error logging."""
    try:
        main_func()
    except Exception as e:
        logging.info(f"app: {app_name}")
        logging.info(f"session state: {st.session_state}")
        logging.error(e)
        raise e
