"""Agent adapter of the curves conversion page.

See ``ccp_web.agent.adapters`` for the interface. The page has two buttons,
so ``start`` takes an ``action``: ``convert`` (the Convert button,
``views.start_conversion``) or ``load`` with a design case ``letter`` (the
Load button of that case, ``views.start_load``). Results and figures come
from the stored impeller TOMLs through the same services as the page's
design-case table and plot panels. Every number carries its units: a value
is ``{"value", "units"}`` or its block has a ``units`` map.
"""

from ccp import Q_
from ccp_web.agent.adapters import json_safe
from ccp_web.core.models import Job
from ccp_web.services import curves, gas, schemas, units

from .views import PANELS, design_cases, load_impeller, start_conversion, start_load

ACTIONS = ("convert", "load")
PARAMS = {
    "action": (
        "'convert' (default): convert the loaded design cases to the new "
        "suction conditions (the Convert button); 'load': load the Engauge "
        "curves of one design case (its Load button, needs 'letter')"
    ),
    "letter": f"design case to load with action 'load': one of {schemas.CASES}",
}
# The plots of every panel, in the page's order (``curves.impeller_view``).
FIGURES = [
    ("head", "Head"),
    ("eff", "Efficiency"),
    ("power", "Power"),
    ("disch_T", "Discharge temperature"),
    ("disch_p", "Discharge pressure"),
]
INFO_UNITS = {"speed": "rpm", "flow": "m³/h"}  # what ``curves.impeller_info`` uses
IMPELLER_KEYS = ["converted_impeller"] + [f"impeller_case_{c}" for c in schemas.CASES]


def start(case, params):
    """Start a load or conversion job.

    ``params``: ``{action: "convert"}`` (the default) or ``{action: "load",
    letter: "A"}``.
    """
    params = dict(params or {})
    unknown = sorted(set(params) - set(PARAMS))
    if unknown:
        raise ValueError(f"unknown params {unknown}; expected {sorted(PARAMS)}")
    action = params.get("action") or "convert"
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {list(ACTIONS)}, got {action!r}")
    if action == "convert":
        if "letter" in params:
            raise ValueError("'letter' is only used with action 'load'")
        return start_conversion(case)
    letter = params.get("letter")
    if not isinstance(letter, str) or letter.strip().upper() not in schemas.CASES:
        raise ValueError(
            f"action 'load' needs 'letter', one of {schemas.CASES}; got {letter!r}"
        )
    return start_load(case, letter.strip().upper())


def has_results(case):
    return case.artifacts.filter(key__in=IMPELLER_KEYS).exists()


def _quantity(value, unit):
    return {"value": value, "units": unit}


def _last_job(case, kind):
    return Job.objects.filter(case=case, kind=kind).order_by("-created").first()


def _job(job):
    if job is None:
        return None
    out = {
        "id": job.pk,
        "status": job.status,
        "message": job.message,
        "warnings": list(job.warnings or []),
    }
    if job.status == Job.FAILED:
        out["error"] = job.error
        out["errors"] = (job.result or {}).get("errors") or {}
    return out


def _info(impeller):
    """``curves.impeller_info`` plus the curve speeds, with its units."""
    info = curves.impeller_info(impeller)
    info["curve_speeds"] = sorted(
        c.speed.to(INFO_UNITS["speed"]).m for c in impeller.curves
    )
    info["units"] = dict(INFO_UNITS)
    return info


def operating_point(impeller, state, prefix):
    """The point the plots of panel ``prefix`` are drawn at, as numbers.

    The same point as the page's point summary (``curves.impeller_view``):
    the flow and speed typed in ``<prefix>_flow_input`` /
    ``<prefix>_speed_input``, else the impeller's first point, in the plot
    units. ``{"error"}`` when the point cannot be interpolated (e.g. a flow
    outside the curves).
    """
    u = curves.plot_units(state)
    try:
        flow, speed = curves.operating_point(impeller, state, prefix)
        point = impeller.point(
            flow_v=Q_(flow, u["flow_v"]), speed=Q_(speed, u["speed"])
        )
        out = {
            "flow_input_key": f"{prefix}_flow_input",
            "speed_input_key": f"{prefix}_speed_input",
            "speed": _quantity(point.speed.to(u["speed"]).m, u["speed"]),
            "flow_v": _quantity(point.flow_v.to(u["flow_v"]).m, u["flow_v"]),
            "head": _quantity(point.head.to(u["head"]).m, u["head"]),
            "eff": _quantity(point.eff.to("dimensionless").m, "fraction"),
            "power": _quantity(point.power.to(u["power"]).m, u["power"]),
            "suction_pressure": _quantity(point.suc.p(u["disch_p"]).m, u["disch_p"]),
            "suction_temperature": _quantity(point.suc.T(u["disch_T"]).m, u["disch_T"]),
            "discharge_pressure": _quantity(
                point.disch.p(u["disch_p"]).m, u["disch_p"]
            ),
            "discharge_temperature": _quantity(
                point.disch.T(u["disch_T"]).m, u["disch_T"]
            ),
            "gas_mol_fractions": {
                comp.lower(): float(frac)
                for comp, frac in point.suc.fluid.items()
                if float(frac) > 0
            },
        }
    except Exception as exc:  # the page shows the same error in the panel
        return {"error": str(exc)}
    return out


