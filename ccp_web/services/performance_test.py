"""Straight-through and back-to-back performance tests.

One module serves both pages: a straight-through compressor has one unnamed
section, a back-to-back compressor has ``section_1`` and ``section_2``. The
calculation follows ``ccp/app/pages/1_straight_through.py`` and
``2_back_to_back.py``; the differences are listed in SPEC.md section 5.

Everything here must run inside ``units.state_context(state)``.
"""

import io
from dataclasses import dataclass

import numpy as np
import pandas as pd

import ccp
from ccp import Q_
from ccp.compressor import (
    BackToBack,
    Point1Sec,
    PointFirstSection,
    PointSecondSection,
    StraightThrough,
)
from ccp.config.utilities import r_getattr

from . import gas, schemas
from .units import Cancelled, InputError, StateReader, is_mass_flow_unit  # noqa: F401

T_ = "ₜ"
SP = "ₛₚ"
CONV = "ᶜᵒⁿᵛ"

COLUMNS = [
    f"φ{T_}",
    f"φ{T_} / φ{SP}",
    "vi / vd",
    f"(vi/vd){T_}/(vi/vd){SP}",
    f"Mach{T_}",
    f"Mach{T_} - Mach{SP}",
    f"Re{T_}",
    f"Re{T_} / Re{SP}",
    f"pd{CONV} (bar)",
    f"pd{CONV}/pd{SP}",
    f"Head{T_} (kJ/kg)",
    f"Head{T_}/Head{SP}",
    f"Head{CONV} (kJ/kg)",
    f"Head{CONV}/Head{SP}",
    f"Q{CONV} (m3/h)",
    f"Q{CONV}/Q{SP}",
    f"W{T_} (kW)",
    f"W{T_}/W{SP}",
    f"W{CONV} (kW)",
    f"W{CONV}/W{SP}",
    f"Eff{T_}",
    f"Eff{CONV}",
]
PERCENT_COLUMNS = {
    f"φ{T_} / φ{SP}",
    f"pd{CONV}/pd{SP}",
    f"(vi/vd){T_}/(vi/vd){SP}",
    f"Head{T_}/Head{SP}",
    f"Head{CONV}/Head{SP}",
    f"Q{CONV}/Q{SP}",
    f"W{T_}/W{SP}",
    f"W{CONV}/W{SP}",
    f"Eff{T_}",
    f"Eff{CONV}",
}
SCIENTIFIC_COLUMNS = {f"Re{T_}"}
GUARANTEE = "Guarantee Point"
OVERALL = "Overall"


@dataclass
class Section:
    """Key naming for one compressor section."""

    app_type: str
    name: str | None  # None, "section_1" or "section_2"

    @property
    def sec(self):
        return {None: None, "section_1": "sec1", "section_2": "sec2"}[self.name]

    @property
    def title(self):
        return {
            None: "Results",
            "section_1": "First Section",
            "section_2": "Second Section",
        }[self.name]

    def ds_value(self, param):
        if self.name is None:
            return f"{param}_point_guarantee"
        return f"{param}_{self.name}_point_guarantee"

    def ds_unit(self, param):
        if self.name is None:
            return f"{param}_units_point_guarantee"
        return f"{param}_units_section_1_point_guarantee"

    @property
    def ds_gas(self):
        if self.name is None:
            return "gas_point_guarantee"
        return f"gas_{self.name}_point_guarantee"

    def tp_value(self, param, i):
        if self.name is None:
            return f"{param}_point_{i}"
        return f"{param}_{self.name}_point_{i}"

    def tp_unit(self, param):
        if self.name is None:
            return f"{param}_units"
        return f"{param}_units_{self.name}"

    def tp_gas(self, i):
        if self.name is None:
            return f"gas_point_{i}"
        return f"gas_{self.name}_point_{i}"

    @property
    def flow_method(self):
        """State key of the section's flow method ("Direct" or "Orifice")."""
        return "flow_method" if self.name is None else f"flow_method_{self.name}"

    def fo_value(self, param, i):
        """Orifice plate key (Streamlit ``outer_diameter_fo_1`` naming)."""
        if self.name is None:
            return f"{param}_{i}"
        return f"{param}_{self.name}_{i}"

    def fo_unit(self, param):
        if self.name is None:
            return f"{param}_units"
        return f"{param}_units_{self.name}"

    @property
    def test_parameters(self):
        return {
            None: schemas.TEST_PARAMETERS_ST,
            "section_1": schemas.TEST_PARAMETERS_SEC1,
            "section_2": schemas.TEST_PARAMETERS_SEC2,
        }[self.name]

    def curve_prefix(self, curve):
        return curve if self.sec is None else f"{curve}_{self.sec}"

    def attr(self, name):
        """Compressor attribute for this section (``points_flange_sp_sec1``...)."""
        return name if self.sec is None else f"{name}_{self.sec}"


