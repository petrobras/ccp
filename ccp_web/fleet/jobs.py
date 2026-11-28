from ccp_web.core.jobs import register
from ccp_web.core.models import Case
from ccp_web.services import evaluation as ev
from ccp_web.services import fleet as fl
from ccp_web.services import performance_test as pt
from ccp_web.services import units
from ccp_web.services.units import InputError

FLEET_KEY = "fleet"
RESULTS_KEY = "fleet_results"


def _member_case(owner, pk, app_type, artifact_key):
    case = Case.objects.filter(owner=owner, pk=pk, app_type=app_type).first()
    artifact = case.artifact(artifact_key) if case is not None else None
    if artifact is None:
        raise InputError(
            {"fleet_members": f"Case {pk} has no {artifact_key.replace('_', ' ')}."}
        )
    return case, artifact


def loaders(owner):
    """``load_evaluation`` and ``load_shop`` for the owner's cases."""

    def load_evaluation(pk):
        case, artifact = _member_case(
            owner, pk, Case.PERFORMANCE_EVALUATION, "evaluation"
        )
        with units.state_context(case.state):
            return ev.load(artifact.read(), case.state)

    def load_shop(pk):
        case, artifact = _member_case(
            owner, pk, Case.STRAIGHT_THROUGH, Case.STRAIGHT_THROUGH
        )
        with units.state_context(case.state):
            compressor = pt.load_compressor(case.app_type, artifact.read_text())
            return list(compressor.points_flange_sp)

    return load_evaluation, load_shop


def unit_specs(case):
    """Name, site and case ids of each member with an evaluation."""
    members = [m for m in fl.members(case.state) if m["evaluation"] is not None]
    names = dict(
        Case.objects.filter(
            owner=case.owner, pk__in=[m["evaluation"] for m in members]
        ).values_list("pk", "name")
    )
    return [
        {**m, "name": name} for m, name in zip(members, fl.unit_names(members, names))
    ]


@register("fleet")
def run_fleet(ctx):
    state = ctx.state
    if not fl.available():
        raise InputError({"fleet_members": f"Install PyMC: {fl.INSTALL_HINT}"})
    specs = unit_specs(ctx.case)
    load_evaluation, load_shop = loaders(ctx.case.owner)
    # the shop tests convert the design curves: default ambient and method
    with units.state_context(state):
        field, shop, sites = fl.observations(
            specs, load_evaluation, load_shop, progress=ctx.progress
        )
    ctx.progress(0.3, "Building the fleet model...")
    try:
        fleet = fl.build(field, shop, sites, state)
    except ValueError as exc:
        raise InputError({"fleet_members": str(exc)}) from exc
    kw = fl.sampler_kwargs(state)
    ctx.progress(
        0.35,
        f"Sampling {kw['chains']} chain(s) × {kw['draws']} draws "
        f"({len(fleet.field)} rows, {fleet.n_bins} periods of {fleet.freq})...",
    )
    fl.fit(fleet, state)
    ctx.progress(0.9, "Summarising the posterior...")
    data = fl.results(fleet, state)
    ctx.save_artifact(FLEET_KEY, "fleet.zip", fl.save(fleet))
    ctx.save_artifact(RESULTS_KEY, "fleet_results.json", fl.dumps(data))
    diag = fl.diagnostics(data)
    for reason in diag["reasons"]:
        ctx.warn(f"{reason}; increase tune and draws.")
    for unit in data["units_without_field"]:
        ctx.warn(
            f"Unit {unit}: no field rows away from choke; only its as-built "
            "deviations (from the shop test) are estimated."
        )
    ctx.set_result(
        units=len(data["units"]),
        max_rhat=diag.get("max_rhat"),
        divergences=diag.get("divergences"),
    )
    ctx.job.message = (
        f"{len(data['units'])} units · max R-hat {diag['max_rhat']:.3f} · "
        f"{diag['divergences']} divergences"
    )
