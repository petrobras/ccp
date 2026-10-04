"""State schemas: every key a case of each app type may hold.

Keys follow the Streamlit ``session_state.json`` names so ``.ccp`` files move
between the two apps unchanged. Keys Streamlit never persisted (widgets
created without ``key=``) have new names; see SPEC.md section 3.2.

Kinds:

- ``text``: free text typed by the user, usually a number kept as a string
  (the Streamlit text inputs).
- ``number``: JSON number (Streamlit ``number_input``).
- ``select``: one of ``options``.
- ``bool``: checkbox.
- ``string``: free text that is not a number (tags, names).
- ``gas``: name of one of the six gases; falls back to the first gas when
  the name is not defined, as the Streamlit selects do.
- ``json``: structured value (the gas composition table).
"""

from dataclasses import dataclass, field

from . import gas, units

N_POINTS = 6
CASES = ["A", "B", "C", "D", "E"]
N_FLUID_TAGS = 12
CURVES = ["head", "eff", "discharge_pressure", "power"]
SECTIONS_B2B = ["section_1", "section_2"]


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    units: tuple
    help: str = ""


def _p(key, label, unit_list, help=""):
    return Param(key, label, tuple(unit_list), help)


PARAMETERS = {
    p.key: p
    for p in [
        _p(
            "flow",
            "Flow",
            units.flow_units,
            "Flow can be mass flow or volumetric flow depending on the selected unit.",
        ),
        _p("flow_v", "Volumetric Flow", units.flow_v_units, "Volumetric flow."),
        _p("suction_pressure", "Suction Pressure", units.pressure_units),
        _p("suction_temperature", "Suction Temperature", units.temperature_units),
        _p("discharge_pressure", "Discharge Pressure", units.pressure_units),
        _p("discharge_temperature", "Discharge Temperature", units.temperature_units),
        _p(
            "casing_delta_T",
            "Casing ΔT",
            units.temperature_units,
            "Temperature difference between the casing and the ambient temperature.",
        ),
        _p("speed", "Speed", units.speed_units),
        _p("balance_line_flow_m", "Balance Line Flow", units.flow_m_units),
        _p(
            "end_seal_upstream_pressure",
            "Pressure Upstream End Seal",
            units.pressure_units,
            "Second section suction pressure.",
        ),
        _p(
            "end_seal_upstream_temperature",
            "Temperature Upstream End Seal",
            units.temperature_units,
            "Second section suction temperature.",
        ),
        _p(
            "div_wall_flow_m",
            "Division Wall Flow",
            units.flow_m_units,
            "Flow through the division wall if measured. Otherwise it is calculated "
            "from the First Section Discharge Flow.",
        ),
        _p(
            "div_wall_upstream_pressure",
            "Pressure Upstream Division Wall",
            units.pressure_units,
            "Second section discharge pressure.",
        ),
        _p(
            "div_wall_upstream_temperature",
            "Temperature Upstream Division Wall",
            units.temperature_units,
            "Second section discharge temperature.",
        ),
        _p(
            "first_section_discharge_flow_m",
            "First Section Discharge Flow",
            units.flow_m_units,
            "If the Division Wall Flow is not measured, we use this value to "
            "calculate it.",
        ),
        _p("seal_gas_flow_m", "Seal Gas Flow", units.flow_m_units),
        _p("seal_gas_temperature", "Seal Gas Temperature", units.temperature_units),
        _p(
            "oil_flow_journal_bearing_de",
            "Oil Flow Journal Bearing DE",
            units.oil_flow_units,
        ),
        _p(
            "oil_flow_journal_bearing_nde",
            "Oil Flow Journal Bearing NDE",
            units.oil_flow_units,
        ),
        _p(
            "oil_flow_thrust_bearing_nde",
            "Oil Flow Thrust Bearing NDE",
            units.oil_flow_units,
        ),
        _p("oil_inlet_temperature", "Oil Inlet Temperature", units.temperature_units),
        _p(
            "oil_outlet_temperature_de",
            "Oil Outlet Temperature DE",
            units.temperature_units,
        ),
        _p(
            "oil_outlet_temperature_nde",
            "Oil Outlet Temperature NDE",
            units.temperature_units,
        ),
        _p("head", "Head", units.head_units),
        _p("eff", "Efficiency", [""]),
        _p("power", "Gas Power", units.power_units),
        _p("power_shaft", "Shaft Power", units.power_units),
        _p("b", "First Impeller Width", units.length_units),
        _p("D", "First Impeller Diameter", units.length_units),
        _p(
            "surface_roughness",
            "Surface Roughness",
            units.roughness_units,
            "Mean surface roughness of the gas path.",
        ),
        _p("casing_area", "Casing Area", units.area_units),
        _p(
            "outer_diameter_fo",
            "Orifice Outer Diameter",
            units.orifice_length_units,
            "Outer diameter of orifice plate.",
        ),
        _p(
            "inner_diameter_fo",
            "Orifice Inner Diameter",
            units.orifice_length_units,
            "Inner diameter of orifice plate.",
        ),
        _p(
            "upstream_pressure_fo",
            "Orifice Upstream Pressure",
            units.pressure_units,
            "Upstream pressure of orifice plate.",
        ),
        _p(
            "upstream_temperature_fo",
            "Orifice Upstream Temperature",
            units.temperature_units,
            "Upstream temperature of orifice plate.",
        ),
        _p(
            "pressure_drop_fo",
            "Orifice Pressure Drop",
            units.pressure_units,
            "Pressure drop across orifice plate.",
        ),
        _p(
            "tappings_fo",
            "Orifice Tappings",
            units.tappings_options,
            "Pressure tappings type.",
        ),
        _p("mass_flow_fo", "Mass Flow (Result)", ["kg/h", "lbm/h", "kg/s", "lbm/s"]),
    ]
}

