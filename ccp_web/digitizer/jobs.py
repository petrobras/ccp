from ccp_web.core.jobs import register
from ccp_web.services import digitizer
from ccp_web.services.units import InputError


@register("digitize_pdf")
def digitize_pdf(ctx):
    pdf = ctx.case.file("curve_pdf")
    if pdf is None:
        raise InputError({"curve_pdf": "Upload a curve PDF first."})
    pages = digitizer.parse_pages(ctx.state.get("digitize_pages"))
    ctx.progress(0.02, "Reading the PDF...")

    def progress(done, total):
        ctx.progress(0.03 + 0.92 * done / total, f"Digitized page {done} of {total}")

    data = digitizer.digitize(pdf.read(), pages=pages, progress=progress)
    ctx.progress(0.97, "Saving...")
    text = digitizer.dumps(data)
    # the original is kept so edited plots can be reset
    ctx.save_artifact("digitized_original", "digitized_original.json", text)
    ctx.save_artifact("digitized", "digitized.json", text)
    rows, unassigned = digitizer.cases_overview(data)
    n_plots = len(data.get("plots", []))
    n_warn = sum(r["n_warnings"] for r in rows)
    ctx.set_result(cases=len(rows), plots=n_plots, warnings=n_warn)
    ctx.job.message = f"{len(rows)} cases, {n_plots} plots" + (
        f", {n_warn} warnings to review" if n_warn else ""
    )
