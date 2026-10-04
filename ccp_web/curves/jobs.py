from ccp_web.core.jobs import register
from ccp_web.services import curves, schemas, units


def design_csv_files(case, letter):
    files = []
    for n in (1, 2):
        f = case.file(f"curves_file_{n}_case_{letter}")
        if f is not None:
            files.append((f.name, f.read()))
    return files


def loaded_impellers(case):
    """``{letter: Impeller}`` of the design cases with stored curves."""
    result = {}
    for letter in schemas.CASES:
        artifact = case.artifact(f"impeller_case_{letter}")
        if artifact is not None:
            result[letter] = curves.load_impeller(artifact.read_text())
    return result


@register("load_curves")
def load_curves(ctx):
    letter = ctx.params["case"]
    state = ctx.case.state
    ctx.progress(0.05, f"Loading curves for case {letter}...")
    with units.state_context(state):
        impeller, curve_name = curves.load_design_case(
            state, letter, design_csv_files(ctx.case, letter)
        )
        text = curves.dump_impeller(impeller)
    ctx.save_artifact(f"impeller_case_{letter}", f"impeller_case_{letter}.toml", text)
    ctx.update_state(**{f"curve_name_case_{letter}": curve_name})
    ctx.job.message = (
        f"Case {letter} curves loaded: {len(impeller.points)} points, "
        f"{len(impeller.curves)} curves"
    )


@register("convert_curves")
def convert_curves(ctx):
    state = ctx.case.state
    ctx.progress(0.05, "Reading design cases...")
    with units.state_context(state):
        impellers = loaded_impellers(ctx.case)
        ctx.progress(0.2, "Converting curves...")
        converted, note = curves.convert(state, impellers)
        text = curves.dump_impeller(converted)
    ctx.save_artifact("converted_impeller", "converted_impeller.toml", text)
    # A new conversion resets the operating point of the converted plots.
    ctx.update_state(converted_flow_input=None, converted_speed_input=None)
    ctx.job.message = note