def sections(app_type):
    if app_type == "straight_through":
        return [Section(app_type, None)]
    return [Section(app_type, "section_1"), Section(app_type, "section_2")]


@dataclass
class Options:
    reynolds_correction: bool
    casing_heat_loss: bool
    bearing_mechanical_losses: bool
    calculate_leakages: bool
    seal_gas_flow: bool
    variable_speed: bool
    show_points: bool
    oil_specific_heat: bool
    oil_iso: bool
    oil_iso_classification: str
    oil_specific_heat_value: object = None
    oil_density_value: object = None

    @classmethod
    def from_state(cls, state, reader=None):
        r = reader or StateReader(state)
        opts = cls(
            reynolds_correction=r.flag("opt_reynolds_correction", True),
            casing_heat_loss=r.flag("opt_casing_heat_loss", True),
            bearing_mechanical_losses=r.flag("opt_bearing_mechanical_losses", True),
            calculate_leakages=r.flag("opt_calculate_leakages", True),
            seal_gas_flow=r.flag("opt_seal_gas_flow", True),
            variable_speed=r.flag("opt_variable_speed", True),
            show_points=r.flag("opt_show_points", True),
            oil_specific_heat=r.flag("oil_specific_heat"),
            oil_iso=r.flag("oil_iso"),
            oil_iso_classification=r.text("oil_iso_classification", "VG 32"),
        )
        if opts.oil_specific_heat:
            cp = r.quantity(
                "oil_specific_heat_magnitude",
                r.text("oil_specific_heat_unit", "kJ/kg/degK"),
            )
            rho = r.quantity(
                "oil_density_magnitude", r.text("oil_density_unit", "kg/m³")
            )
            opts.oil_specific_heat_value = (
                cp.to("kJ/kg/kelvin") if cp is not None else None
            )
            opts.oil_density_value = rho.to("kg/m³") if rho is not None else None
        return opts


def specific_heat_calculate(T_in, T_out, oil_iso_classification):
    """ISO VG oil mean specific heat between two temperatures (``common.py``)."""
    T_in = T_in.to("degC").m
    T_out = T_out.to("degC").m
    if oil_iso_classification[3:] == "32":
        a, b, c = -0.0000019, 0.0042, 1.80
    else:
        a, b, c = -0.0000018, 0.0040, 1.83
    cp = (
        a * (T_out**3 - T_in**3) / 3 + b * (T_out**2 - T_in**2) / 2 + c * (T_out - T_in)
    ) / (T_out - T_in)
    return Q_(cp, "kJ/kg/degK")


def density_calculate(T_in, T_out, oil_iso_classification):
    """ISO VG oil mean density between two temperatures (``common.py``)."""
    T_in = T_in.to("degC").m
    T_out = T_out.to("degC").m
    beta = 0.00075
    rho_15 = 870.0 if oil_iso_classification[3:] == "32" else 876.0
    density = (
        rho_15
        / (beta * (T_out - T_in))
        * (np.log(1 + beta * T_out - 15 * beta) - np.log(1 + beta * T_in - 15 * beta))
    )
    return Q_(density, "kg/m³")


def _fluid(r, state, gas_key):
    name = state.get(gas_key)
    fluid = gas.composition(state, name)
    if not fluid:
        r.errors[gas_key] = f"Gas '{name}' has no composition"
    return fluid


def _guarantee_values(r, state, sec, opts):
    """Read the data sheet of one section; no ccp objects are created."""
    v = {"fluid": _fluid(r, state, sec.ds_gas)}
    for param in [
        "flow",
        "suction_pressure",
        "suction_temperature",
        "discharge_pressure",
        "discharge_temperature",
        "speed",
        "b",
        "D",
        "power",
        "casing_area",
        "surface_roughness",
    ]:
        v[param] = r.quantity(sec.ds_value(param), state.get(sec.ds_unit(param)))
    v["power_shaft"] = r.quantity(
        sec.ds_value("power_shaft"),
        state.get(sec.ds_unit("power_shaft")),
        required=False,
    )
    v["flow_is_mass"] = is_mass_flow_unit(state.get(sec.ds_unit("flow")) or "kg/h")
    return v


