"""Fleet analysis: compressors of one design in a hierarchical Bayesian model.

Wraps ``ccp.analytics.fleet``. Each member is a performance-evaluation case
(the unit's field data) with an optional straight-through case (its shop
test). The job loads the evaluations, turns them into observation tables,
fits the model with PyMC and stores the fitted fleet (``fleet.zip``) and a
results JSON (``Fleet.to_dict`` plus figures) that the page renders without
PyMC.

Loading cases is Django's business: :func:`observations` takes loader
callables, so this module stays free of Django.
"""

import json
import tempfile
from pathlib import Path

import pandas as pd

from ccp import Q_

from .evaluation import fig_json
from .units import InputError

INSTALL_HINT = "pip install ccp-performance[bayes]"
PROB = 0.9
SCATTER_LABELS = {
    "mu_flow": ("Fleet mean, flow capacity", "%"),
    "mu_head": ("Fleet mean, head", "%"),
    "mu_eff": ("Fleet mean, efficiency", "points"),
    "tau_unit_flow": ("Manufacturing scatter, flow capacity", "%"),
    "tau_unit_head": ("Manufacturing scatter, head", "%"),
    "tau_unit_eff": ("Manufacturing scatter, efficiency", "points"),
    "tau_install_head": ("Installation scatter, head", "%"),
    "tau_install_eff": ("Installation scatter, efficiency", "points"),
    "tau_site_head": ("Site scatter, head", "%"),
    "tau_site_eff": ("Site scatter, efficiency", "points"),
    "mu_rate_head": ("Mean degradation rate, head", "%/1000 h"),
    "mu_rate_eff": ("Mean degradation rate, efficiency", "points/1000 h"),
    "tau_rate_head": ("Rate scatter, head", "%/1000 h"),
    "tau_rate_eff": ("Rate scatter, efficiency", "points/1000 h"),
}
MAX_RHAT = 1.01
# interval columns of the unit table, in order
INTERVAL_COLUMNS = [
    "current_eff",
    "current_head",
    "asbuilt_eff",
    "asbuilt_head",
    "asbuilt_flow",
    "rate_eff",
    "rate_head",
]


def available():
    """True when PyMC can be imported (the ``bayes`` extra)."""
    from ccp.analytics.fleet import pymc_available

    return pymc_available()


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------