DATA_SHEET_PARAMETERS = [
    "flow",
    "suction_pressure",
    "suction_temperature",
    "discharge_pressure",
    "discharge_temperature",
    "power",
    "power_shaft",
    "speed",
    "head",
    "eff",
    "b",
    "D",
    "surface_roughness",
    "casing_area",
]

TEST_PARAMETERS_ST = [
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
    "oil_flow_journal_bearing_de",
    "oil_flow_journal_bearing_nde",
    "oil_flow_thrust_bearing_nde",
    "oil_inlet_temperature",
    "oil_outlet_temperature_de",
    "oil_outlet_temperature_nde",
]

TEST_PARAMETERS_SEC1 = [
    "flow",
    "suction_pressure",
    "suction_temperature",
    "discharge_pressure",
    "discharge_temperature",
    "casing_delta_T",
    "speed",
    "balance_line_flow_m",
    "end_seal_upstream_pressure",
    "end_seal_upstream_temperature",
    "div_wall_flow_m",
    "div_wall_upstream_pressure",
    "div_wall_upstream_temperature",
    "first_section_discharge_flow_m",
    "seal_gas_flow_m",
    "seal_gas_temperature",
    "oil_flow_journal_bearing_de",
    "oil_flow_journal_bearing_nde",
    "oil_flow_thrust_bearing_nde",
    "oil_inlet_temperature",
    "oil_outlet_temperature_de",
    "oil_outlet_temperature_nde",
]

TEST_PARAMETERS_SEC2 = [
    "flow",
    "suction_pressure",
    "suction_temperature",
    "discharge_pressure",
    "discharge_temperature",
    "casing_delta_T",
    "speed",
    "balance_line_flow_m",
    "seal_gas_flow_m",
    "oil_flow_journal_bearing_de",
    "oil_flow_journal_bearing_nde",
    "oil_flow_thrust_bearing_nde",
    "oil_inlet_temperature",
    "oil_outlet_temperature_de",
    "oil_outlet_temperature_nde",
]

