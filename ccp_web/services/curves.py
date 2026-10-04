"""Design-case curves: Engauge loading, conversion to new suction conditions,
and the impeller plots of the curves conversion page.

Follows ``ccp/app/common.py`` (``curves_upload_section``) and
``ccp/app/pages/3_curves_conversion.py``. Run inside ``units.calculation_context``.
"""

import tempfile
from pathlib import Path

import toml

import ccp
from ccp import Q_

from . import gas, schemas
from .units import InputError, flow_v_units

ENGAUGE_SUFFIXES = ["head", "eff", "power", "power_shaft"]


def extract_curve_name(filename):
    name = filename.rsplit(".", 1)[0]
    for suffix in ENGAUGE_SUFFIXES:
        if name.endswith(f"-{suffix}"):
            return name[: -len(f"-{suffix}")]
    return name


def design_suction_state(state, case):
    """Suction state of design case ``case`` (A..E)."""
    errors = {}
    gas_name = state.get(f"gas_case_{case}")
    fluid = gas.composition(state, gas_name)
    if not fluid:
        errors[f"gas_case_{case}"] = (
            f"No gas composition found for {gas_name}. Please define molar fractions."
        )
    p = state.get(f"suc_p_case_{case}") or 0
    T = state.get(f"suc_T_case_{case}") or 0
    if not p or float(p) <= 0:
        errors[f"suc_p_case_{case}"] = (
            f"Please define valid suction conditions for Case {case}"
        )
    if not T or float(T) <= 0:
        errors[f"suc_T_case_{case}"] = (
            f"Please define valid suction conditions for Case {case}"
        )
    if errors:
        raise InputError(errors)
    return ccp.State(
        p=Q_(float(p), state.get("design_suc_p_unit") or "bar"),
        T=Q_(float(T), state.get("design_suc_T_unit") or "degC"),
        fluid=fluid,
    )


def load_design_case(state, case, csv_files):
    """``Impeller.load_from_engauge_csv`` for one design case.

    Parameters
    ----------
    csv_files : list of (name, bytes)
        The two Engauge CSVs of the case (``<curve>-head.csv``,
        ``<curve>-eff.csv``, or power files).

    Returns
    -------
    impeller : ccp.Impeller
    curve_name : str
    """
    if len(csv_files) < 2:
        raise InputError(
            {
                f"curves_file_1_case_{case}": (
                    f"Please upload both curve files for Case {case}"
                )
            }
        )
    suc = design_suction_state(state, case)
    curve_name = extract_curve_name(csv_files[0][0])
    with tempfile.TemporaryDirectory(prefix="ccp-engauge-") as tmp:
        path = Path(tmp)
        for name, content in csv_files:
            (path / name).write_bytes(content)
        impeller = ccp.Impeller.load_from_engauge_csv(
            suc=suc,
            curve_name=curve_name,
            curve_path=path,
            flow_units=state.get("loaded_curves_flow_units") or "m³/h",
            head_units=state.get("loaded_curves_head_units") or "kJ/kg",
            power_units=state.get("loaded_curves_power_units") or "kW",
            speed_units=state.get("loaded_curves_speed_units") or "rpm",
            disch_p_units=state.get("loaded_curves_disch_p_units") or "bar",
            disch_T_units=state.get("loaded_curves_disch_T_units") or "degK",
        )
    return impeller, curve_name


def new_suction_state(state):
    errors = {}
    p = float(state.get("new_suc_p") or 0)
    T = float(state.get("new_suc_t") or 0)
    if p <= 0:
        errors["new_suc_p"] = "Please fill in all new suction condition values"
    if T <= 0:
        errors["new_suc_t"] = "Please fill in all new suction condition values"
    gas_name = state.get("new_gas_selection")
    fluid = gas.composition(state, gas_name)
    if not fluid:
        errors["new_gas_selection"] = f"Gas '{gas_name}' has no composition"
    if errors:
        raise InputError(errors)
    return ccp.State(
        p=Q_(p, state.get("new_suc_p_unit") or "bar"),
        T=Q_(T, state.get("new_suc_t_unit") or "degC"),
        fluid=fluid,
    )


def convert(state, impellers):
    """Convert the loaded design cases to the new suction conditions.

    Parameters
    ----------
    impellers : dict
        ``{case: Impeller}`` of the loaded design cases.

    Returns
    -------
    converted : ccp.Impeller
    note : str
        Which case(s) the conversion started from.
    """
    if not impellers:
        raise InputError(
            {
                "impeller_case_A": "Please load at least one design case "
                "before converting. "
                "Upload curves in the 'Performance Curves Upload' section."
            }
        )
    suc = new_suction_state(state)
    cases = sorted(impellers)
    if len(cases) == 1:
        original = impellers[cases[0]]
        note = f"Converted from case {cases[0]} to the target conditions."
    else:
        original = [impellers[c] for c in cases]
        note = (
            f"Multiple design cases loaded ({', '.join(cases)}). "
            "ccp picked the closest case based on speed of sound."
        )
    speed = None if state.get("conv_speed_option") == "calculate" else "same"
    converted = ccp.Impeller.convert_from(
        original_impeller=original,
        suc=suc,
        find=state.get("conv_find_method") or "speed",
        speed=speed,
    )
    return converted, note


