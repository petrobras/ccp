"""Module to keep everything that is common to ccp_app_straight_through and ccp_app_back_to_back."""

import io
import pandas as pd
import toml
from packaging.version import Version
from ccp import Q_
import numpy as np

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


# @check_units
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