def _guarantee_point(v, opts):
    kwargs = {}
    kwargs["flow_m" if v["flow_is_mass"] else "flow_v"] = v["flow"]
    kwargs["suc"] = ccp.State(
        p=v["suction_pressure"], T=v["suction_temperature"], fluid=v["fluid"]
    )
    kwargs["disch"] = ccp.State(
        p=v["discharge_pressure"], T=v["discharge_temperature"], fluid=v["fluid"]
    )
    kwargs["speed"] = v["speed"]
    kwargs["b"] = v["b"]
    kwargs["D"] = v["D"]
    if opts.bearing_mechanical_losses:
        shaft = v["power_shaft"] if v["power_shaft"] is not None else v["power"]
        kwargs["power_losses"] = shaft.to("kW") - v["power"]
    else:
        kwargs["power_losses"] = Q_(0, "W")
    return ccp.Point(**kwargs)


def _point_filled(r, sec, i):
    return any(not r.is_blank(sec.tp_value(p, i)) for p in sec.test_parameters)


def _test_point_values(r, state, sec, i, opts, guarantee):
    """Keyword arguments (as quantities) for test point ``i`` of a section."""

    def q(param, required=True):
        return r.quantity(
            sec.tp_value(param, i), state.get(sec.tp_unit(param)), required
        )

    def zero(param):
        return Q_(0, state.get(sec.tp_unit(param)) or "")

    v = {"fluid": _fluid(r, state, sec.tp_gas(i))}
    flow_unit = state.get(sec.tp_unit("flow")) or "kg/h"
    v["flow_key"] = "flow_m" if is_mass_flow_unit(flow_unit) else "flow_v"
    v["flow"] = q("flow")
    for param in [
        "suction_pressure",
        "suction_temperature",
        "discharge_pressure",
        "discharge_temperature",
        "speed",
    ]:
        v[param] = q(param)

    kw = {}
    casing = q("casing_delta_T", required=False)
    if casing is not None and opts.casing_heat_loss:
        kw["casing_temperature"] = casing
        kw["ambient_temperature"] = 0
    else:
        kw["casing_temperature"] = 0
        kw["ambient_temperature"] = 0

    if opts.calculate_leakages:
        kw["balance_line_flow_m"] = q("balance_line_flow_m", required=False)
        seal = q("seal_gas_flow_m", required=False) if opts.seal_gas_flow else None
        kw["seal_gas_flow_m"] = seal if seal is not None else zero("seal_gas_flow_m")
        if sec.name in (None, "section_1"):
            seal_T = (
                q("seal_gas_temperature", required=False)
                if opts.seal_gas_flow
                else None
            )
            kw["seal_gas_temperature"] = (
                seal_T if seal_T is not None else zero("seal_gas_temperature")
            )
        if sec.name == "section_1":
            kw["div_wall_flow_m"] = q("div_wall_flow_m", required=False)
            kw["first_section_discharge_flow_m"] = q(
                "first_section_discharge_flow_m", required=False
            )
            for param in [
                "end_seal_upstream_pressure",
                "end_seal_upstream_temperature",
                "div_wall_upstream_pressure",
                "div_wall_upstream_temperature",
            ]:
                kw[param] = q(param)
    else:
        kw["leakages"] = False
        if sec.name == "section_1":
            # The division wall and end seal states are still needed to
            # build the section 2 suction; they are measured regardless.
            for param in [
                "end_seal_upstream_pressure",
                "end_seal_upstream_temperature",
                "div_wall_upstream_pressure",
                "div_wall_upstream_temperature",
            ]:
                kw[param] = q(param, required=False)

    kw["bearing_mechanical_losses"] = opts.bearing_mechanical_losses
    if opts.bearing_mechanical_losses:
        for param in [
            "oil_flow_journal_bearing_de",
            "oil_flow_journal_bearing_nde",
            "oil_flow_thrust_bearing_nde",
            "oil_inlet_temperature",
            "oil_outlet_temperature_de",
            "oil_outlet_temperature_nde",
        ]:
            kw[param] = q(param, required=False)
        if opts.oil_iso:
            missing = [
                p
                for p in [
                    "oil_inlet_temperature",
                    "oil_outlet_temperature_de",
                    "oil_outlet_temperature_nde",
                ]
                if kw[p] is None
            ]
            for p in missing:
                r.errors[sec.tp_value(p, i)] = "Required for ISO oil properties"
            if not missing:
                T_in = kw["oil_inlet_temperature"]
                kw["oil_specific_heat_de"] = specific_heat_calculate(
                    T_in, kw["oil_outlet_temperature_de"], opts.oil_iso_classification
                )
                kw["oil_specific_heat_nde"] = specific_heat_calculate(
                    T_in, kw["oil_outlet_temperature_nde"], opts.oil_iso_classification
                )
                kw["oil_density_de"] = density_calculate(
                    T_in, kw["oil_outlet_temperature_de"], opts.oil_iso_classification
                )
                kw["oil_density_nde"] = density_calculate(
                    T_in, kw["oil_outlet_temperature_nde"], opts.oil_iso_classification
                )
        elif opts.oil_specific_heat:
            kw["oil_specific_heat_de"] = opts.oil_specific_heat_value
            kw["oil_specific_heat_nde"] = opts.oil_specific_heat_value
            kw["oil_density_de"] = opts.oil_density_value
            kw["oil_density_nde"] = opts.oil_density_value

    kw["b"] = guarantee["b"]
    kw["D"] = guarantee["D"]
    kw["casing_area"] = guarantee["casing_area"]
    kw["surface_roughness"] = guarantee["surface_roughness"]
    v["kwargs"] = kw
    return v