# Orifice plate rows of the test data, shown when the flow method of a
# section is "Orifice"; the flow is then calculated from them (ISO 5167).
ORIFICE_PARAMETERS = [
    "outer_diameter_fo",
    "inner_diameter_fo",
    "upstream_pressure_fo",
    "upstream_temperature_fo",
    "pressure_drop_fo",
    "tappings_fo",
]
FLOW_METHODS = ["Direct", "Orifice"]

# Rows disabled by the options, as in the Streamlit pages.
SEAL_GAS_PARAMETERS = {"seal_gas_flow_m", "seal_gas_temperature"}
LEAKAGE_PARAMETERS = {
    "balance_line_flow_m",
    "end_seal_upstream_pressure",
    "end_seal_upstream_temperature",
    "div_wall_flow_m",
    "div_wall_upstream_pressure",
    "div_wall_upstream_temperature",
    "first_section_discharge_flow_m",
    "seal_gas_flow_m",
    "seal_gas_temperature",
}

OPTIONS = [
    ("opt_reynolds_correction", "Reynolds Correction", ""),
    ("opt_casing_heat_loss", "Casing Heat Loss", ""),
    ("opt_bearing_mechanical_losses", "Bearing Mechanical Losses", ""),
    ("opt_calculate_leakages", "Calculate Leakages", ""),
    ("opt_seal_gas_flow", "Seal Gas Flow", ""),
    ("opt_variable_speed", "Variable Speed", ""),
    (
        "opt_show_points",
        "Show Points",
        "If marked, shows points in the plotted curves in addition to interpolation.",
    ),
]


@dataclass
class Field:
    key: str
    kind: str
    default: object = ""
    options: tuple = ()
    label: str = ""
    export: bool = True


@dataclass
class Schema:
    app_type: str
    fields: dict = field(default_factory=dict)

    def add(self, key, kind, default="", options=(), label="", export=True):
        self.fields[key] = Field(key, kind, default, tuple(options), label, export)

    def __contains__(self, key):
        return key in self.fields

    def defaults(self):
        import copy

        return {k: copy.deepcopy(f.default) for k, f in self.fields.items()}


def _unit_default(options):
    return options[0] if options else ""


def _common_session(schema):
    schema.add("session_name", "string", "")


def _gas_fields(schema):
    for i in range(gas.N_GASES):
        schema.add(f"gas_{i}", "string", f"gas_{i}", label="Gas Name")
    schema.add("gas_compositions_table", "json", gas.default_table())


def _options_fields(schema):
    for key, label, _help in OPTIONS:
        schema.add(key, "bool", True, label=label)
    schema.add(
        "ambient_pressure_magnitude", "text", "1.01325", label="Ambient Pressure"
    )
    schema.add("ambient_pressure_unit", "select", "bar", units.pressure_units)
    schema.add("oil_specific_heat", "bool", False, label="Specific Heat")
    schema.add("oil_specific_heat_magnitude", "text", "2.03")
    schema.add(
        "oil_specific_heat_unit", "select", "kJ/kg/degK", units.specific_heat_units
    )
    schema.add("oil_density_magnitude", "text", "846.9")
    schema.add("oil_density_unit", "select", "kg/m³", units.density_units)
    schema.add("oil_iso", "bool", False, label="Oil ISO Classification")
    schema.add("oil_iso_classification", "select", "VG 32", units.oil_iso_options)
    schema.add(
        "polytropic_method",
        "select",
        "Sandberg-Colby",
        list(units.polytropic_methods.keys()),
    )


