"""Constraint-propagation solver for :class:`ccp.point.Point`.

Historically, ``Point`` decided how to compute itself by joining its provided
keyword names into a string and dispatching to a matching ``_calc_from_<args>``
method.  That produced ~46 nearly-identical methods, because the real degrees of
freedom are small and combine as a cartesian product:

* how the discharge state is pinned down (``disch`` directly, ``head+eff``,
  ``disch_p+eff``, ``disch_T+head``, ``disch_T+pressure_ratio``,
  ``eff+volume_ratio``, ``flow+head+power``, ``flow+head+power_shaft`` ...);
* whether the flow is given as ``flow_v`` or ``flow_m``;
* which variable closes the mechanical-loss loop (nothing -> ``power_losses=0``,
  ``torque`` or ``power_losses``).

The relationships are non-linear (head/eff come from the equation of state via
Newton iterations), so a literal matrix solve does not apply.  Instead this
module models the problem as a set of small *relations*, each of which can
produce one or more unknowns once its inputs are known, and a fixpoint engine
that keeps firing applicable relations until the point is fully defined.  This
means the user gets a valid ``Point`` whenever they provide *any* sufficient set
of arguments -- including combinations that were never enumerated as a method.
"""

from scipy.optimize import newton

from ccp.config.units import Q_
from ccp.state import State

# Variables tracked by the solver.
VAR_NAMES = [
    "suc",
    "disch",
    "disch_p",
    "flow_v",
    "flow_m",
    "speed",
    "head",
    "eff",
    "power",
    "power_shaft",
    "power_losses",
    "torque",
    "phi",
    "psi",
    "volume_ratio",
    "pressure_ratio",
    "disch_T",
]

# Variables that must be known for a point to be considered fully defined.
REQUIRED = [
    "disch",
    "head",
    "eff",
    "volume_ratio",
    "flow_v",
    "flow_m",
    "speed",
    "phi",
    "psi",
    "power",
    "power_shaft",
    "power_losses",
    "torque",
]


class _Context:
    """Read-only bundle of everything the relations need from the point.

    Helper functions are imported lazily from :mod:`ccp.point` to avoid a
    circular import at module load time.
    """

    def __init__(self, point):
        import ccp.point as point_module

        self.m = point_module
        self.suc = point.suc
        self.D = point.D
        self.b = point.b
        self.head_calc_func = point.head_calc_func
        self.eff_calc_func = point.eff_calc_func
        self._dummy_state = point._dummy_state
        self.polytropic_method = point.polytropic_method
        # casing heat-loss parameters
        self.casing_temperature = point.casing_temperature
        self.ambient_temperature = point.ambient_temperature
        self.casing_area = point.casing_area
        self.convection_constant = point.convection_constant


# ---------------------------------------------------------------------------
# Relations
# ---------------------------------------------------------------------------
#
# Each relation is a function ``rule(v, ctx) -> dict | None`` where ``v`` is the
# dict of currently-known variables.  A relation returns a dict of newly
# computed variables when its inputs are available and at least one of its
# outputs is still missing, otherwise ``None``.  The engine only commits values
# for keys that are still unknown, so a relation never overwrites a value that
# was provided or already derived.


def _has(v, *keys):
    return all(k in v for k in keys)


def _missing(v, *keys):
    return any(k not in v for k in keys)


# --- discharge-state closures (produce ``disch``) --------------------------


def _disch_p_from_pressure_ratio(v, ctx):
    if _has(v, "pressure_ratio") and _missing(v, "disch_p"):
        return {"disch_p": ctx.suc.p() * v["pressure_ratio"]}


def _disch_from_head_eff(v, ctx):
    if _has(v, "head", "eff") and _missing(v, "disch"):
        disch = ctx.m.disch_from_suc_head_eff(
            ctx.suc, v["head"], v["eff"], polytropic_method=ctx.polytropic_method
        )
        return {"disch": disch}


def _disch_from_disch_p_eff(v, ctx):
    if _has(v, "disch_p", "eff") and _missing(v, "disch"):
        disch = ctx.m.disch_from_suc_disch_p_eff(
            ctx.suc, v["disch_p"], v["eff"], polytropic_method=ctx.polytropic_method
        )
        return {"disch": disch}