def _test_point(v, sec):
    kw = dict(v["kwargs"])
    kw[v["flow_key"]] = v["flow"]
    kw["suc"] = ccp.State(
        p=v["suction_pressure"], T=v["suction_temperature"], fluid=v["fluid"]
    )
    kw["disch"] = ccp.State(
        p=v["discharge_pressure"], T=v["discharge_temperature"], fluid=v["fluid"]
    )
    cls = {
        None: Point1Sec,
        "section_1": PointFirstSection,
        "section_2": PointSecondSection,
    }[sec.name]
    return cls(speed=v["speed"], **kw)


def read_inputs(app_type, state):
    """Validate every input; return the values needed to build the compressor.

    Raises ``InputError`` listing every invalid field before any flash runs.
    """
    r = StateReader(state)
    opts = Options.from_state(state, r)
    data = {"options": opts, "sections": [], "warnings": []}
    for sec in sections(app_type):
        guarantee = _guarantee_values(r, state, sec, opts)
        points = []
        for i in range(1, schemas.N_POINTS + 1):
            required = ["flow", "suction_pressure", "suction_temperature"]
            if any(r.is_blank(sec.tp_value(p, i)) for p in required):
                if _point_filled(r, sec, i):
                    label = f"{sec.title} point {i}" if sec.name else f"Point {i}"
                    data["warnings"].append(
                        f"{label} skipped: flow, suction pressure and suction "
                        "temperature are required."
                    )
                continue
            points.append((i, _test_point_values(r, state, sec, i, opts, guarantee)))
        if not points:
            r.errors[sec.tp_value("flow", 1)] = "At least one test point is required"
        data["sections"].append((sec, guarantee, points))
    r.raise_errors()
    return data


def calculate(app_type, state, calculate_speed=False, progress=None, cancelled=None):
    """Build the compressor object for a case.

    Parameters
    ----------
    progress : callable(fraction, message), optional
    cancelled : callable() -> bool, optional
        Checked between steps; raises ``Cancelled``.

    Returns
    -------
    compressor : StraightThrough or BackToBack
    warnings : list of str
    """

    def step(fraction, message):
        if cancelled is not None and cancelled():
            raise Cancelled()
        if progress is not None:
            progress(fraction, message)

    data = read_inputs(app_type, state)
    opts = data["options"]
    step(0.02, "Calculating guarantee point...")
    built = []
    n_points = sum(len(points) for _, _, points in data["sections"])
    done = 0
    for sec, guarantee, points in data["sections"]:
        guarantee_point = _guarantee_point(guarantee, opts)
        test_points = []
        for i, values in points:
            label = f"{sec.title.lower()} point {i}" if sec.name else f"test point {i}"
            step(0.05 + 0.25 * done / max(n_points, 1), f"Calculating {label}...")
            test_points.append(_test_point(values, sec))
            done += 1
        built.append((guarantee_point, test_points))

    step(0.35, "Converting points...")
    if app_type == "straight_through":
        ((guarantee_point, test_points),) = built
        compressor = StraightThrough(
            guarantee_point=guarantee_point,
            test_points=test_points,
            reynolds_correction=opts.reynolds_correction,
            bearing_mechanical_losses=opts.bearing_mechanical_losses,
        )
    else:
        (g1, t1), (g2, t2) = built
        compressor = BackToBack(
            guarantee_point_sec1=g1,
            guarantee_point_sec2=g2,
            test_points_sec1=t1,
            test_points_sec2=t2,
            reynolds_correction=opts.reynolds_correction,
            bearing_mechanical_losses=opts.bearing_mechanical_losses,
        )
    if calculate_speed:
        step(0.7, "Finding speed to match discharge pressure...")
        compressor = compressor.calculate_speed_to_match_discharge_pressure()
    step(1.0, "Done")
    return compressor, data["warnings"]