def _curve_fields(schema, suffix=""):
    for curve in CURVES:
        base = f"{curve}{suffix}"
        schema.add(f"x_{base}_lower", "text", "")
        schema.add(f"x_{base}_upper", "text", "")
        schema.add(
            f"x_{base}_flow_units", "select", units.flow_v_units[0], units.flow_v_units
        )
        schema.add(f"y_{base}_lower", "text", "")
        schema.add(f"y_{base}_upper", "text", "")
        y_units = PARAMETERS[curve].units
        schema.add(f"y_{base}_units", "select", _unit_default(y_units), y_units)


def straight_through_schema():
    s = Schema("straight_through")
    _common_session(s)
    _gas_fields(s)
    _options_fields(s)
    s.add("gas_point_guarantee", "gas", "gas_0")
    for param in DATA_SHEET_PARAMETERS:
        opts = PARAMETERS[param].units
        s.add(f"{param}_units_point_guarantee", "select", _unit_default(opts), opts)
        s.add(f"{param}_point_guarantee", "text", "")
    _curve_fields(s)
    for i in range(1, N_POINTS + 1):
        s.add(f"gas_point_{i}", "gas", "gas_0")
        # Streamlit's orifice gas; the orifice now uses the test point gas.
        s.add(f"gas_fo_{i}", "gas", "gas_0")
    for param in TEST_PARAMETERS_ST:
        opts = PARAMETERS[param].units
        s.add(f"{param}_units", "select", _unit_default(opts), opts)
        for i in range(1, N_POINTS + 1):
            s.add(f"{param}_point_{i}", "text", "")
    s.add("flow_method", "select", FLOW_METHODS[0], FLOW_METHODS)
    _measured_flow_fields(s, "_units", "_point_{i}")
    # Streamlit keys: ``outer_diameter_fo_1``, ``outer_diameter_fo_units``...
    # ``mass_flow_fo`` is Streamlit's result row, kept in sync for its files.
    _orifice_fields(s, "", ORIFICE_PARAMETERS + ["mass_flow_fo"])
    return s


def _measured_flow_fields(s, unit_suffix, value_suffix):
    """Measured flows kept aside while the flow comes from the orifice."""
    opts = PARAMETERS["flow"].units
    s.add(f"flow_measured{unit_suffix}", "select", "", ("",) + opts)
    for i in range(1, N_POINTS + 1):
        s.add(f"flow_measured{value_suffix.format(i=i)}", "text", "")


def _orifice_fields(s, suffix, params):
    for param in params:
        opts = PARAMETERS[param].units
        if param == "tappings_fo":
            for i in range(1, N_POINTS + 1):
                s.add(f"{param}{suffix}_{i}", "select", opts[0], opts)
            continue
        s.add(f"{param}_units{suffix}", "select", _unit_default(opts), opts)
        for i in range(1, N_POINTS + 1):
            s.add(f"{param}{suffix}_{i}", "text", "")


def back_to_back_schema():
    s = Schema("back_to_back")
    _common_session(s)
    _gas_fields(s)
    _options_fields(s)
    for section in SECTIONS_B2B:
        s.add(f"gas_{section}_point_guarantee", "gas", "gas_0")
    for param in DATA_SHEET_PARAMETERS:
        opts = PARAMETERS[param].units
        # One unit select shared by both sections, keyed on section 1.
        s.add(
            f"{param}_units_section_1_point_guarantee",
            "select",
            _unit_default(opts),
            opts,
        )
        for section in SECTIONS_B2B:
            s.add(f"{param}_{section}_point_guarantee", "text", "")
    for sec in ["sec1", "sec2"]:
        _curve_fields(s, f"_{sec}")
    for section, params in zip(
        SECTIONS_B2B, [TEST_PARAMETERS_SEC1, TEST_PARAMETERS_SEC2]
    ):
        for i in range(1, N_POINTS + 1):
            s.add(f"gas_{section}_point_{i}", "gas", "gas_0")
        for param in params:
            opts = PARAMETERS[param].units
            s.add(f"{param}_units_{section}", "select", _unit_default(opts), opts)
            for i in range(1, N_POINTS + 1):
                s.add(f"{param}_{section}_point_{i}", "text", "")
        s.add(f"flow_method_{section}", "select", FLOW_METHODS[0], FLOW_METHODS)
        _measured_flow_fields(s, f"_units_{section}", f"_{section}_point_{{i}}")
        _orifice_fields(s, f"_{section}", ORIFICE_PARAMETERS)
    return s