def _design_case(case, row):
    letter = row["letter"]
    state = case.state
    out = {
        "letter": letter,
        "loaded": row["info"] is not None,
        "curve_name": row["curve_name"] or None,
        "gas": state.get(row["gas_key"]),
        "suction_pressure": _quantity(
            state.get(row["p_key"]), state.get("design_suc_p_unit") or "bar"
        ),
        "suction_temperature": _quantity(
            state.get(row["T_key"]), state.get("design_suc_T_unit") or "degC"
        ),
        "files": {
            slot["key"]: slot["file"].name if slot["file"] else None
            for slot in row["slots"]
        },
        "load_job": _job(row["job"]),
    }
    if out["loaded"]:
        impeller = load_impeller(case, f"impeller_case_{letter}")
        out["info"] = _info(impeller)
        out["operating_point"] = operating_point(impeller, state, f"orig_case_{letter}")
    return out


def _converted(case):
    artifact = case.artifact("converted_impeller")
    job = _last_job(case, "convert_curves")
    if artifact is None:
        reason = "not converted yet: POST calculate {params: {action: 'convert'}}"
        if job is not None and job.status == Job.FAILED:
            reason = f"the last conversion failed: {job.error}"
        return {"available": False, "reason": reason, "job": _job(job)}
    impeller = load_impeller(case, "converted_impeller")
    # The job itself saves state after the artifact (it resets the panel's
    # operating point), so compare with when it finished.
    done = artifact.created
    if job is not None and job.status == Job.SUCCEEDED and job.finished:
        done = max(done, job.finished)
    return {
        "available": True,
        "info": _info(impeller),
        "operating_point": operating_point(impeller, case.state, "converted"),
        "calculated": artifact.created,
        "inputs_saved_after_calculation": case.updated > done,
        "job": _job(job),
    }


def results(case):
    """Loaded design cases, the conversion target and the converted impeller.

    ``design_cases`` lists all five cases (A-E) with their inputs and, when
    loaded, the impeller info and operating point; ``converted`` is the
    conversion result. ``plot_units`` are the units of the operating points.
    """
    state = case.state
    with units.state_context(state):
        rows = [_design_case(case, row) for row in design_cases(case)]
        converted = _converted(case)
    loaded = [r["letter"] for r in rows if r["loaded"]]
    out = {
        "available": bool(loaded) or converted["available"],
        "app_type": case.app_type,
        "loaded_cases": loaded,
        "design_cases": rows,
        "target": {
            "gas": state.get("new_gas_selection"),
            "gas_defined": bool(gas.composition(state, state.get("new_gas_selection"))),
            "suction_pressure": _quantity(
                state.get("new_suc_p"), state.get("new_suc_p_unit") or "bar"
            ),
            "suction_temperature": _quantity(
                state.get("new_suc_t"), state.get("new_suc_t_unit") or "degC"
            ),
            "find_method": state.get("conv_find_method") or "speed",
            "speed_option": state.get("conv_speed_option") or "same",
        },
        "converted": converted,
        "plot_units": curves.plot_units(state),
    }
    if not out["available"]:
        out["reason"] = (
            "no design case loaded yet: upload the two Engauge CSVs of a case "
            "in the browser, then POST calculate {params: {action: 'load', "
            "letter: 'A'}}"
        )
    return json_safe(out)


def _panels(case):
    """``(prefix, artifact key, label)`` of the panels that have an impeller."""
    keys = set(
        case.artifacts.filter(key__in=IMPELLER_KEYS).values_list("key", flat=True)
    )
    return [
        (prefix, key, label) for prefix, (key, label) in PANELS.items() if key in keys
    ]


def figures(case):
    """The plots of the converted panel and of every loaded design case."""
    return [
        {"id": f"{prefix}_{name}", "title": f"{title} ({label})", "section": prefix}
        for prefix, _, label in _panels(case)
        for name, title in FIGURES
    ]


def figure(case, figure_id):
    """One plot of a panel, at the panel's operating point."""
    for prefix, (key, _) in PANELS.items():
        for name, _ in FIGURES:
            if figure_id == f"{prefix}_{name}":
                impeller = load_impeller(case, key)
                if impeller is None:
                    raise KeyError(figure_id)
                try:
                    with units.state_context(case.state):
                        figs, _ = curves.impeller_view(impeller, case.state, prefix)
                except Exception as exc:  # e.g. a point outside the curves
                    raise ValueError(
                        f"cannot plot {figure_id}: {exc}; check {prefix}_flow_input "
                        f"and {prefix}_speed_input"
                    ) from exc
                return figs[name]
    raise KeyError(figure_id)