def load_compressor(app_type, toml_text):
    import toml

    cls = StraightThrough if app_type == "straight_through" else BackToBack
    return cls.from_dict(toml.loads(toml_text))


def dump_compressor(compressor):
    import toml

    return toml.dumps(compressor.to_dict())


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


def _r(x):
    return None if x is None else round(float(x), 5)


def interpolated_point(compressor, sec):
    guarantee = getattr(compressor, sec.attr("guarantee_point"))
    method = "point" if sec.sec is None else f"point_{sec.sec}"
    return getattr(compressor, method)(
        flow_v=guarantee.flow_v, speed=compressor.speed_operational
    )


def _guarantee_power_kw(state, sec, which):
    """Data sheet power (``power`` or ``power_shaft``) in kW, or None."""
    r = StateReader(state)
    value = r.quantity(
        sec.ds_value(which), state.get(sec.ds_unit(which)), required=False
    )
    return None if value is None or r.errors else value.to("kW").m


def results_table(compressor, state, sec, point_interpolated=None, all_points=None):
    """The PTC 10 results table of one section.

    Returns a JSON-serialisable dict with ``columns``, ``rows`` (label and
    values), ``checks`` (pass/fail of the highlighted cells) and the column
    formats.
    """
    opts = Options.from_state(state)
    g = getattr(compressor, sec.attr("guarantee_point"))
    test_points = getattr(compressor, sec.attr("test_points"))
    flange_sp = getattr(compressor, sec.attr("points_flange_sp"))
    flange_t = getattr(compressor, sec.attr("points_flange_t"))
    rotor_t = getattr(compressor, sec.attr("points_rotor_t"))
    rotor_sp = getattr(compressor, sec.attr("points_rotor_sp"))
    pi = point_interpolated or interpolated_point(compressor, sec)

    shaft_kw = _guarantee_power_kw(state, sec, "power_shaft")
    gas_kw = _guarantee_power_kw(state, sec, "power")
    power_ref = shaft_kw if (opts.bearing_mechanical_losses and shaft_kw) else gas_kw

    def ratio(a, b):
        return None if (a is None or not b) else a / b

    g_head = g.head.to("kJ/kg").m
    g_flow = g.flow_v.to("m³/h").m
    g_pd = g.disch.p("bar").m

    def row(t, fsp, ft, rt, rsp):
        head_t = ft.head.to("kJ/kg").m
        return [
            _r(t.phi.m),
            _r(t.phi.m / g.phi.m),
            _r(t.volume_ratio.m),
            _r(t.volume_ratio.m / g.volume_ratio.m),
            _r(t.mach.m),
            _r(t.mach.m - g.mach.m),
            _r(t.reynolds.m),
            _r(t.reynolds.m / g.reynolds.m),
            _r(fsp.disch.p("bar").m),
            _r(fsp.disch.p("bar").m / g_pd),
            _r(head_t),
            _r(t.head.to("kJ/kg").m / g_head),
            _r(fsp.head.to("kJ/kg").m),
            _r(fsp.head.to("kJ/kg").m / g_head),
            _r(fsp.flow_v.to("m³/h").m),
            _r(fsp.flow_v.to("m³/h").m / g_flow),
            _r(rt.power_shaft.to("kW").m),
            _r(ratio(rt.power_shaft.to("kW").m, power_ref)),
            _r(rsp.power_shaft.to("kW").m),
            _r(ratio(rsp.power_shaft.to("kW").m, power_ref)),
            _r(ft.eff.m),
            _r(fsp.eff.m),
        ]

    rows = []
    for n, (t, fsp, ft, rt, rsp) in enumerate(
        zip(test_points, flange_sp, flange_t, rotor_t, rotor_sp), start=1
    ):
        rows.append({"label": f"Point {n}", "values": row(t, fsp, ft, rt, rsp)})

    pi_head = pi.head.to("kJ/kg").m
    pi_power = pi.power_shaft.to("kW").m
    rows.append(
        {
            "label": GUARANTEE,
            "values": [
                _r(pi.phi.m),
                _r(pi.phi.m / g.phi.m),
                _r(pi.volume_ratio.m),
                _r(pi.volume_ratio.m / g.volume_ratio.m),
                _r(pi.mach.m),
                _r(pi.mach.m - g.mach.m),
                _r(pi.reynolds.m),
                _r(pi.reynolds.m / g.reynolds.m),
                _r(pi.disch.p("bar").m),
                _r(pi.disch.p("bar").m / g_pd),
                _r(pi_head),
                _r(pi_head / g_head),
                _r(pi_head),
                _r(pi_head / g_head),
                _r(pi.flow_v.to("m³/h").m),
                _r(pi.flow_v.to("m³/h").m / g_flow),
                None,
                None,
                _r(pi_power),
                _r(ratio(pi_power, power_ref)),
                _r(pi.eff.m),
                _r(pi.eff.m),
            ],
        }
    )

    if sec.name is not None and all_points is not None:
        rows.append(
            {
                "label": OVERALL,
                "values": _overall_row(compressor, state, opts, all_points),
            }
        )

    if opts.variable_speed:
        power_limit, pressure_limit = 1.04, None
    else:
        power_limit, pressure_limit = 1.07, 1.05

    mach = pi.mach_limits()
    reynolds = pi.reynolds_limits()
    checks = []

    def check(row_label, column, lower, upper):
        idx = COLUMNS.index(column)
        for rw in rows:
            if rw["label"] != row_label:
                continue
            value = rw["values"][idx]
            if value is None:
                return
            ok = value >= lower and (upper is None or value <= upper)
            checks.append(
                {
                    "row": row_label,
                    "column": column,
                    "ok": bool(ok),
                    "lower": lower,
                    "upper": upper,
                }
            )

    check(GUARANTEE, f"Mach{T_}", float(mach["lower"]), float(mach["upper"]))
    check(GUARANTEE, f"Re{T_}", float(reynolds["lower"]), float(reynolds["upper"]))
    check(GUARANTEE, f"(vi/vd){T_}/(vi/vd){SP}", 0.95, 1.05)
    check(GUARANTEE, f"φ{T_} / φ{SP}", 0.96, 1.04)
    for row_label in [GUARANTEE] + ([OVERALL] if sec.name else []):
        check(row_label, f"pd{CONV}/pd{SP}", 1.0, pressure_limit)
        check(row_label, f"W{CONV}/W{SP}", 0.0, power_limit)

    return {
        "key": sec.sec or "results",
        "title": sec.title,
        "columns": COLUMNS,
        "rows": rows,
        "checks": checks,
        "percent": sorted(PERCENT_COLUMNS),
        "scientific": sorted(SCIENTIFIC_COLUMNS),
        "speed_operational_rpm": float(compressor.speed_operational.to("rpm").m),
    }


