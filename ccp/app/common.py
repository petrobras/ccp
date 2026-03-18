"""Module to keep everything that is common to ccp_app_straight_through and ccp_app_back_to_back."""

import base64
import io
import json
import logging
import os
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import sentry_sdk
import streamlit as st
import toml
from packaging.version import Version

import ccp
from ccp import Q_

# parameters with name and label
flow_m_units = ["kg/h", "kg/min", "kg/s", "lbm/h", "lbm/min", "lbm/s"]
flow_v_units = ["m³/h", "m³/min", "m³/s"]
flow_units = flow_m_units + flow_v_units
pressure_units = ["bar", "kgf/cm²", "barg", "Pa", "kPa", "MPa", "psi", "mmH2O"]
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
    st.markdown(
        """
        <style>
        .st-key-gas_selection_container div[data-testid="stExpanderDetails"] {
            overflow-x: auto !important;
        }
        .st-key-gas_selection_container div[data-testid="stExpanderDetails"] div[data-testid="stHorizontalBlock"] {
            min-width: 1200px !important;
            flex-wrap: nowrap !important;
            flex-direction: row !important;
        }
        .st-key-gas_selection_container div[data-testid="stExpanderDetails"] div[data-testid="column"] {
            width: calc(16.6666% - 1rem) !important;
            flex: 1 1 calc(16.6666% - 1rem) !important;
            min-width: calc(16.6666% - 1rem) !important;
        }
        .st-key-gas_selection_container div[data-testid="stExpanderDetails"] div[data-testid="stColumn"] {
            width: calc(16.6666% - 1rem) !important;
            flex: 1 1 calc(16.6666% - 1rem) !important;
            min-width: calc(16.6666% - 1rem) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="gas_selection_container"):
        with st.form(key="form_gas_selection", enter_to_submit=False, border=False):
            with st.expander(
                "Gas Selection", expanded=st.session_state.expander_state
            ):
                gas_compositions_table = {}
                gas_columns = st.columns(6)
                for i, gas_column in enumerate(gas_columns):
                    gas_compositions_table[f"gas_{i}"] = {}

                    gas_compositions_table[f"gas_{i}"][
                        "name"
                    ] = gas_column.text_input(
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
                                            "component": st.session_state[key][
                                                f"gas_{i}"
                                            ][column],
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
                            gas_compositions_table[f"gas_{i}"][
                                f"{column}_{j}"
                            ] = value

                submit_composition = st.form_submit_button(
                    "Submit", type="primary"
                )

                if (
                    "gas_compositions_table" not in st.session_state
                    or submit_composition
                ):
                    st.session_state[
                        "gas_compositions_table"
                    ] = gas_compositions_table

    return gas_compositions_table


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


def build_fluid_list():
    """Build sorted list of available fluid names for selection widgets.

    Returns
    -------
    fluid_list : list of str
        Sorted list with an empty string at the start.
    """
    fluid_list = []
    for fluid in ccp.fluid_list.keys():
        fluid_list.append(fluid.lower())
        for possible_name in ccp.fluid_list[fluid].possible_names:
            if possible_name != fluid.lower():
                fluid_list.append(possible_name)
    fluid_list = sorted(fluid_list)
    fluid_list.insert(0, "")
    return fluid_list


# ---------------------------------------------------------------------------
# PI data utilities
# ---------------------------------------------------------------------------


def build_pi_query(tag_mappings):
    """Build PI tag list and column rename map from tag_mappings.

    Parameters
    ----------
    tag_mappings : dict
        Dictionary with tag configuration from session state.

    Returns
    -------
    tags_list : list of str
        Unique PI tag name strings to query.
    rename_map : dict
        Mapping from PI tag name to primary ccp internal column name.
    alias_map : dict
        Mapping from additional ccp internal column names to their primary
        column names when multiple fields are configured with the same PI tag.
    """
    key_to_col = {
        "suc_p_tag": "ps",
        "suc_p_tag_2": "ps_2",
        "suc_T_tag": "Ts",
        "suc_T_tag_2": "Ts_2",
        "disch_p_tag": "pd",
        "disch_p_tag_2": "pd_2",
        "disch_T_tag": "Td",
        "disch_T_tag_2": "Td_2",
        "speed_tag": "speed",
        "speed_tag_2": "speed_2",
        "flow_tag": "flow_v",
        "flow_tag_2": "flow_v_2",
        "delta_p_tag": "delta_p",
        "delta_p_tag_2": "delta_p_2",
        "p_downstream_tag": "p_downstream",
        "p_downstream_tag_2": "p_downstream_2",
    }

    tags_list = []
    rename_map = {}
    alias_map = {}

    for key, col_name in key_to_col.items():
        tag_name = tag_mappings.get(key, "")
        if tag_name:
            if tag_name not in tags_list:
                tags_list.append(tag_name)

            existing_col = rename_map.get(tag_name)
            if existing_col is None:
                rename_map[tag_name] = col_name
            elif existing_col != col_name:
                alias_map[col_name] = existing_col

    fluid_tags = tag_mappings.get("fluid_tags", {})
    for component_name, tag_name in fluid_tags.items():
        if tag_name:
            if tag_name not in tags_list:
                tags_list.append(tag_name)

            col_name = f"fluid_{component_name}"
            existing_col = rename_map.get(tag_name)
            if existing_col is None:
                rename_map[tag_name] = col_name
            elif existing_col != col_name:
                alias_map[col_name] = existing_col

    return tags_list, rename_map, alias_map


def format_pi_time(dt):
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


def apply_fluid_unit_conversions(df, tag_mappings):
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


def sanitize_pi_dataframe(df):
    """Clean a raw PI DataFrame for use with ccp.Evaluation.

    PI Web API may return dict objects for digital/enumerated tags or when
    instrument errors occur.  These are detected and the affected rows are
    dropped so that downstream calculations only see valid numeric data.

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
    error_columns = {}
    for col in df.columns:
        if df[col].dtype == object:
            is_dict_mask = df[col].apply(lambda v: isinstance(v, dict))
            if is_dict_mask.any():
                n_dicts = is_dict_mask.sum()
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
        for col, info in error_columns.items():
            print(
                f"[WARNING] Column '{col}': {info['count']}/{info['total']} rows "
                f"contain PI system/error values (e.g. {info['sample']}). "
                f"These rows will be dropped."
            )
        dict_row_mask = pd.Series(False, index=df.index)
        for col in error_columns:
            dict_row_mask |= df[col].apply(lambda v: isinstance(v, dict))
        df = df[~dict_row_mask].copy()

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _frozen_series_mask(series, min_points=10, min_seconds=4500):
    """Return mask for samples that belong to frozen-value runs."""
    s = series.copy()
    valid = s.notna()
    if not valid.any():
        return pd.Series(False, index=series.index)

    group_id = s.ne(s.shift()).cumsum()
    group_size = s.groupby(group_id).transform("size")
    frozen_by_points = group_size >= min_points

    frozen_by_time = pd.Series(False, index=series.index)
    if isinstance(series.index, pd.DatetimeIndex):
        for _, idx_values in series.groupby(group_id).groups.items():
            idx_values = list(idx_values)
            if len(idx_values) < 2:
                continue
            duration = (idx_values[-1] - idx_values[0]).total_seconds()
            if duration > min_seconds:
                frozen_by_time.loc[idx_values] = True

    return valid & (frozen_by_points | frozen_by_time)


def _convert_series_unit(values, from_unit, to_unit):
    """Convert numeric series values from one unit to another using pint."""
    if from_unit == to_unit:
        return values
    return values.apply(lambda v: Q_(v, from_unit).to(to_unit).m)


def merge_redundant_parameter_tags(df, tag_mappings):
    """Merge optional secondary tags into primary process columns.

    A value is considered valid when it is numeric, non-zero, and not frozen.
    Frozen means same value for more than 4500 s or at least 10 measurements.
    """
    parameter_map = [
        ("ps", "suc_p_tag", "suc_p_tag_2", "suc_p_unit", "suc_p_unit_2"),
        ("Ts", "suc_T_tag", "suc_T_tag_2", "suc_T_unit", "suc_T_unit_2"),
        ("pd", "disch_p_tag", "disch_p_tag_2", "disch_p_unit", "disch_p_unit_2"),
        ("Td", "disch_T_tag", "disch_T_tag_2", "disch_T_unit", "disch_T_unit_2"),
        ("speed", "speed_tag", "speed_tag_2", "speed_unit", "speed_unit_2"),
        ("flow_v", "flow_tag", "flow_tag_2", "flow_unit", "flow_unit_2"),
        ("delta_p", "delta_p_tag", "delta_p_tag_2", "delta_p_unit", "delta_p_unit_2"),
        (
            "p_downstream",
            "p_downstream_tag",
            "p_downstream_tag_2",
            "p_downstream_unit",
            "p_downstream_unit_2",
        ),
    ]

    for col, tag1_key, tag2_key, unit1_key, unit2_key in parameter_map:
        tag2 = tag_mappings.get(tag2_key, "")
        col2 = f"{col}_2"

        if col not in df.columns and col2 in df.columns:
            df[col] = df[col2]

        if col not in df.columns:
            continue

        s1 = pd.to_numeric(df[col], errors="coerce")
        valid_1 = s1.notna() & (s1 != 0) & ~_frozen_series_mask(s1)
        s1_valid = s1.where(valid_1)

        if tag2 and col2 in df.columns:
            s2 = pd.to_numeric(df[col2], errors="coerce")
            valid_2 = s2.notna() & (s2 != 0) & ~_frozen_series_mask(s2)
            s2_valid = s2.where(valid_2)

            unit1 = tag_mappings.get(unit1_key)
            unit2 = tag_mappings.get(unit2_key, unit1)
            if unit1 and unit2:
                try:
                    s2_valid = _convert_series_unit(s2_valid, unit2, unit1)
                except Exception as exc:
                    print(
                        f"[WARNING] Failed unit conversion for '{col}' secondary "
                        f"tag ({unit2} -> {unit1}): {exc}"
                    )
                    s2_valid = pd.Series(np.nan, index=s2_valid.index)

            merged = s1_valid.copy()
            both_valid = s1_valid.notna() & s2_valid.notna()
            only_second_valid = s1_valid.isna() & s2_valid.notna()
            merged[both_valid] = (s1_valid[both_valid] + s2_valid[both_valid]) / 2.0
            merged[only_second_valid] = s2_valid[only_second_valid]
            df[col] = merged
        else:
            df[col] = s1_valid

        if col2 in df.columns:
            df = df.drop(columns=[col2])

    return df


def fetch_pi_data(tag_mappings, start_time=None, end_time=None, testing=False):
    """Fetch historical PI data for a time range.

    Parameters
    ----------
    tag_mappings : dict
        Dictionary with tag mappings (used to determine which file to load).
    start_time : datetime, optional
        Start time from which to fetch data.
    end_time : datetime, optional
        End time up to which to fetch data.  Defaults to ``datetime.now()``.
    testing : bool, optional
        If True, returns complete test dataframe from parquet files.

    Returns
    -------
    pd.DataFrame
        DataFrame with data from start_time to end_time.
    """
    if testing:
        data_path = Path(ccp.__file__).parent / "tests/data"

        if tag_mappings.get("delta_p_tag"):
            df = pd.read_parquet(data_path / "data_delta_p.parquet")
        else:
            df = pd.read_parquet(data_path / "data.parquet")

        return df
    else:
        from pandaspi import SessionWeb

        tags_list, rename_map, alias_map = build_pi_query(tag_mappings)
        if not tags_list:
            raise ValueError("No PI tags configured. Please fill in the tag names.")

        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)

        print(
            f"[fetch_pi_data] tags={tags_list}, "
            f"time_range=({format_pi_time(start_time)}, {format_pi_time(end_time)})"
        )
        session = SessionWeb(
            server_name=tag_mappings.get("pi_server_name", ""),
            login=tag_mappings.get("pi_login"),
            tags=tags_list,
            time_range=(format_pi_time(start_time), format_pi_time(end_time)),
            time_span="450s",
            authentication=tag_mappings.get("pi_auth_method", "kerberos"),
        )

        print(f"[fetch_pi_data] raw PI DataFrame:\n{session.df}")
        print(f"[fetch_pi_data] raw dtypes:\n{session.df.dtypes}")
        df = session.df.rename(columns=rename_map)
        df = sanitize_pi_dataframe(df)
        for alias_col, source_col in alias_map.items():
            if source_col in df.columns:
                df[alias_col] = df[source_col]
        df = merge_redundant_parameter_tags(df, tag_mappings)
        print(f"[fetch_pi_data] sanitized DataFrame:\n{df}")
        print(f"[fetch_pi_data] sanitized dtypes:\n{df.dtypes}")
        df = apply_fluid_unit_conversions(df, tag_mappings)
        return df


