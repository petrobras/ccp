from ccp_web.core.jobs import register
from ccp_web.services import performance_test as pt
from ccp_web.services import units


@register("calculate")
def calculate(ctx):
    """Build the StraightThrough/BackToBack object and store its TOML."""
    app_type = ctx.case.app_type
    state = ctx.case.state
    with units.state_context(state):
        compressor, warnings = pt.calculate(
            app_type,
            state,
            calculate_speed=bool(ctx.params.get("calculate_speed")),
            progress=ctx.progress,
            cancelled=ctx.cancelled,
        )
        text = pt.dump_compressor(compressor)
        speed = compressor.speed_operational.to("rpm").m
    for w in warnings:
        ctx.warn(w)
    ctx.save_artifact(app_type, f"{app_type}.toml", text)
    ctx.job.message = f"Operational speed {speed:.2f} RPM"
    ctx.set_result(speed_operational_rpm=speed)