def _overall_row(compressor, state, opts, points):
    """Back-to-back overall row: section 2 discharge and summed power."""
    p1, p2 = points
    values = [None] * len(COLUMNS)
    g2 = compressor.guarantee_point_sec2
    values[COLUMNS.index(f"pd{CONV} (bar)")] = _r(p2.disch.p("bar").m)
    values[COLUMNS.index(f"pd{CONV}/pd{SP}")] = _r(
        p2.disch.p("bar").m / g2.disch.p("bar").m
    )
    total = p1.power.to("kW").m + p2.power.to("kW").m
    if opts.bearing_mechanical_losses:
        total += max(p1.power_losses.to("kW").m, p2.power_losses.to("kW").m)
        which = "power_shaft"
    else:
        which = "power"
    refs = [_guarantee_power_kw(state, sec, which) for sec in sections("back_to_back")]
    if opts.bearing_mechanical_losses and not all(refs):
        refs = [
            _guarantee_power_kw(state, sec, "power") for sec in sections("back_to_back")
        ]
    values[COLUMNS.index(f"W{CONV} (kW)")] = _r(total)
    if all(refs):
        values[COLUMNS.index(f"W{CONV}/W{SP}")] = _r(total / sum(refs))
    return values


def results(app_type, compressor, state):
    """Tables for every section of a calculated compressor."""
    secs = sections(app_type)
    points = [interpolated_point(compressor, sec) for sec in secs]
    return [
        results_table(
            compressor,
            state,
            sec,
            point_interpolated=p,
            all_points=points if len(secs) > 1 else None,
        )
        for sec, p in zip(secs, points)
    ]