def _design_case_fields(s):
    for case in CASES:
        s.add(f"gas_case_{case}", "gas", "gas_0")
        s.add(f"suc_p_case_{case}", "number", 0.0)
        s.add(f"suc_T_case_{case}", "number", 0.0)
        s.add(f"curve_name_case_{case}", "string", "")
    s.add("design_suc_p_unit", "select", "bar", units.pressure_units)
    s.add("design_suc_T_unit", "select", "degC", units.temperature_units)
    s.add("loaded_curves_speed_units", "select", "rpm", units.speed_units)
    s.add("loaded_curves_flow_units", "select", "m³/h", units.flow_units)
    s.add("loaded_curves_head_units", "select", "kJ/kg", units.head_units)
    s.add("loaded_curves_power_units", "select", "kW", units.power_units)
    s.add("loaded_curves_disch_p_units", "select", "bar", units.pressure_units)
    s.add("loaded_curves_disch_T_units", "select", "degK", units.temperature_units)


def curves_conversion_schema():
    s = Schema("curves_conversion")
    _common_session(s)
    _gas_fields(s)
    _design_case_fields(s)
    s.add("new_gas_selection", "gas", "gas_0")
    s.add("new_suc_p_unit", "select", "bar", units.pressure_units)
    s.add("new_suc_p", "number", 0.0)
    s.add("new_suc_t_unit", "select", "degC", units.temperature_units)
    s.add("new_suc_t", "number", 0.0)
    s.add("conv_find_method", "select", "speed", ["speed", "volume_ratio"])
    s.add("conv_speed_option", "select", "same", ["same", "calculate"])
    s.add("plot_curves_speed_units", "select", "rpm", units.speed_units)
    s.add("plot_curves_flow_units", "select", "m³/h", units.flow_units)
    s.add("plot_curves_disch_p_units", "select", "bar", units.pressure_units)
    s.add("plot_curves_disch_T_units", "select", "degK", units.temperature_units)
    s.add("plot_curves_head_units", "select", "kJ/kg", units.head_units)
    s.add("plot_curves_power_units", "select", "kW", units.power_units)
    s.add("show_design_curves", "bool", False)
    for prefix in ["converted"] + [f"orig_case_{c}" for c in CASES]:
        s.add(f"{prefix}_flow_input", "number", None)
        s.add(f"{prefix}_speed_input", "number", None)
        s.add(f"{prefix}_show_similarity", "bool", False)
    return s


TAG_PARAMETERS = [
    ("suc_p", "Suction Pressure", units.pressure_units),
    ("suc_T", "Suction Temperature", units.temperature_units),
    ("disch_p", "Discharge Pressure", units.pressure_units),
    ("disch_T", "Discharge Temperature", units.temperature_units),
    ("speed", "Speed", units.speed_units),
]
FLOW_TAG_PARAMETERS = [("flow", "Flow", units.flow_units)]
ORIFICE_TAG_PARAMETERS = [
    ("delta_p", "Delta P", units.pressure_units),
    ("p_downstream", "Downstream P", units.pressure_units),
]

DATA_SOURCES = [
    ("pi", "PI Live"),
    ("file", "File"),
    ("mock", "Mock"),
]