def _disch_from_disch_T_head(v, ctx):
    if _has(v, "disch_T", "head") and _missing(v, "disch"):
        disch = ctx.m.disch_from_suc_disch_T_head(
            ctx.suc, v["disch_T"], v["head"], polytropic_method=ctx.polytropic_method
        )
        return {"disch": disch}


def _disch_from_disch_T_disch_p(v, ctx):
    # covers the disch_T + pressure_ratio path (disch_p derived above)
    if _has(v, "disch_T", "disch_p") and _missing(v, "disch"):
        disch = State(p=v["disch_p"], T=v["disch_T"], fluid=ctx.suc.fluid)
        return {"disch": disch}


def _disch_from_eff_volume_ratio(v, ctx):
    if _missing(v, "disch") and _has(v, "eff", "volume_ratio"):
        suc = ctx.suc
        eff = v["eff"]
        disch_v = suc.v() / v["volume_ratio"]
        disch_rho = 1 / disch_v

        # consider first an isentropic compression
        disch = State(rho=disch_rho, s=suc.s(), fluid=suc.fluid)

        def update_state(x, update_type):
            if update_type == "pressure":
                disch.update(rho=disch_rho, p=x)
            elif update_type == "temperature":
                disch.update(rho=disch_rho, T=x)
            new_eff = ctx.eff_calc_func(suc, disch)
            if not 0.0 < new_eff < 1.5:
                raise ValueError("Efficiency did not converge")
            return (new_eff - eff).magnitude

        try:
            newton(update_state, disch.T().magnitude, args=("temperature",), tol=1e-1)
        except ValueError:
            # re-instantiate disch, since update with temperature not converging
            # might break the state
            disch = State(rho=disch_rho, s=suc.s(), fluid=suc.fluid)
            newton(update_state, disch.p().magnitude, args=("pressure",), tol=1e-1)

        return {"disch": disch}


# --- quantities derived from a known ``disch`` -----------------------------


def _head_from_states(v, ctx):
    if _has(v, "disch") and _missing(v, "head"):
        return {"head": ctx.head_calc_func(ctx.suc, v["disch"], ctx._dummy_state)}


def _eff_from_states(v, ctx):
    # Efficiency computed from a measured discharge state.  When casing data is
    # supplied, the efficiency is corrected for the casing heat loss, which
    # requires the mass flow -- so we wait for ``flow_m`` in that case.
    if _missing(v, "disch") or not _missing(v, "eff"):
        return None
    if ctx.casing_temperature is not None and _missing(v, "flow_m"):
        return None
    eff = ctx.eff_calc_func(ctx.suc, v["disch"], ctx._dummy_state)
    out = {"eff": eff}
    if ctx.casing_temperature is not None:
        casing_heat_loss = (
            ctx.convection_constant
            * ctx.casing_area
            * (ctx.casing_temperature - ctx.ambient_temperature)
        )
        out["eff"] = eff / (
            1 + (casing_heat_loss / ((v["disch"].h() - ctx.suc.h()) * v["flow_m"]))
        )
        out["casing_heat_loss"] = casing_heat_loss
    return out


def _volume_ratio_from_states(v, ctx):
    if _has(v, "disch") and _missing(v, "volume_ratio"):
        return {"volume_ratio": ctx.suc.v() / v["disch"].v()}


# --- flow / speed / coefficient algebra ------------------------------------


def _flow_m_from_flow_v(v, ctx):
    if _has(v, "flow_v") and _missing(v, "flow_m"):
        return {"flow_m": v["flow_v"] * ctx.suc.rho()}


def _flow_v_from_flow_m(v, ctx):
    if _has(v, "flow_m") and _missing(v, "flow_v"):
        return {"flow_v": v["flow_m"] / ctx.suc.rho()}


def _flow_v_from_phi(v, ctx):
    if _has(v, "phi", "speed") and _missing(v, "flow_v"):
        return {"flow_v": ctx.m.flow_from_phi(ctx.D, v["phi"], v["speed"])}


def _phi_from_flow(v, ctx):
    if _has(v, "flow_v", "speed") and _missing(v, "phi"):
        return {"phi": ctx.m.phi(v["flow_v"], v["speed"], ctx.D)}


def _speed_from_psi(v, ctx):
    if _has(v, "psi", "head") and _missing(v, "speed"):
        return {"speed": ctx.m.speed_from_psi(ctx.D, v["head"], v["psi"])}


def _head_from_psi(v, ctx):
    if _has(v, "psi", "speed") and _missing(v, "head"):
        return {"head": ctx.m.head_from_psi(ctx.D, v["psi"], v["speed"])}


