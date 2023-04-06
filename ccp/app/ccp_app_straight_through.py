import ccp
import streamlit as st
import json
import pandas as pd
import pickle
import base64
import zipfile
import time
from ccp.compressor import Point1Sec, StraightThrough
from ccp.config.utilities import r_getattr
from pathlib import Path

Q_ = ccp.Q_

assets = Path(__file__).parent / "assets"
ccp_ico = assets / "favicon.ico"
ccp_logo = assets / "ccp.png"


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

# remove streamlit menu
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid=stVerticalBlock]{
    gap: 0.75rem;
}
[data-testid=stHorizontalBlock]{
    gap: 0.5rem;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

title_alignment = """
<p style="text-align: center; font-weight: bold; font-size:20px;">
 ccp 
</p>
"""
st.sidebar.markdown(title_alignment, unsafe_allow_html=True)
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
    for curve in ["head", "power", "eff", "discharge_pressure"]:
        if f"fig_{curve}" not in st.session_state:
            st.session_state[f"fig_{curve}"] = ""


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
            for name in my_zip.namelist():
                if name.endswith(".json"):
                    session_state_data = json.loads(my_zip.read(name))

            # extract figures and straight_through objects
            for name in my_zip.namelist():
                if name.endswith(".png"):
                    session_state_data[name.split(".")[0]] = my_zip.read(name)
                elif name.endswith(".pkl"):
                    session_state_data[name.split(".")[0]] = pickle.loads(
                        my_zip.read(name)
                    )

        session_state_data_copy = session_state_data.copy()
        # remove keys that cannot be set with st.session_state.update
        for key in session_state_data.keys():
            if key.startswith(("FormSubmitter", "my_form", "uploaded")):
                del session_state_data_copy[key]
        st.session_state.update(session_state_data_copy)
        st.session_state.session_name = file.name.replace(".ccp", "")
        st.experimental_rerun()

    if save_button:
        session_state_dict = dict(st.session_state)

        # create a zip file to add the data to
        file_name = f"{st.session_state.session_name}.ccp"
        session_state_dict_copy = session_state_dict.copy()
        with zipfile.ZipFile(file_name, "w") as my_zip:
            # first save figures
            for key, value in session_state_dict.items():
                if isinstance(
                    value, (bytes, st.runtime.uploaded_file_manager.UploadedFile)
                ):
                    if key.startswith("fig"):
                        my_zip.writestr(f"{key}.png", value)
                    del session_state_dict_copy[key]
                if isinstance(value, StraightThrough):
                    my_zip.writestr(f"{key}.pkl", pickle.dumps(value))
                    del session_state_dict_copy[key]
            # then save the rest of the session state
            session_state_json = json.dumps(session_state_dict_copy)
            my_zip.writestr("session_state.json", session_state_json)

        st.download_button(
            label="💾 Save As",
            data=session_state_json,
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

with st.expander("Gas Selection"):
    gas_compositions_table = {}
    gas_columns = st.columns(5)
    for i, gas_column in enumerate(gas_columns):
        gas_compositions_table[f"gas_{i}"] = {}

        gas_compositions_table[f"gas_{i}"]["name"] = gas_column.text_input(
            f"Gas Name",
            value=f"gas_{i}",
            key=f"gas_{i}",
        )
        component, molar_fraction = gas_column.columns([2, 1])
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
            "nitrogen",
            "h2s",
            "co2",
            "h2o",
        ]
        for j, default_component in enumerate(default_components):
            gas_compositions_table[f"gas_{i}"][f"component_{j}"] = component.selectbox(
                "Component",
                options=fluid_list,
                index=fluid_list.index(default_component),
                key=f"gas_{i}_component_{j}",
                label_visibility="collapsed",
            )
            gas_compositions_table[f"gas_{i}"][
                f"molar_fraction_{j}"
            ] = molar_fraction.text_input(
                "Molar Fraction",
                value="0",
                key=f"gas_{i}_molar_fraction_{j}",
                label_visibility="collapsed",
            )


# add container with 4 columns and 2 rows
with st.sidebar.expander("⚙️ Options"):
    reynolds_correction = st.checkbox("Reynolds Correction", value=True)
    casing_heat_loss = st.checkbox("Casing Heat Loss", value=True)
    calculate_leakages = st.checkbox("Calculate Leakages", value=True)
    seal_gas_flow = st.checkbox("Seal Gas Flow", value=True)
    variable_speed = st.checkbox("Variable Speed", value=True)

# parameters with name and label
flow_m_units = ["kg/h", "lbm/h", "kg/s", "lbm/s"]
pressure_units = ["bar", "psi", "Pa", "kPa", "MPa"]
temperature_units = ["degK", "degC", "degF", "degR"]
speed_units = ["rpm", "Hz"]
length_units = ["m", "mm", "ft", "in"]

parameters_map = {
    "flow": {
        "label": "Flow",
        "units": ["m³/h", "m³/s", "kg/h", "lbm/h", "kg/s", "lbm/s"],
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
    },
    "speed": {
        "label": "Speed",
        "units": speed_units,
    },
    "balance_line_flow_m": {
        "label": "Balance Line Flow",
        "units": flow_m_units,
    },
    "seal_gas_flow_m": {
        "label": "Seal Gas Flow",
        "units": flow_m_units,
    },
    "seal_gas_temperature": {
        "label": "Seal Gas Temperature",
        "units": temperature_units,
    },
    "head": {
        "label": "Head",
        "units": ["kJ/kg", "J/kg", "m*g0", "ft"],
    },
    "eff": {
        "label": "Efficiency",
        "units": [""],
    },
    "power": {
        "label": "Gas Power",
        "units": ["kW", "hp", "W", "Btu/h", "MW"],
    },
    "b": {
        "label": "First Impeller Width",
        "units": ["mm", "m", "ft", "in"],
    },
    "D": {
        "label": "First Impeller Diameter",
        "units": ["mm", "m", "ft", "in"],
    },
    "surface_roughness": {
        "label": "Surface Roughness",
        "units": ["mm", "m", "ft", "in"],
    },
    "casing_area": {
        "label": "Casing Area",
        "units": ["m²", "mm²", "ft²", "in²"],
    },
}

# add dict to store the values for guarantee and test points
# in the parameters_map
number_of_test_points = 6
points_list = ["point_guarantee"] + [
    f"point_{i}" for i in range(1, number_of_test_points + 1)
]
for parameter in parameters_map:
    parameters_map[parameter]["points"] = {
        "data_sheet_units": None,
        "test_units": None,
    }
    for point in points_list:
        parameters_map[parameter]["points"][point] = {
            "value": None,
        }

with st.expander("Data Sheet"):
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
        st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_columns)
    ]  ##############################

    # fill the gas selection dropdowns with the gases selected
    def get_index_selected_gas(gas_name):
        try:
            index_gas_name = gas_options.index(st.session_state[gas_name])
        except KeyError:
            index_gas_name = 0
        return index_gas_name

    gas_name_point_guarantee = points_gas_columns[2].selectbox(
        "gas_point_guarantee",
        options=gas_options,
        label_visibility="collapsed",
        index=get_index_selected_gas("gas_point_guarantee"),
    )

    # build one container with 8 columns for each parameter
    for parameter in [
        "flow",
        "suction_pressure",
        "suction_temperature",
        "discharge_pressure",
        "discharge_temperature",
        "power",
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

        parameters_col.markdown(f"{parameters_map[parameter]['label']}")

        parameters_map[parameter]["points"]["data_sheet_units"] = units_col.selectbox(
            f"{parameter} units",
            options=parameters_map[parameter]["units"],
            key=f"{parameter}_units_point_guarantee",  #############################
            label_visibility="collapsed",
        )
        parameters_map[parameter]["points"]["point_guarantee"][
            "value"
        ] = values_col.text_input(
            f"{parameter} value.",
            key=f"{parameter}_point_guarantee",
            label_visibility="collapsed",
        )


with st.expander("Curves"):
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
                plot_limits[curve][f"{axis}"][
                    "lower_limit"
                ] = lower_value_col.text_input(
                    f"Lower limit",
                    key=f"{axis}_{curve}_lower",
                    label_visibility="collapsed",
                )
                plot_limits[curve][f"{axis}"][
                    "upper_limit"
                ] = upper_value_col.text_input(
                    f"Upper limit",
                    key=f"{axis}_{curve}_upper",
                    label_visibility="collapsed",
                )
                if axis == "x":
                    plot_limits[curve][f"{axis}"]["units"] = units_col.selectbox(
                        f"{parameter} units",
                        options=parameters_map["flow"]["units"],
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

with st.expander("Test Data"):

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
                st.session_state[f"gas_{i}"] for i, gas in enumerate(gas_columns)
            ]
            col.selectbox(
                f"gas_point_{i - 1}",
                options=gas_options,
                label_visibility="collapsed",
                key=f"gas_point_{i - 1}",
                index=get_index_selected_gas(f"gas_point_{i - 1}"),
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
    ]:
        parameter_container = st.container()
        parameter_columns = parameter_container.columns(number_of_columns, gap="small")
        for i, col in enumerate(parameter_columns):
            if i == 0:
                col.markdown(f"{parameters_map[parameter]['label']}")
            elif i == 1:
                parameters_map[parameter]["points"]["test_units"] = col.selectbox(
                    f"{parameter} units",
                    options=parameters_map[parameter]["units"],
                    key=f"{parameter}_units",
                    label_visibility="collapsed",
                )
            else:
                parameters_map[parameter]["points"][f"point_{i - 1}"][
                    "value"
                ] = col.text_input(
                    f"{parameter} value.",
                    key=f"{parameter}_point_{i - 1}",
                    label_visibility="collapsed",
                )

# add calculate button
straight_through = None

with st.container():
    calculate_col, calculate_speed_col = st.columns([1, 1])
    calculate_button = calculate_col.button(
        "Calculate",
        type="primary",
        use_container_width=True,
        # help="Calculate results using the data sheet speed.",
        # for now help breaks the button width. See streamlit issue #6161
    )
    calculate_speed_button = calculate_speed_col.button(
        "Calculate Speed",
        type="primary",
        use_container_width=True,
        # help="Calculate speed to match the discharge pressure.",
    )


def get_gas_composition(gas_name):
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
            for i in range(len(default_components) - 1):
                component = gas_compositions_table[gas][f"component_{i}"]
                molar_fraction = float(
                    gas_compositions_table[gas][f"molar_fraction_{i}"]
                )
                if molar_fraction != 0:
                    gas_composition[component] = molar_fraction

    return gas_composition


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
        gas_name_point_guarantee
    )

    # to get data sheet units we use parameters_map[parameter]["selected_units"]
    if (
        Q_(0, parameters_map["flow"]["points"]["data_sheet_units"]).dimensionality
        == "[mass] / [time]"
    ):
        kwargs_guarantee["flow_m"] = Q_(
            float(st.session_state[f"flow_point_guarantee"]),
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
            float(st.session_state[f"suction_temperature_point_guarantee"]),
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
        float(st.session_state[f"speed_point_guarantee"]),
        parameters_map["speed"]["points"]["data_sheet_units"],
    )
    kwargs_guarantee["b"] = Q_(
        float(st.session_state[f"b_point_guarantee"]),
        parameters_map["b"]["points"]["data_sheet_units"],
    )
    kwargs_guarantee["D"] = Q_(
        float(st.session_state[f"D_point_guarantee"]),
        parameters_map["D"]["points"]["data_sheet_units"],
    )

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
                fluid=get_gas_composition(st.session_state[f"gas_point_{i}"]),
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
                fluid=get_gas_composition(st.session_state[f"gas_point_{i}"]),
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
                        parameters_map["balance_line_flow_m"]["points"]["test_units"],
                    )
                else:
                    kwargs["balance_line_flow_m"] = None
                if st.session_state[f"seal_gas_flow_m_point_{i}"] != "":
                    kwargs["seal_gas_flow_m"] = Q_(
                        float(st.session_state[f"seal_gas_flow_m_point_{i}"]),
                        parameters_map["seal_gas_flow_m"]["points"]["test_units"],
                    )
                else:
                    kwargs["seal_gas_flow_m"] = Q_(
                        0, parameters_map["seal_gas_flow_m"]["points"]["test_units"]
                    )
                if st.session_state[f"seal_gas_temperature_point_{i}"] != "":
                    kwargs["seal_gas_temperature"] = Q_(
                        float(st.session_state[f"seal_gas_temperature_point_{i}"]),
                        parameters_map["seal_gas_temperature"]["points"]["test_units"],
                    )
                else:
                    kwargs["seal_gas_temperature"] = Q_(
                        0,
                        parameters_map["seal_gas_temperature"]["points"]["test_units"],
                    )
            else:
                pass
                # TODO implement calculation without leakages

            kwargs["b"] = Q_(
                float(st.session_state[f"b_point_guarantee"]),
                parameters_map["b"]["points"]["data_sheet_units"],
            )
            kwargs["D"] = Q_(
                float(st.session_state[f"D_point_guarantee"]),
                parameters_map["D"]["points"]["data_sheet_units"],
            )
            kwargs["casing_area"] = Q_(
                float(st.session_state[f"casing_area_point_guarantee"]),
                parameters_map["casing_area"]["points"]["data_sheet_units"],
            )
            kwargs["surface_roughness"] = Q_(
                float(st.session_state[f"surface_roughness_point_guarantee"]),
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
        _t = "\u209C"
        _sp = "\u209B\u209A"
        conv = "\u1D9C" + "\u1D52" + "\u207F" + "\u1D5B"

        results = {}

        if straight_through:
            # create interpolated point with point method
            point_interpolated = getattr(straight_through, f"point")(
                flow_v=getattr(straight_through, f"guarantee_point").flow_v,
                speed=straight_through.speed,
            )

            results[f"φ{_t}"] = [
                round(p.phi.m, 5) for p in getattr(straight_through, f"test_points")
            ]
            results[f"φ{_t} / φ{_sp}"] = [
                round(
                    p.phi.m / getattr(straight_through, f"guarantee_point").phi.m,
                    5,
                )
                for p in getattr(straight_through, f"test_points")
            ]
            results["vi / vd"] = [
                round(p.volume_ratio.m, 5)
                for p in getattr(straight_through, f"test_points")
            ]
            results[f"(vi/vd){_t}/(vi/vd){_sp}"] = [
                round(
                    p.volume_ratio.m
                    / getattr(straight_through, f"guarantee_point").volume_ratio.m,
                    5,
                )
                for p in getattr(straight_through, f"test_points")
            ]
            results[f"Mach{_t}"] = [
                round(p.mach.m, 5) for p in getattr(straight_through, f"test_points")
            ]
            results[f"Mach{_t} - Mach{_sp}"] = [
                round(
                    p.mach.m - getattr(straight_through, f"guarantee_point").mach.m,
                    5,
                )
                for p in getattr(straight_through, f"test_points")
            ]
            results[f"Re{_t}"] = [
                round(p.reynolds.m, 5)
                for p in getattr(straight_through, f"test_points")
            ]
            results[f"Re{_t} / Re{_sp}"] = [
                round(
                    p.reynolds.m
                    / getattr(straight_through, f"guarantee_point").reynolds.m,
                    5,
                )
                for p in getattr(straight_through, f"test_points")
            ]
            results[f"pd{conv} (bar)"] = [
                round(p.disch.p("bar").m, 5)
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"pd{conv}/pd{_sp}"] = [
                round(
                    p.disch.p("bar").m
                    / getattr(straight_through, f"guarantee_point").disch.p("bar").m,
                    5,
                )
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"Head{_t} (kJ/kg)"] = [
                round(p.head.to("kJ/kg").m, 5)
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"Head{_t}/Head{_sp}"] = [
                round(
                    p.head.to("kJ/kg").m
                    / getattr(straight_through, f"guarantee_point").head.to("kJ/kg").m,
                    5,
                )
                for p in getattr(straight_through, f"test_points")
            ]
            results[f"Head{conv} (kJ/kg)"] = [
                round(p.head.to("kJ/kg").m, 5)
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"Head{conv}/Head{_sp}"] = [
                round(
                    p.head.to("kJ/kg").m
                    / getattr(straight_through, f"guarantee_point").head.to("kJ/kg").m,
                    5,
                )
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"Q{conv} (m3/h)"] = [
                round(p.flow_v.to("m³/h").m, 5)
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"Q{conv}/Q{_sp}"] = [
                round(
                    p.flow_v.to("m³/h").m
                    / getattr(straight_through, f"guarantee_point").flow_v.to("m³/h").m,
                    5,
                )
                for p in getattr(straight_through, f"points_flange_sp")
            ]
            results[f"W{_t} (kW)"] = [
                round(p.power.to("kW").m, 5)
                for p in getattr(straight_through, f"points_rotor_t")
            ]
            results[f"W{_t}/W{_sp}"] = [
                round(
                    p.power.to("kW").m
                    / getattr(straight_through, f"guarantee_point").power.to("kW").m,
                    5,
                )
                for p in getattr(straight_through, f"points_rotor_t")
            ]
            results[f"W{conv} (kW)"] = [
                round(p.power.to("kW").m, 5)
                for p in getattr(straight_through, f"points_rotor_sp")
            ]
            results[f"W{conv}/W{_sp}"] = [
                round(
                    p.power.to("kW").m
                    / getattr(straight_through, f"guarantee_point").power.to("kW").m,
                    5,
                )
                for p in getattr(straight_through, f"points_rotor_sp")
            ]
            results[f"Eff{_t}"] = [
                round(p.eff.m, 5) for p in getattr(straight_through, f"points_flange_t")
            ]
            results[f"Eff{conv}"] = [
                round(p.eff.m, 5)
                for p in getattr(straight_through, f"points_flange_sp")
            ]

            results[f"φ{_t}"].append(round(point_interpolated.phi.m, 5))
            results[f"φ{_t} / φ{_sp}"].append(
                round(
                    point_interpolated.phi.m
                    / getattr(straight_through, f"guarantee_point").phi.m,
                    5,
                )
            )
            results["vi / vd"].append(round(point_interpolated.volume_ratio.m, 5))
            results[f"(vi/vd){_t}/(vi/vd){_sp}"].append(
                round(
                    point_interpolated.volume_ratio.m
                    / getattr(straight_through, f"guarantee_point").volume_ratio.m,
                    5,
                )
            )
            results[f"Mach{_t}"].append(round(point_interpolated.mach.m, 5))
            results[f"Mach{_t} - Mach{_sp}"].append(
                round(
                    point_interpolated.mach.m
                    - getattr(straight_through, f"guarantee_point").mach.m,
                    5,
                )
            )
            results[f"Re{_t}"].append(round(point_interpolated.reynolds.m, 5))
            results[f"Re{_t} / Re{_sp}"].append(
                round(
                    point_interpolated.reynolds.m
                    / getattr(straight_through, f"guarantee_point").reynolds.m,
                    5,
                )
            )
            results[f"pd{conv} (bar)"].append(
                round(point_interpolated.disch.p("bar").m, 5)
            )
            results[f"pd{conv}/pd{_sp}"].append(
                round(
                    point_interpolated.disch.p("bar").m
                    / getattr(straight_through, f"guarantee_point").disch.p("bar").m,
                    5,
                )
            )
            results[f"Head{_t} (kJ/kg)"].append(
                round(point_interpolated.head.to("kJ/kg").m, 5)
            )
            results[f"Head{_t}/Head{_sp}"].append(
                round(
                    point_interpolated.head.to("kJ/kg").m
                    / getattr(straight_through, f"guarantee_point").head.to("kJ/kg").m,
                    5,
                )
            )
            results[f"Head{conv} (kJ/kg)"].append(
                round(point_interpolated.head.to("kJ/kg").m, 5)
            )
            results[f"Head{conv}/Head{_sp}"].append(
                round(
                    point_interpolated.head.to("kJ/kg").m
                    / getattr(straight_through, f"guarantee_point").head.to("kJ/kg").m,
                    5,
                )
            )
            results[f"Q{conv} (m3/h)"].append(
                round(point_interpolated.flow_v.to("m³/h").m, 5)
            )
            results[f"Q{conv}/Q{_sp}"].append(
                round(
                    point_interpolated.flow_v.to("m³/h").m
                    / getattr(straight_through, f"guarantee_point").flow_v.to("m³/h").m,
                    5,
                )
            )
            results[f"W{_t} (kW)"].append(None)
            results[f"W{_t}/W{_sp}"].append(None)
            results[f"W{conv} (kW)"].append(
                round(point_interpolated.power.to("kW").m, 5)
            )
            results[f"W{conv}/W{_sp}"].append(
                round(
                    point_interpolated.power.to("kW").m
                    / Q_(
                        float(st.session_state[f"power_point_guarantee"]),
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
                i: f"Point {i+1}"
                for i in range(len(getattr(straight_through, f"points_flange_t")))
            }
            rename_index[
                len(getattr(straight_through, f"points_flange_t"))
            ] = "Guarantee Point"

            df_results.rename(
                index=rename_index,
                inplace=True,
            )

            def highlight_cell(
                styled_df, df, row_index, col_index, lower_limit, higher_limit
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
                    styled_df = styled_df.applymap(
                        lambda x: "background-color: #C8E6C9" if x == cell_value else ""
                    ).applymap(
                        lambda x: "font-color: #33691E" if x == cell_value else ""
                    )

                else:
                    styled_df = styled_df.applymap(
                        lambda x: "background-color: #FFCDD2" if x == cell_value else ""
                    ).applymap(
                        lambda x: "font-color: #FFCDD2" if x == cell_value else ""
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

            with st.container():
                mach_col, reynolds_col = st.columns(2)
                mach_col.plotly_chart(
                    point_interpolated.plot_mach(), use_container_width=True
                )
                reynolds_col.plotly_chart(
                    point_interpolated.plot_reynolds(), use_container_width=True
                )

            def add_background_image(curve_name=None, fig=None, image=None):
                """Add png file to plot background

                Parameters
                ----------
                curve_name : str
                    The name of the curve to add the background image to.
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
                        x=plot_limits[curve_name]["x"]["lower_limit"],
                        y=plot_limits[curve_name]["y"]["upper_limit"],
                        sizex=float(plot_limits[curve_name]["x"]["upper_limit"])
                        - float(plot_limits[curve_name]["x"]["lower_limit"]),
                        sizey=float(plot_limits[curve_name]["y"]["upper_limit"])
                        - float(plot_limits[curve_name]["y"]["lower_limit"]),
                        sizing="stretch",
                        opacity=0.5,
                        layer="below",
                    )
                )
                return fig

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
                    straight_through,
                    # getattr(straight_through, f"imp_flange_sp"),
                    f"{curve_plot_method}_plot",
                )(
                    **kwargs,
                )
                plots_dict[curve] = r_getattr(
                    point_interpolated, f"{curve_plot_method}_plot"
                )(
                    fig=plots_dict[curve],
                    **kwargs,
                )

                plots_dict[curve].data[0].update(
                    name=f"Converted Curve {straight_through.speed.to('rpm').m:.0f} RPM",
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

                if (
                    st.session_state.get(f"fig_{curve}") is not None
                    and st.session_state.get(f"fig_{curve}") != ""
                ):
                    plots_dict[curve] = add_background_image(
                        curve_name=curve,
                        fig=plots_dict[curve],
                        image=st.session_state[f"fig_{curve}"],
                    )

            with st.container():
                head_col, eff_col = st.columns(2)
                head_col.plotly_chart(plots_dict["head"], use_container_width=True)
                eff_col.plotly_chart(plots_dict["eff"], use_container_width=True)

            with st.container():
                disch_p_col, power_col = st.columns(2)
                disch_p_col.plotly_chart(
                    plots_dict["discharge_pressure"], use_container_width=True
                )
                power_col.plotly_chart(plots_dict["power"], use_container_width=True)