def table_to_excel(table):
    """Excel bytes of one results table, with the PTC 10 cells coloured."""
    df = pd.DataFrame(
        [r["values"] for r in table["rows"]],
        index=[r["label"] for r in table["rows"]],
        columns=table["columns"],
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1")
        book = writer.book
        sheet = writer.sheets["Sheet1"]
        percent = book.add_format({"num_format": "0.00%"})
        scientific = book.add_format({"num_format": "0.0000E+00"})
        good = {"bg_color": "#C8E6C9", "font_color": "#33691E"}
        bad = {"bg_color": "#FFCDD2", "font_color": "#B71C1C"}
        for j, column in enumerate(table["columns"], start=1):
            if column in PERCENT_COLUMNS:
                sheet.set_column(j, j, 14, percent)
            elif column in SCIENTIFIC_COLUMNS:
                sheet.set_column(j, j, 14, scientific)
            else:
                sheet.set_column(j, j, 14)
        labels = [r["label"] for r in table["rows"]]
        for c in table["checks"]:
            i = labels.index(c["row"]) + 1
            j = table["columns"].index(c["column"]) + 1
            value = df.loc[c["row"], c["column"]]
            fmt = dict(good if c["ok"] else bad)
            if c["column"] in PERCENT_COLUMNS:
                fmt["num_format"] = "0.00%"
            elif c["column"] in SCIENTIFIC_COLUMNS:
                fmt["num_format"] = "0.0000E+00"
            sheet.write_number(i, j, float(value), book.add_format(fmt))
    return buffer.getvalue()


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------


def _curve_settings(state, sec, curve):
    prefix = sec.curve_prefix(curve)
    return {
        "x": {
            "lower_limit": state.get(f"x_{prefix}_lower", ""),
            "upper_limit": state.get(f"x_{prefix}_upper", ""),
            "units": state.get(f"x_{prefix}_flow_units") or "m³/h",
        },
        "y": {
            "lower_limit": state.get(f"y_{prefix}_lower", ""),
            "upper_limit": state.get(f"y_{prefix}_upper", ""),
            "units": state.get(f"y_{prefix}_units", ""),
        },
    }


def _limits_complete(limits):
    try:
        values = [
            float(limits[a][b])
            for a in ("x", "y")
            for b in ("lower_limit", "upper_limit")
        ]
    except (TypeError, ValueError, KeyError):
        return None
    return values


def figures(app_type, compressor, state, sec, point_interpolated=None):
    """Plotly figures of one section: Mach, Reynolds and the four curves.

    Returns ``{name: plotly Figure}`` plus the axis limits used by the curve
    image overlays (``limits[curve]``).
    """
    opts = Options.from_state(state)
    pi = point_interpolated or interpolated_point(compressor, sec)
    base = (
        compressor
        if sec.sec is None
        else getattr(compressor, f"imp_flange_sp_{sec.sec}")
    )
    figs = {"mach": pi.plot_mach(), "reynolds": pi.plot_reynolds()}
    limits = {}
    speed_rpm = compressor.speed_operational.to("rpm").m
    for curve in schemas.CURVES:
        settings = _curve_settings(state, sec, curve)
        limits[curve] = settings
        flow_v_units = settings["x"]["units"]
        curve_units = settings["y"]["units"]
        kwargs = {}
        if flow_v_units:
            kwargs["flow_v_units"] = flow_v_units
        if curve_units:
            kwargs["p_units" if curve == "discharge_pressure" else f"{curve}_units"] = (
                curve_units
            )
        method = "disch.p" if curve == "discharge_pressure" else curve
        fig = r_getattr(base, f"{method}_plot")(show_points=opts.show_points, **kwargs)
        fig = r_getattr(pi, f"{method}_plot")(
            fig=fig, show_points=opts.show_points, **kwargs
        )
        fig.data[0].update(name=f"Converted Curve {speed_rpm:.0f} RPM")
        if curve == "discharge_pressure":
            y_value = r_getattr(pi, method)(curve_units or "Pa")
        else:
            y_value = r_getattr(pi, method)
            if curve_units:
                y_value = y_value.to(curve_units)
        label = (
            f"Flow: {pi.flow_v.to(flow_v_units or 'm³/h'):.~2f}, "
            f"{curve.capitalize()}: {y_value:.~2f}"
        )
        if len(fig.data) > 1:
            fig.data[1].update(
                name=label.replace("m ** 3 / h", "m³/h").replace(
                    "Discharge_pressure", "Disch. p"
                )
            )
        fig.update_layout(
            showlegend=True,
            legend=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01),
        )
        values = _limits_complete(settings)
        if values:
            x0, x1, y0, y1 = values
            fig.update_layout(xaxis_range=(x0, x1), yaxis_range=(y0, y1))
        figs[curve] = fig
    return figs, limits