def load_impeller(toml_text):
    return ccp.Impeller.from_dict(toml.loads(toml_text))


def dump_impeller(impeller):
    return toml.dumps(impeller.to_dict())


def impeller_info(impeller):
    speeds = [p.speed.to("rpm").m for p in impeller.points]
    flows = [p.flow_v.to("m³/h").m for p in impeller.points]
    return {
        "n_points": len(impeller.points),
        "n_curves": len(impeller.curves),
        "speed_min": min(speeds),
        "speed_max": max(speeds),
        "flow_min": min(flows),
        "flow_max": max(flows),
    }


def plot_units(state):
    flow = state.get("plot_curves_flow_units") or "m³/h"
    return {
        "speed": state.get("plot_curves_speed_units") or "rpm",
        "flow": flow,
        "flow_v": flow if flow in flow_v_units else "m³/h",
        "disch_p": state.get("plot_curves_disch_p_units") or "bar",
        "disch_T": state.get("plot_curves_disch_T_units") or "degK",
        "head": state.get("plot_curves_head_units") or "kJ/kg",
        "power": state.get("plot_curves_power_units") or "kW",
    }


def operating_point(impeller, state, prefix):
    """Flow and speed the plots of ``prefix`` are drawn at, in plot units."""
    u = plot_units(state)
    flow = state.get(f"{prefix}_flow_input")
    speed = state.get(f"{prefix}_speed_input")
    if flow in (None, ""):
        flow = impeller.points[0].flow_v.to(u["flow_v"]).m
    if speed in (None, ""):
        speed = impeller.points[0].speed.to(u["speed"]).m
    return float(flow), float(speed)


def impeller_view(impeller, state, prefix):
    """The five plots and the point summary for one impeller.

    Returns ``(figures, summary)``: ``figures`` maps head, eff, power,
    disch_T, disch_p to plotly figures; ``summary`` is a dict of display
    values for the interpolated point.
    """
    u = plot_units(state)
    flow, speed = operating_point(impeller, state, prefix)
    similarity = bool(state.get(f"{prefix}_show_similarity"))
    flow_q = Q_(flow, u["flow_v"])
    speed_q = Q_(speed, u["speed"])
    common = dict(
        flow_v_units=u["flow_v"], flow_v=flow_q, speed=speed_q, similarity=similarity
    )
    figs = {
        "head": impeller.head_plot(head_units=u["head"], **common),
        "eff": impeller.eff_plot(**common),
        "power": impeller.power_plot(power_units=u["power"], **common),
        "disch_T": impeller.disch.T_plot(T_units=u["disch_T"], **common),
        "disch_p": impeller.disch.p_plot(p_units=u["disch_p"], **common),
    }
    point = impeller.point(flow_v=flow_q, speed=speed_q)
    gas_items = sorted(
        (
            (comp.lower(), float(frac) * 100)
            for comp, frac in point.suc.fluid.items()
            if float(frac) > 0
        ),
        key=lambda kv: kv[1],
        reverse=True,
    )
    summary = {
        "flow": flow,
        "speed": speed,
        "similarity": similarity,
        "units": u,
        "rows": [
            ("Speed", f"{point.speed.to(u['speed']).m:.0f}", u["speed"]),
            ("Flow", f"{point.flow_v.to(u['flow_v']).m:.2f}", u["flow_v"]),
            ("Head", f"{point.head.to(u['head']).m:.2f}", u["head"]),
            ("Eff", f"{point.eff.m * 100:.2f}", "%"),
            ("Power", f"{point.power.to(u['power']).m:.2f}", u["power"]),
            ("Suction pressure", f"{point.suc.p(u['disch_p']).m:.2f}", u["disch_p"]),
            ("Suction temperature", f"{point.suc.T(u['disch_T']).m:.2f}", u["disch_T"]),
            (
                "Discharge pressure",
                f"{point.disch.p(u['disch_p']).m:.2f}",
                u["disch_p"],
            ),
            (
                "Discharge temperature",
                f"{point.disch.T(u['disch_T']).m:.2f}",
                u["disch_T"],
            ),
        ],
        "gas": gas_items,
    }
    return figs, summary


def loaded_cases(case_impellers):
    return [c for c in schemas.CASES if case_impellers.get(c) is not None]