# ---------------------------------------------------------------------------
# Shared UI sections
# ---------------------------------------------------------------------------


def gas_selection_ui():
    """Render Gas Selection UI and return relevant data.

    Returns
    -------
    fluid_list : list of str
        Sorted list of available fluids.
    gas_compositions_table : dict
        Gas compositions table from the form.
    """
    fluid_list = build_fluid_list()
    gas_compositions_table = gas_selection_form(fluid_list, default_components)
    return fluid_list, gas_compositions_table


def design_cases_section():
    """Render Design Cases Suction Conditions expander."""
    with st.expander(
        "Design Cases Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Design Suction Conditions")
        st.markdown("Define the suction conditions for each design case (A, B, C, D).")

        gas_options = [st.session_state[f"gas_{i}"] for i in range(6)]

        header_cols = st.columns(6)
        header_cols[0].markdown("**Parameter**")
        header_cols[1].markdown("**Unit**")
        header_cols[2].markdown("**Case A**")
        header_cols[3].markdown("**Case B**")
        header_cols[4].markdown("**Case C**")
        header_cols[5].markdown("**Case D**")

        gas_row = st.columns(6)
        gas_row[0].markdown("Gas Selection")
        gas_row[1].markdown("")
        for idx, case in enumerate(["A", "B", "C", "D"]):
            with gas_row[idx + 2]:
                st.selectbox(
                    f"Gas Case {case}",
                    options=gas_options,
                    key=f"gas_case_{case}",
                    label_visibility="collapsed",
                )

        p_row = st.columns(6)
        p_row[0].markdown("Suction Pressure")
        with p_row[1]:
            st.selectbox(
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

        T_row = st.columns(6)
        T_row[0].markdown("Suction Temperature")
        with T_row[1]:
            st.selectbox(
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


def curves_upload_section():
    """Render Performance Curves Upload expander."""
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

        design_suc_p_unit = st.session_state.get("design_suc_p_unit", "bar")
        design_suc_T_unit = st.session_state.get("design_suc_T_unit", "degC")

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

                    for csv_file in [
                        st.session_state[f"curves_file_1_case_{case}"],
                        st.session_state[f"curves_file_2_case_{case}"],
                    ]:
                        file_path = temp_path / csv_file["name"]
                        with open(file_path, "wb") as f:
                            f.write(csv_file["content"])

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

                    suc_p = st.session_state.get(f"suc_p_case_{case}", 0)
                    suc_T = st.session_state.get(f"suc_T_case_{case}", 0)

                    if suc_p <= 0 or suc_T <= 0:
                        st.error(
                            f"Please define valid suction conditions for Case {case}"
                        )
                        shutil.rmtree(temp_dir)
                        continue

                    suc_state = ccp.State(
                        p=Q_(suc_p, design_suc_p_unit),
                        T=Q_(suc_T, design_suc_T_unit),
                        fluid=gas_composition,
                    )

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

            if st.session_state.get(f"impeller_case_{case}") is not None:
                imp = st.session_state[f"impeller_case_{case}"]
                st.info(f"Loaded: {len(imp.points)} points, {len(imp.curves)} curves")

            st.markdown("---")


def tags_config_section(fluid_list):
    """Render Tags Configuration expander.

    Parameters
    ----------
    fluid_list : list of str
        List of available fluid names for component selection.
    """
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

        st.caption(
            "Each parameter accepts one or two tags. When both are valid, "
            "tag 2 is converted to unit 1 and values are averaged."
        )

        def dual_tag_input_row(label, tag_key, unit_key, tag_key_2, unit_key_2, units):
            cols = st.columns([2, 1, 2, 1])
            with cols[0]:
                st.text_input(f"{label} Tag 1", key=tag_key)
            with cols[1]:
                st.selectbox("Unit 1", options=units, key=unit_key)
            with cols[2]:
                st.text_input(f"{label} Tag 2", key=tag_key_2)
            with cols[3]:
                st.selectbox("Unit 2", options=units, key=unit_key_2)

        dual_tag_input_row(
            "Suction Pressure",
            "suc_p_tag",
            "suc_p_unit",
            "suc_p_tag_2",
            "suc_p_unit_2",
            pressure_units,
        )
        dual_tag_input_row(
            "Suction Temperature",
            "suc_T_tag",
            "suc_T_unit",
            "suc_T_tag_2",
            "suc_T_unit_2",
            temperature_units,
        )
        dual_tag_input_row(
            "Discharge Pressure",
            "disch_p_tag",
            "disch_p_unit",
            "disch_p_tag_2",
            "disch_p_unit_2",
            pressure_units,
        )
        dual_tag_input_row(
            "Discharge Temperature",
            "disch_T_tag",
            "disch_T_unit",
            "disch_T_tag_2",
            "disch_T_unit_2",
            temperature_units,
        )
        dual_tag_input_row(
            "Speed",
            "speed_tag",
            "speed_unit",
            "speed_tag_2",
            "speed_unit_2",
            speed_units,
        )

        if st.session_state.get("flow_method", "Direct") == "Direct":
            row4 = st.columns([2, 1])
            with row4[0]:
                flow_method = st.radio(
                    "Flow Measurement Method",
                    options=["Direct", "Orifice"],
                    key="flow_method",
                    horizontal=True,
                )
            dual_tag_input_row(
                "Flow",
                "flow_tag",
                "flow_unit",
                "flow_tag_2",
                "flow_unit_2",
                flow_units,
            )
        else:
            row4 = st.columns([2, 1])
            with row4[0]:
                flow_method = st.radio(
                    "Flow Measurement Method",
                    options=["Direct", "Orifice"],
                    key="flow_method",
                    horizontal=True,
                )
            dual_tag_input_row(
                "Delta P",
                "delta_p_tag",
                "delta_p_unit",
                "delta_p_tag_2",
                "delta_p_unit_2",
                pressure_units,
            )
            dual_tag_input_row(
                "Downstream P",
                "p_downstream_tag",
                "p_downstream_unit",
                "p_downstream_tag_2",
                "p_downstream_unit_2",
                pressure_units,
            )

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


# ---------------------------------------------------------------------------
# Shared builder functions
# ---------------------------------------------------------------------------


def get_available_impellers():
    """Return available design cases and their impeller objects.

    Returns
    -------
    available_cases : list of str
        Case letters (e.g. ``["A", "C"]``) that have loaded impellers.
    impellers_list : list of ccp.Impeller
        Corresponding Impeller objects.
    """
    available_cases = []
    impellers_list = []
    for case in ["A", "B", "C", "D"]:
        if st.session_state.get(f"impeller_case_{case}") is not None:
            available_cases.append(case)
            impellers_list.append(st.session_state[f"impeller_case_{case}"])
    return available_cases, impellers_list


def get_operation_fluid(available_cases):
    """Get fluid composition based on fluid_source setting.

    Parameters
    ----------
    available_cases : list of str
        Available design case letters.

    Returns
    -------
    operation_fluid : dict or None
        Fluid composition dict, or None if using component tags.
    """
    fluid_source = st.session_state.get("fluid_source", "Fixed Operation Fluid")
    if fluid_source == "Inform Component Tags":
        return None

    gas_name = st.session_state.get(f"gas_case_{available_cases[0]}")
    if "gas_compositions_table" in st.session_state:
        return get_gas_composition(
            gas_name,
            st.session_state["gas_compositions_table"],
            default_components,
        )
    return None


def build_tag_mappings():
    """Build tag_mappings dict from session state.

    Returns
    -------
    tag_mappings : dict
        Dictionary with PI tag names and configuration.
    """
    tag_mappings = {
        "pi_server_name": st.session_state.get("pi_server_name", ""),
        "pi_auth_method": st.session_state.get("pi_auth_method", "kerberos"),
        "suc_p_tag": st.session_state.get("suc_p_tag", ""),
        "suc_p_tag_2": st.session_state.get("suc_p_tag_2", ""),
        "suc_p_unit": st.session_state.get("suc_p_unit", "bar"),
        "suc_p_unit_2": st.session_state.get("suc_p_unit_2", "bar"),
        "suc_T_tag": st.session_state.get("suc_T_tag", ""),
        "suc_T_tag_2": st.session_state.get("suc_T_tag_2", ""),
        "suc_T_unit": st.session_state.get("suc_T_unit", "degC"),
        "suc_T_unit_2": st.session_state.get("suc_T_unit_2", "degC"),
        "disch_p_tag": st.session_state.get("disch_p_tag", ""),
        "disch_p_tag_2": st.session_state.get("disch_p_tag_2", ""),
        "disch_p_unit": st.session_state.get("disch_p_unit", "bar"),
        "disch_p_unit_2": st.session_state.get("disch_p_unit_2", "bar"),
        "disch_T_tag": st.session_state.get("disch_T_tag", ""),
        "disch_T_tag_2": st.session_state.get("disch_T_tag_2", ""),
        "disch_T_unit": st.session_state.get("disch_T_unit", "degC"),
        "disch_T_unit_2": st.session_state.get("disch_T_unit_2", "degC"),
        "speed_tag": st.session_state.get("speed_tag", ""),
        "speed_tag_2": st.session_state.get("speed_tag_2", ""),
        "speed_unit": st.session_state.get("speed_unit", "rpm"),
        "speed_unit_2": st.session_state.get("speed_unit_2", "rpm"),
    }

    if tag_mappings["pi_auth_method"] == "basic":
        username = st.session_state.get("pi_username", "")
        password = st.session_state.get("pi_password", "")
        tag_mappings["pi_login"] = (username, password)
    else:
        tag_mappings["pi_login"] = None

    flow_method = st.session_state.get("flow_method", "Direct")
    if flow_method == "Direct":
        tag_mappings["flow_tag"] = st.session_state.get("flow_tag", "")
        tag_mappings["flow_tag_2"] = st.session_state.get("flow_tag_2", "")
        tag_mappings["flow_unit"] = st.session_state.get("flow_unit", "m³/h")
        tag_mappings["flow_unit_2"] = st.session_state.get("flow_unit_2", "m³/h")
    else:
        tag_mappings["delta_p_tag"] = st.session_state.get("delta_p_tag", "")
        tag_mappings["delta_p_tag_2"] = st.session_state.get("delta_p_tag_2", "")
        tag_mappings["delta_p_unit"] = st.session_state.get("delta_p_unit", "bar")
        tag_mappings["delta_p_unit_2"] = st.session_state.get("delta_p_unit_2", "bar")
        tag_mappings["p_downstream_tag"] = st.session_state.get(
            "p_downstream_tag", ""
        )
        tag_mappings["p_downstream_tag_2"] = st.session_state.get(
            "p_downstream_tag_2", ""
        )
        tag_mappings["p_downstream_unit"] = st.session_state.get(
            "p_downstream_unit", "bar"
        )
        tag_mappings["p_downstream_unit_2"] = st.session_state.get(
            "p_downstream_unit_2", "bar"
        )

    fluid_source = st.session_state.get("fluid_source", "Fixed Operation Fluid")
    if fluid_source == "Inform Component Tags":
        fluid_tags = {}
        fluid_units_map = {}
        for i in range(9):
            comp = st.session_state.get(f"fluid_component_{i}", "")
            tag = st.session_state.get(f"fluid_tag_{i}", "")
            unit = st.session_state.get(f"fluid_unit_{i}", "mol_frac")
            if comp and tag:
                fluid_tags[comp] = tag
                fluid_units_map[comp] = unit
        tag_mappings["fluid_tags"] = fluid_tags
        tag_mappings["fluid_units"] = fluid_units_map

    return tag_mappings


def build_data_units(tag_mappings):
    """Build data_units dict from session state.

    Parameters
    ----------
    tag_mappings : dict
        Tag mappings (needed for fluid_units).

    Returns
    -------
    data_units : dict
        Dictionary mapping column names to unit strings.
    """
    data_units = {
        "ps": st.session_state.get("suc_p_unit", "bar"),
        "Ts": st.session_state.get("suc_T_unit", "degC"),
        "pd": st.session_state.get("disch_p_unit", "bar"),
        "Td": st.session_state.get("disch_T_unit", "degC"),
        "speed": st.session_state.get("speed_unit", "rpm"),
    }

    fluid_units_map = tag_mappings.get("fluid_units", {})
    for comp_name, unit in fluid_units_map.items():
        col = f"fluid_{comp_name}"
        if unit == "ppm":
            data_units[col] = "ppm"

    flow_method = st.session_state.get("flow_method", "Direct")
    if flow_method == "Direct":
        data_units["flow_v"] = st.session_state.get("flow_unit", "m³/h")
    else:
        data_units["delta_p"] = st.session_state.get("delta_p_unit", "bar")
        data_units["p_downstream"] = st.session_state.get(
            "p_downstream_unit", "bar"
        )

    return data_units


def build_evaluation_kwargs(
    tag_mappings, data_units, impellers_list, df_raw, testing=False
):
    """Build kwargs dict for ccp.Evaluation constructor.

    Parameters
    ----------
    tag_mappings : dict
        Tag mappings.
    data_units : dict
        Data units.
    impellers_list : list
        List of impeller objects.
    df_raw : pd.DataFrame
        Raw data.
    testing : bool
        Testing mode flag.

    Returns
    -------
    evaluation_kwargs : dict
        Keyword arguments for ``ccp.Evaluation()``.
    """
    available_cases, _ = get_available_impellers()
    operation_fluid = get_operation_fluid(available_cases)

    evaluation_kwargs = {
        "data": df_raw,
        "operation_fluid": operation_fluid,
        "data_units": data_units,
        "impellers": impellers_list,
        "n_clusters": len(impellers_list),
        "calculate_points": False,
        "parallel": not testing,
        "temperature_fluctuation": st.session_state.get(
            "temperature_fluctuation", 0.5
        ),
        "pressure_fluctuation": st.session_state.get("pressure_fluctuation", 2.0),
        "speed_fluctuation": st.session_state.get("speed_fluctuation", 0.5),
    }

    flow_method = st.session_state.get("flow_method", "Direct")
    if flow_method != "Direct":
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

    return evaluation_kwargs


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