def add_background_image(fig, limits, source):
    """Stretch a curve image (URL or data URI) over the given axis limits."""
    values = _limits_complete(limits)
    if not values:
        return fig
    x0, x1, y0, y1 = values
    fig.add_layout_image(
        dict(
            source=source,
            xref="x",
            yref="y",
            x=x0,
            y=y1,
            sizex=x1 - x0,
            sizey=y1 - y0,
            sizing="stretch",
            opacity=0.5,
            layer="below",
        )
    )
    return fig


# --------------------------------------------------------------------------
# Orifice flow: the test flow of a section whose flow method is "Orifice"
# --------------------------------------------------------------------------

ORIFICE_REQUIRED = [
    "outer_diameter_fo",
    "inner_diameter_fo",
    "upstream_pressure_fo",
    "upstream_temperature_fo",
    "pressure_drop_fo",
]


def orifice_sections(app_type, state):
    return [s for s in sections(app_type) if state.get(s.flow_method) == "Orifice"]


def switch_flow_method(app_type, old, new):
    """State updates for sections whose flow method changed.

    Switching to "Orifice" keeps the measured flows and their unit aside
    (``flow_measured_*``); switching back to "Direct" restores them.
    """
    updates = {}
    for sec in sections(app_type):
        before = old.get(sec.flow_method) or "Direct"
        after = new.get(sec.flow_method) or "Direct"
        if before == after:
            continue
        pairs = [(sec.tp_unit("flow"), sec.tp_unit("flow_measured"))] + [
            (sec.tp_value("flow", i), sec.tp_value("flow_measured", i))
            for i in range(1, schemas.N_POINTS + 1)
        ]
        if after == "Orifice":
            # The unit select may already hold the orifice (mass) unit.
            updates.update({kept: old.get(key, "") for key, kept in pairs})
        elif new.get(sec.tp_unit("flow_measured")):
            updates.update({key: new.get(kept, "") for key, kept in pairs})
            updates.update({kept: "" for _, kept in pairs})
    return updates


def orifice_flows(app_type, state, strict=False):
    """Test flows calculated from the orifice plate data (ISO 5167).

    For every section in "Orifice" mode, the flow of each test point is the
    orifice mass flow, in the section's flow unit, using the point's gas.
    A point without orifice data gets a blank flow.

    Returns ``(updates, errors)``: state values to store and ``{key:
    message}``. With ``strict`` (before a calculation) a partly filled point
    is an error on its blank fields; otherwise (while typing) its flow is
    just left blank.
    """
    r = StateReader(state)
    updates = {}
    errors = {}
    for sec in orifice_sections(app_type, state):
        flow_unit = state.get(sec.tp_unit("flow")) or ""
        if not is_mass_flow_unit(flow_unit):
            errors[sec.tp_unit("flow")] = "The orifice flow needs a mass flow unit"
            continue
        for i in range(1, schemas.N_POINTS + 1):
            flow_key = sec.tp_value("flow", i)
            keys = {p: sec.fo_value(p, i) for p in ORIFICE_REQUIRED}
            blank = [p for p, k in keys.items() if r.is_blank(k)]
            if blank:
                updates[flow_key] = ""
                if strict and len(blank) < len(keys):
                    for p in blank:
                        errors[keys[p]] = "Required for the orifice flow"
                continue
            values = {
                p: r.quantity(k, state.get(sec.fo_unit(p))) for p, k in keys.items()
            }
            fluid = _fluid(r, state, sec.tp_gas(i))
            if r.errors:
                errors.update(r.errors)
                r.errors.clear()
                updates[flow_key] = ""
                continue
            try:
                fo = ccp.FlowOrifice(
                    state=ccp.State(
                        p=values["upstream_pressure_fo"],
                        T=values["upstream_temperature_fo"],
                        fluid=fluid,
                    ),
                    delta_p=values["pressure_drop_fo"],
                    D=values["outer_diameter_fo"],
                    d=values["inner_diameter_fo"],
                    tappings=state.get(sec.fo_value("tappings_fo", i)) or "flange",
                )
                qm = fo.qm
            except Exception as exc:  # flash or ISO 5167 range failure
                errors[flow_key] = f"Orifice flow failed: {exc}"
                updates[flow_key] = ""
                continue
            updates[flow_key] = f"{qm.to(flow_unit).m:.6g}"
            if sec.name is None:
                # Streamlit's result row, so its files stay consistent.
                fo_unit = state.get("mass_flow_fo_units") or "kg/h"
                updates[f"mass_flow_fo_{i}"] = str(round(qm.to(fo_unit).m, 5))
    return updates, errors