def _psi_from_head(v, ctx):
    if _has(v, "head", "speed") and _missing(v, "psi"):
        return {"psi": ctx.m.psi(v["head"], v["speed"], ctx.D)}


# --- power / loss algebra --------------------------------------------------


def _power_from_flow_head_eff(v, ctx):
    if _has(v, "flow_m", "head", "eff") and _missing(v, "power"):
        return {"power": ctx.m.power_calc(v["flow_m"], v["head"], v["eff"])}


def _eff_from_flow_head_power(v, ctx):
    if _has(v, "flow_m", "head", "power") and _missing(v, "eff"):
        return {"eff": (v["flow_m"] * v["head"] / v["power"]).to("dimensionless")}


def _power_from_shaft_losses(v, ctx):
    if _has(v, "power_shaft", "power_losses") and _missing(v, "power"):
        return {"power": v["power_shaft"] - v["power_losses"]}


def _shaft_from_torque(v, ctx):
    if _has(v, "torque", "speed") and _missing(v, "power_shaft"):
        return {"power_shaft": v["torque"] * v["speed"]}


def _losses_from_shaft_power(v, ctx):
    if _has(v, "power_shaft", "power") and _missing(v, "power_losses"):
        return {"power_losses": v["power_shaft"] - v["power"]}


def _shaft_from_power_losses(v, ctx):
    if _has(v, "power", "power_losses") and _missing(v, "power_shaft"):
        return {"power_shaft": v["power"] + v["power_losses"]}


def _torque_from_shaft(v, ctx):
    if _has(v, "power_shaft", "speed") and _missing(v, "torque"):
        return {"torque": v["power_shaft"] / v["speed"]}


RELATIONS = [
    # discharge-state closures
    _disch_p_from_pressure_ratio,
    _disch_from_disch_T_disch_p,
    _disch_from_head_eff,
    _disch_from_disch_p_eff,
    _disch_from_disch_T_head,
    _disch_from_eff_volume_ratio,
    # derived from states
    _head_from_states,
    _eff_from_states,
    _volume_ratio_from_states,
    # flow / speed / coefficients
    _flow_m_from_flow_v,
    _flow_v_from_flow_m,
    _flow_v_from_phi,
    _phi_from_flow,
    _speed_from_psi,
    _head_from_psi,
    _psi_from_head,
    # power / loss
    _power_from_flow_head_eff,
    _eff_from_flow_head_power,
    _power_from_shaft_losses,
    _shaft_from_torque,
    _losses_from_shaft_power,
    _shaft_from_power_losses,
    _torque_from_shaft,
]


def _is_complete(v):
    return all(k in v for k in REQUIRED)


def solve(point):
    """Fill in a :class:`Point`'s attributes from its provided inputs.

    Runs a fixpoint over :data:`RELATIONS`.  When no relation can make further
    progress and the mechanical-loss loop is still open (neither ``torque`` nor
    ``power_losses`` was provided), ``power_losses`` defaults to zero, matching
    the historical behaviour, and propagation resumes.

    Returns
    -------
    list of str
        The required variables that could *not* be determined.  An empty list
        means the point was fully resolved; a non-empty list means the provided
        inputs were insufficient and the caller decides how to report it.
    """
    ctx = _Context(point)
    provided = {k for k in VAR_NAMES if getattr(point, k, None) is not None}
    v = {k: getattr(point, k) for k in provided}

    extra = {}  # non-variable outputs such as casing_heat_loss

    progressed = True
    while not _is_complete(v) and progressed:
        progressed = False
        for rule in RELATIONS:
            out = rule(v, ctx)
            if not out:
                continue
            for key, val in out.items():
                if key in VAR_NAMES:
                    if key not in v:
                        v[key] = val
                        progressed = True
                else:
                    extra[key] = val

        if not progressed and not _is_complete(v):
            # default the loss loop only when the user pinned neither end of it
            if (
                "power_losses" not in v
                and "torque" not in provided
                and "power_losses" not in provided
            ):
                v["power_losses"] = Q_(0, "watt")
                progressed = True

    # commit whatever was resolved, even on a partial solve, so the caller can
    # inspect the point if it wishes
    for key, val in v.items():
        setattr(point, key, val)
    for key, val in extra.items():
        setattr(point, key, val)

    return [k for k in REQUIRED if k not in v]
