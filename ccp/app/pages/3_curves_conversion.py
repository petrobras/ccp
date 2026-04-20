import ccp
import io
import streamlit as st
import time
import logging
import json
import toml

from ccp.app.common import (
    default_components,
    pressure_units,
    temperature_units,
    flow_units,
    flow_v_units,
    speed_units,
    head_units,
    power_units,
    get_gas_composition,
    file_sidebar,
    gas_selection_ui,
    design_cases_section,
    curves_upload_section,
    get_available_impellers,
    init_sentry,
    setup_page,
    run_app,
)

init_sentry()


def main():
    """The code has to be inside this main function to allow sentry to work."""
    Q_ = ccp.Q_

    setup_page()
    st.markdown(
        """
    ## Curves Conversion
    """
    )

    def get_session():
        if "session_name" not in st.session_state:
            st.session_state.session_name = ""
        if "converted_impeller" not in st.session_state:
            st.session_state.converted_impeller = None
        if "expander_state" not in st.session_state:
            st.session_state.expander_state = False
        if "ccp_version" not in st.session_state:
            st.session_state.ccp_version = ccp.__version__
        if "app_type" not in st.session_state:
            st.session_state.app_type = "curves_conversion"

        for case in ["A", "B", "C", "D", "E"]:
            if f"impeller_case_{case}" not in st.session_state:
                st.session_state[f"impeller_case_{case}"] = None
            if f"curves_file_1_case_{case}" not in st.session_state:
                st.session_state[f"curves_file_1_case_{case}"] = None
            if f"curves_file_2_case_{case}" not in st.session_state:
                st.session_state[f"curves_file_2_case_{case}"] = None

    get_session()

    def _load_curves_conversion(my_zip, version):
        session_state_data = {}
        for name in my_zip.namelist():
            if name.endswith(".json"):
                session_state_data = json.loads(my_zip.read(name))
                session_state_data["app_type"] = "curves_conversion"

        for name in my_zip.namelist():
            # New format: case_{CASE}/<original-engauge-name>.csv
            if name.endswith(".csv") and name.startswith("case_") and "/" in name:
                prefix, original_name = name.split("/", 1)
                case = prefix.replace("case_", "")
                target_key = None
                for file_num in ("1", "2"):
                    k = f"curves_file_{file_num}_case_{case}"
                    if session_state_data.get(k) is None:
                        target_key = k
                        break
                if target_key is None:
                    target_key = f"curves_file_2_case_{case}"
                session_state_data[target_key] = {
                    "name": original_name,
                    "content": my_zip.read(name),
                }
            # Legacy format: curves_file_{N}_case_{CASE}.csv (original name lost).
            # Reconstruct engauge name from curve_name_case_{CASE} + head/eff
            # convention (file 1 = head, file 2 = eff) so "Load Curves" works.
            elif name.endswith(".csv") and "curves_file_" in name and "_case_" in name:
                parts = name.replace(".csv", "").split("_")
                file_num = parts[2]
                case = parts[-1]
                curve_name = session_state_data.get(f"curve_name_case_{case}")
                if curve_name:
                    suffix = "head" if file_num == "1" else "eff"
                    restored_name = f"{curve_name}-{suffix}.csv"
                else:
                    restored_name = name
                session_state_data[f"curves_file_{file_num}_case_{case}"] = {
                    "name": restored_name,
                    "content": my_zip.read(name),
                }
            if name.endswith(".toml"):
                impeller_file = io.StringIO(my_zip.read(name).decode("utf-8"))
                if name.startswith("impeller_case_"):
                    case = name.replace("impeller_case_", "").replace(".toml", "")
                    session_state_data[f"impeller_case_{case}"] = ccp.Impeller.load(
                        impeller_file
                    )
                elif name.startswith("converted_impeller"):
                    session_state_data["converted_impeller"] = ccp.Impeller.load(
                        impeller_file
                    )

        for key in list(session_state_data.keys()):
            if key.startswith(("load_curves", "convert_curves")):
                del session_state_data[key]

        return session_state_data

    def _save_curves_conversion(my_zip, session_state_dict_copy):
        for key, value in dict(session_state_dict_copy).items():
            if isinstance(value, ccp.Impeller):
                if key == "converted_impeller":
                    my_zip.writestr(
                        "converted_impeller.toml",
                        toml.dumps(value._dict_to_save()),
                    )
                elif key.startswith("impeller_case_"):
                    my_zip.writestr(
                        f"{key}.toml",
                        toml.dumps(value._dict_to_save()),
                    )
                del session_state_dict_copy[key]
            if key.startswith("curves_file_") and "_case_" in key:
                if session_state_dict_copy[key] is not None:
                    parts = key.split("_")
                    case = parts[-1]
                    original_name = session_state_dict_copy[key].get(
                        "name", f"{key}.csv"
                    )
                    my_zip.writestr(
                        f"case_{case}/{original_name}",
                        session_state_dict_copy[key]["content"],
                    )
                del session_state_dict_copy[key]

        session_state_dict_copy["app_type"] = "curves_conversion"

        keys_to_remove = []
        for key in session_state_dict_copy.keys():
            if key.startswith(
                (
                    "FormSubmitter",
                    "my_form",
                    "uploaded",
                    "form",
                    "table",
                    "load_curves",
                    "convert_curves",
                )
            ) or isinstance(
                session_state_dict_copy[key],
                (bytes, st.runtime.uploaded_file_manager.UploadedFile),
            ):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del session_state_dict_copy[key]

        return session_state_dict_copy

    file_sidebar(_load_curves_conversion, _save_curves_conversion)

    # Shared UI sections
    fluid_list, gas_compositions_table = gas_selection_ui()
    design_cases_section()
    curves_upload_section()

    # New Suction Conditions
    with st.expander(
        "New Suction Conditions", expanded=st.session_state.expander_state
    ):
        st.markdown("### Target Suction Conditions")
        st.markdown("Define the new suction conditions for the curves conversion.")

        gas_options = [st.session_state[f"gas_{i}"] for i in range(6)]

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
        width="stretch",
        help="Convert the curves to new suction conditions",
    )

    if convert_button:
        available_cases, impellers_list = get_available_impellers()

        if not available_cases:
            st.error(
                "Please load at least one design case before converting. "
                "Upload curves in the 'Performance Curves Upload' expander."
            )
            return

        if new_suc_p <= 0 or new_suc_t <= 0:
            st.error("Please fill in all new suction condition values")
            return

        progress_bar = st.progress(0, text="Starting conversion...")

        try:
            progress_bar.progress(30, text="Creating new suction conditions...")

            gas_composition_new = get_gas_composition(
                new_gas,
                gas_compositions_table,
                default_components,
            )

            new_suc_state = ccp.State(
                p=Q_(new_suc_p, new_suc_p_unit),
                T=Q_(new_suc_t, new_suc_t_unit),
                fluid=gas_composition_new,
            )

            progress_bar.progress(60, text="Converting curves...")

            if len(impellers_list) == 1:
                original_for_convert = impellers_list[0]
                st.caption(
                    f"Converting from case **{available_cases[0]}** to target conditions."
                )
            else:
                original_for_convert = impellers_list
                st.caption(
                    f"Multiple design cases loaded ({', '.join(available_cases)}). "
                    "ccp will pick the closest case based on speed of sound."
                )

            converted_impeller = ccp.Impeller.convert_from(
                original_impeller=original_for_convert,
                suc=new_suc_state,
                find=find_method,
                speed=speed_option_arg,
            )
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

            if plot_curves_flow_units in flow_v_units:
                plot_curves_flow_v_units = plot_curves_flow_units
            else:
                plot_curves_flow_v_units = "m³/h"

            @st.cache_data
            def generate_plots(
                _impeller,
                impeller_hash,  # Manual invalidation to avoid caching issues with ccp.Impeller object
                point_flow,
                point_flow_v_units,
                point_speed,
                point_speed_units,
                head_units,
                power_units,
                disch_T_units,
                disch_p_units,
            ):
                head_plot = _impeller.head_plot(
                    flow_v_units=point_flow_v_units,
                    head_units=head_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                power_plot = _impeller.power_plot(
                    flow_v_units=point_flow_v_units,
                    power_units=power_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                disch_T_plot = _impeller.disch.T_plot(
                    flow_v_units=point_flow_v_units,
                    T_units=disch_T_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                eff_plot = _impeller.eff_plot(
                    flow_v_units=point_flow_v_units,
                    flow_v=Q_(point_flow, point_flow_v_units),
                    speed=Q_(point_speed, point_speed_units),
                )
                disch_p_plot = _impeller.disch.p_plot(
                    flow_v_units=point_flow_v_units,
                    p_units=disch_p_units,
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

            def render_impeller_plots(impeller, key_prefix, label):
                flow_container = st.container()
                flow_col1, flow_col2, _, _ = flow_container.columns(4)
                flow_col1.markdown(f"Operational Flow (**{plot_curves_flow_v_units}**)")
                project_flow = flow_col2.number_input(
                    f"{label} Flow",
                    min_value=0.0,
                    value=impeller.points[0].flow_v.to(plot_curves_flow_v_units).m,
                    help="Select an operational flow to display the curves at that flow",
                    label_visibility="collapsed",
                    key=f"{key_prefix}_flow_input",
                )

                speed_container = st.container()
                speed_col1, speed_col2, _, _ = speed_container.columns(4)
                speed_col1.markdown(
                    f"Operational Speed (**{plot_curves_speed_units}**)"
                )
                project_speed = speed_col2.number_input(
                    f"{label} Speed",
                    min_value=0.0,
                    value=impeller.points[0].speed.to(plot_curves_speed_units).m,
                    help="Select an operational speed to display the curves at that speed",
                    label_visibility="collapsed",
                    key=f"{key_prefix}_speed_input",
                )

                (
                    head_plot,
                    power_plot,
                    disch_T_plot,
                    eff_plot,
                    disch_p_plot,
                    project_point,
                ) = generate_plots(
                    impeller,
                    hash(impeller),
                    project_flow,
                    plot_curves_flow_v_units,
                    project_speed,
                    plot_curves_speed_units,
                    head_units=plot_curves_head_units,
                    power_units=plot_curves_power_units,
                    disch_T_units=plot_curves_disch_T_units,
                    disch_p_units=plot_curves_disch_p_units,
                )

                plot_col1, plot_col2 = st.columns(2)
                with plot_col1:
                    st.plotly_chart(
                        head_plot, width="stretch", key=f"{key_prefix}_head"
                    )
                    st.plotly_chart(
                        power_plot, width="stretch", key=f"{key_prefix}_power"
                    )
                    st.plotly_chart(
                        disch_T_plot, width="stretch", key=f"{key_prefix}_disch_T"
                    )
                with plot_col2:
                    st.plotly_chart(eff_plot, width="stretch", key=f"{key_prefix}_eff")
                    st.plotly_chart(
                        disch_p_plot, width="stretch", key=f"{key_prefix}_disch_p"
                    )
                    gas_items = sorted(
                        (
                            (comp, float(frac))
                            for comp, frac in project_point.suc.fluid.items()
                            if float(frac) > 0
                        ),
                        key=lambda kv: kv[1],
                        reverse=True,
                    )
                    gas_lines = "\n".join(
                        f"                                {comp.lower():<22s} {frac * 100:>7.3f} %"
                        for comp, frac in gas_items
                    )

                    st.markdown(f"#### {label} Point")
                    st.code(
                        f"""
                            -----------------------------\n
                                Speed:                 {project_point.speed.to("rpm").m:.0f} {plot_curves_speed_units}
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

                                Gas Composition (mol %)
                                --------------------
{gas_lines}

""",
                    )

            @st.fragment
            def display_results():
                available_cases, impellers_list = get_available_impellers()
                converted_imp = st.session_state.converted_impeller

                if available_cases:
                    st.markdown("### Original (Design) Curves")
                    tabs = st.tabs([f"Case {c}" for c in available_cases])
                    for tab, case, imp in zip(tabs, available_cases, impellers_list):
                        with tab:
                            render_impeller_plots(
                                imp,
                                key_prefix=f"orig_case_{case}",
                                label=f"Design Case {case}",
                            )

                st.markdown("### Converted Curves")
                st.write(f"Number of points: {len(converted_imp.points)}")
                st.write(
                    f"Speed range: {min(p.speed.to('rpm').m for p in converted_imp.points):.0f} - {max(p.speed.to('rpm').m for p in converted_imp.points):.0f} RPM"
                )
                st.write(
                    f"Flow range: {min(p.flow_v.to('m³/h').m for p in converted_imp.points):.2f} - {max(p.flow_v.to('m³/h').m for p in converted_imp.points):.2f} m³/h"
                )
                render_impeller_plots(
                    converted_imp,
                    key_prefix="converted",
                    label="Converted",
                )

            display_results()


if __name__ == "__main__":
    run_app(main, "curves_conversion")