def performance_evaluation_schema():
    s = Schema("performance_evaluation")
    _common_session(s)
    _gas_fields(s)
    _design_case_fields(s)
    s.add("data_source", "select", "pi", [k for k, _ in DATA_SOURCES])
    s.add("pi_server_name", "string", "")
    s.add("pi_auth_method", "select", "kerberos", ["kerberos", "basic"])
    s.add("pi_username", "string", "")
    for prefix, _label, opts in (
        TAG_PARAMETERS + FLOW_TAG_PARAMETERS + ORIFICE_TAG_PARAMETERS
    ):
        for n in ["", "_2"]:
            s.add(f"{prefix}_tag{n}", "string", "")
            s.add(f"{prefix}_unit{n}", "select", opts[0], opts)
    s.add("flow_method", "select", "Direct", ["Direct", "Orifice"])
    s.add("orifice_tappings", "select", "flange", units.tappings_options)
    s.add("orifice_D", "number", 0.0)
    s.add("orifice_D_unit", "select", "m", units.length_units)
    s.add("orifice_d", "number", 0.0)
    s.add("orifice_d_unit", "select", "m", units.length_units)
    s.add(
        "fluid_source",
        "select",
        "Fixed Operation Fluid",
        ["Fixed Operation Fluid", "Inform Component Tags"],
    )
    s.add("operation_fluid_gas", "gas", "gas_0")
    for i in range(N_FLUID_TAGS):
        s.add(f"fluid_component_{i}", "string", "")
        s.add(f"fluid_tag_{i}", "string", "")
        s.add(f"fluid_unit_{i}", "select", "mol_frac", units.fluid_fraction_units)
    s.add("eval_start", "string", "")
    s.add("eval_end", "string", "")
    s.add("temperature_fluctuation", "number", 0.5)
    s.add("pressure_fluctuation", "number", 2.0)
    s.add("speed_fluctuation", "number", 0.5)
    s.add("refresh_interval", "number", 30)
    s.add("show_similarity", "bool", False)
    s.add("eval_cluster_idx", "number", 0)
    s.add("eval_show_similarity", "bool", False)
    s.add("ai_enabled", "bool", False)
    s.add("ai_provider", "select", "gemini", ["gemini", "azure"])
    # Streamlit leaves these out of the saved file; so do we.
    s.add("ai_azure_endpoint", "string", "", export=False)
    s.add("ai_azure_deployment", "string", "", export=False)
    return s


_BUILDERS = {
    "straight_through": straight_through_schema,
    "back_to_back": back_to_back_schema,
    "curves_conversion": curves_conversion_schema,
    "performance_evaluation": performance_evaluation_schema,
}
_CACHE = {}


def get_schema(app_type):
    if app_type not in _CACHE:
        _CACHE[app_type] = _BUILDERS[app_type]()
    return _CACHE[app_type]


def default_state(app_type):
    return get_schema(app_type).defaults()


def coerce(field_, value):
    """Convert a submitted or imported value to the field's JSON type."""
    kind = field_.kind
    if kind == "bool":
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "on", "yes"}
        return bool(value)
    if kind == "number":
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return field_.default
        try:
            number = (
                float(str(value).replace(",", "."))
                if isinstance(value, str)
                else float(value)
            )
        except (TypeError, ValueError):
            return field_.default
        if isinstance(field_.default, int) and not isinstance(field_.default, bool):
            return int(number) if number.is_integer() else number
        return number
    if kind == "select":
        value = "" if value is None else str(value)
        if field_.options and value not in field_.options:
            # Keep legacy unit strings pint understands (e.g. 'mm*H2O*g0').
            return value if value else field_.default
        return value
    if kind == "json":
        return value
    return "" if value is None else str(value)


def normalize(app_type, state):
    """Return a complete state: schema keys only, typed, defaults filled."""
    schema = get_schema(app_type)
    result = schema.defaults()
    for key, value in (state or {}).items():
        f = schema.fields.get(key)
        if f is None:
            continue
        result[key] = coerce(f, value)
    gas.normalize_state(result)
    names = gas.gas_names(result)
    for key, f in schema.fields.items():
        if f.kind == "gas" and result.get(key) not in names:
            result[key] = names[0]
    return result