def _case_id(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def members(state):
    """The member list of a case state, with every key present."""
    out = []
    for m in state.get("fleet_members") or []:
        if not isinstance(m, dict):
            continue
        out.append(
            {
                "evaluation": _case_id(m.get("evaluation")),
                "name": str(m.get("name") or "").strip(),
                "site": str(m.get("site") or "").strip(),
                "shop": _case_id(m.get("shop")),
            }
        )
    return out


def members_from_post(data):
    """Members from the editor form (parallel ``member_*`` lists)."""
    columns = {
        key: data.getlist(f"member_{key}")
        for key in ("evaluation", "name", "site", "shop")
    }
    n = max((len(v) for v in columns.values()), default=0)

    def at(key, i):
        values = columns[key]
        return values[i] if i < len(values) else ""

    return members(
        {"fleet_members": [{key: at(key, i) for key in columns} for i in range(n)]}
    )


def unit_names(members_, case_names):
    """Unit name per member: the typed name, else the evaluation case name."""
    names = []
    for m in members_:
        name = m["name"] or case_names.get(m["evaluation"]) or ""
        names.append(name)
    return names


def validate(state, evaluation_cases, shop_cases):
    """Errors before a run.

    Parameters
    ----------
    evaluation_cases : dict
        Case id -> (name, has an evaluation) of the user's evaluation cases.
    shop_cases : dict
        Case id -> (name, has results) of the user's straight-through cases.
    """
    errors = {}
    if not available():
        errors["fleet_members"] = f"The fleet model needs PyMC ({INSTALL_HINT})."
        return errors
    ms = [m for m in members(state) if m["evaluation"] is not None]
    if len(ms) < 2:
        errors["fleet_members"] = "Add at least two units with an evaluation case."
        return errors
    names = unit_names(ms, {k: v[0] for k, v in evaluation_cases.items()})
    if len(set(names)) != len(names):
        errors["fleet_members"] = "Unit names must be distinct."
    for m, name in zip(ms, names):
        info = evaluation_cases.get(m["evaluation"])
        if info is None:
            errors["fleet_members"] = f"Unit {name}: evaluation case not found."
        elif not info[1]:
            errors["fleet_members"] = (
                f"Unit {name}: run the evaluation of case {info[0]!r} first."
            )
        if m["shop"] is not None:
            shop = shop_cases.get(m["shop"])
            if shop is None:
                errors["fleet_members"] = f"Unit {name}: shop test case not found."
            elif not shop[1]:
                errors["fleet_members"] = (
                    f"Unit {name}: calculate the shop test case {shop[0]!r} first."
                )
    for key, low in (("fleet_draws", 10), ("fleet_tune", 10), ("fleet_chains", 1)):
        value = state.get(key)
        if not isinstance(value, (int, float)) or value < low:
            errors[key] = f"At least {low}."
    for key in ("fleet_tau_unit_head", "fleet_tau_unit_eff"):
        value = state.get(key)
        if value is not None and value <= 0:
            errors[key] = "Must be positive (blank for the default)."
    return errors


def priors(state):
    """``FleetPriors`` with the overrides of the case."""
    from ccp.analytics.fleet import FleetPriors

    overrides = {}
    for key in ("head", "eff"):
        value = state.get(f"fleet_tau_unit_{key}")
        if value:
            overrides[f"tau_unit_{key}"] = Q_(value, "percent").to("dimensionless").m
    return FleetPriors(**overrides)


def threshold(state):
    """Efficiency threshold as a fraction (negative: below the vendor curve)."""
    points = state.get("fleet_threshold")
    points = 3.0 if points is None else float(points)
    return -Q_(abs(points), "percent").to("dimensionless").m


def sampler_kwargs(state):
    seed = state.get("fleet_seed")
    return {
        "draws": int(state.get("fleet_draws") or 1000),
        "tune": int(state.get("fleet_tune") or 1000),
        "chains": int(state.get("fleet_chains") or 4),
        "random_seed": None if seed is None else int(seed),
    }


# --------------------------------------------------------------------------
# Observations and fit
# --------------------------------------------------------------------------


def observations(units, load_evaluation, load_shop=None, progress=None):
    """Field and shop observation tables of the members.

    Parameters
    ----------
    units : list of dict
        ``name``, ``site``, ``evaluation`` (case id) and ``shop`` (case id or
        None) per unit.
    load_evaluation : callable(case id) -> ccp.Evaluation
    load_shop : callable(case id) -> list of ccp.Point, optional
        Shop test points at the specified conditions.
    progress : callable(fraction, message), optional

    Returns
    -------
    field : pandas.DataFrame
    shop : pandas.DataFrame or None
    sites : dict
    """
    from ccp.analytics.fleet import (
        MAX_HEAD_SLOPE,
        FleetUnit,
        field_observations,
        unit_shop_observations,
    )

    field_rows, shop_rows, sites = [], [], {}
    for i, unit in enumerate(units):
        name, site = unit["name"], unit["site"] or "site"
        sites[name] = site
        if progress:
            progress(0.02 + 0.25 * i / len(units), f"Loading {name}...")
        evaluation = load_evaluation(unit["evaluation"])
        try:
            obs = field_observations(evaluation)
        except ValueError as exc:
            # evaluations saved before the analytics columns existed
            raise InputError(
                {
                    "fleet_members": (
                        f"Unit {name}: {exc} Use Full rebuild on its evaluation page."
                    )
                }
            ) from exc
        if obs.empty:
            raise InputError(
                {"fleet_members": f"Unit {name}: the evaluation has no valid rows."}
            )
        field_rows.append(obs.assign(unit=name, site=site))
        has_shop = False
        if unit.get("shop") is not None and load_shop is not None:
            points = load_shop(unit["shop"])
            shop = unit_shop_observations(
                FleetUnit(name, evaluation=evaluation, site=site, shop=points)
            )
            if shop is not None and not shop.empty:
                shop_rows.append(shop.assign(unit=name))
                has_shop = True
        usable = int((obs["head_slope"].abs() <= MAX_HEAD_SLOPE).sum())
        if usable == 0 and not has_shop:
            # the model would report this unit from the priors only
            raise InputError(
                {
                    "fleet_members": (
                        f"Unit {name}: all {len(obs)} valid rows are near choke "
                        f"(|head slope| > {MAX_HEAD_SLOPE}), where the fleet "
                        "model does not apply, and it has no shop test."
                    )
                }
            )
    field = pd.concat(field_rows)
    shop = pd.concat(shop_rows, ignore_index=True) if shop_rows else None
    return field, shop, sites


def build(field, shop, sites, state):
    """Unfitted ``Fleet`` from the observation tables."""
    from ccp.analytics.fleet import Fleet

    return Fleet.from_observations(
        field, shop, sites=sites, priors=priors(state), units=list(sites)
    )


def fit(fleet, state):
    return fleet.fit(**sampler_kwargs(state))


def save(fleet):
    with tempfile.TemporaryDirectory(prefix="ccp-fleet-") as tmp:
        path = Path(tmp) / "fleet.zip"
        fleet.save(path)
        return path.read_bytes()


def load(content):
    from ccp.analytics.fleet import Fleet

    with tempfile.TemporaryDirectory(prefix="ccp-fleet-") as tmp:
        path = Path(tmp) / "fleet.zip"
        path.write_bytes(content)
        return Fleet.load(path)


def results(fleet, state):
    """JSON results: ``Fleet.to_dict`` plus figures and run facts."""
    data = fleet.to_dict(prob=PROB, threshold=threshold(state))
    data["figures"] = {
        "units": fig_json(_forest(fleet.plot_units(prob=PROB))),
        "health_eff": fig_json(fleet.plot_health("eff", prob=PROB)),
        "health_head": fig_json(fleet.plot_health("head", prob=PROB)),
    }
    data["threshold_points"] = -threshold(state) * 100
    data["sampler"] = sampler_kwargs(state)
    data["n_rows"] = int(len(fleet.field))
    data["n_shop"] = 0 if fleet.shop is None else int(len(fleet.shop))
    data["has_power"] = bool(fleet.has_power)
    data["units_without_field"] = without_field(data)
    return data


def without_field(data):
    """Units whose field rows were all left out (near choke)."""
    summary = frame(data.get("summary"))
    if "field_rows" not in summary.columns:
        return []
    return [str(u) for u, n in summary["field_rows"].items() if _num(n) == 0]


def _forest(fig):
    """The forest plot as drawn by the library (kept as a hook for styling)."""
    return fig


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------


def frame(split):
    """DataFrame from a ``to_json(orient="split")`` dict."""
    if not split:
        return pd.DataFrame()
    return pd.DataFrame(split["data"], index=split["index"], columns=split["columns"])


def _num(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value else None


def _interval(row, name):
    m, lo, hi = (_num(row.get(k)) for k in (name, f"{name}_low", f"{name}_high"))
    if m is None:
        return None
    return {
        "mean": m,
        "low": lo,
        "high": hi,
        "text": f"{m:+.2f}",
        "range": f"{lo:+.2f} … {hi:+.2f}" if lo is not None and hi is not None else "",
        # the interval excludes zero
        "sign": ("neg" if hi is not None and hi < 0 else "")
        or ("pos" if lo is not None and lo > 0 else ""),
    }


def _hours_text(hours):
    # to_json writes inf (threshold never reached) as null
    if hours is None or hours == float("inf"):
        return "∞"
    return f"{Q_(hours, 'h').to('day').m:,.0f} d"


def unit_rows(data):
    """Rows of the unit table."""
    summary = frame(data.get("summary"))
    ttt = frame(data.get("time_to_threshold"))
    rows = []
    for unit, row in summary.iterrows():
        row = row.to_dict()
        t = ttt.loc[unit].to_dict() if unit in ttt.index else {}
        no_field = _num(row.get("field_rows")) == 0
        rows.append(
            {
                "unit": unit,
                "site": row.get("site"),
                "no_field": no_field,
                "current_eff": _interval(row, "current_eff"),
                "current_head": _interval(row, "current_head"),
                "asbuilt_eff": _interval(row, "asbuilt_eff"),
                "asbuilt_head": _interval(row, "asbuilt_head"),
                "asbuilt_flow": _interval(row, "asbuilt_flow"),
                "rate_eff": _interval(row, "rate_eff"),
                "rate_head": _interval(row, "rate_head"),
                "p_worst": _num(row.get("p_worst_eff")),
                "p_below": _num(row.get("p_below_threshold")),
                "p_degrading": _num(row.get("p_degrading_eff")),
                "bias_T": _num(row.get("bias_T")),
                "bias_flow": _num(row.get("bias_flow")),
                "bias_driver": _num(row.get("bias_driver")),
                "time_to": (
                    _hours_text(_num(t.get("median_h"))) if t and not no_field else "—"
                ),
                "time_to_range": (
                    f"{_hours_text(_num(t.get('q05_h')))}–"
                    f"{_hours_text(_num(t.get('q95_h')))}"
                    if t and not no_field
                    else ""
                ),
                "p_within_year": _num(t.get("p_within_horizon")),
            }
        )
        rows[-1]["intervals"] = [rows[-1][k] for k in INTERVAL_COLUMNS]
    return rows


def scatter_rows(data):
    scatter = frame(data.get("scatter"))
    rows = []
    for name, row in scatter.iterrows():
        label, unit = SCATTER_LABELS.get(name, (name, ""))
        rows.append(
            {
                "name": name,
                "label": label,
                "unit": unit,
                "mean": _num(row.get("mean")),
                "low": _num(row.get("low")),
                "high": _num(row.get("high")),
            }
        )
    return rows


def event_rows(data):
    events = frame(data.get("events"))
    rows = []
    for _, row in events.iterrows():
        step = _num(row.get("step"))
        rows.append(
            {
                "unit": row.get("unit"),
                "field": "efficiency" if row.get("field") == "eff" else "head",
                "time": str(row.get("time") or "")[:10],
                "step": step,
                "kind": "recovery" if step is not None and step > 0 else "drop",
                "probability": _num(row.get("probability")),
            }
        )
    return rows


def ranking_rows(data):
    ranking = frame(data.get("ranking"))
    return {
        "columns": [c.replace("rank_", "") for c in ranking.columns],
        "rows": [(unit, [_num(v) for v in row]) for unit, row in ranking.iterrows()],
    }


def diagnostics(data):
    """Diagnostics with a status: ``ok`` or ``warn`` and the reasons."""
    diag = dict(data.get("diagnostics") or {})
    reasons = []
    rhat = _num(diag.get("max_rhat"))
    if rhat is not None and rhat > MAX_RHAT:
        reasons.append(f"R-hat {rhat:.3f} > {MAX_RHAT}: chains have not converged")
    divergences = diag.get("divergences") or 0
    if divergences:
        reasons.append(f"{divergences} divergent transitions")
    diag["status"] = "warn" if reasons else "ok"
    diag["reasons"] = reasons
    return diag


def dumps(data):
    return json.dumps(data)
