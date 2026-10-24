"""Agent adapter of the curves digitizer page.

See ``ccp_web.agent.adapters`` for the interface. ``start`` is the page's
Digitize button (``views.start_digitize``): it runs on the uploaded curve PDF
(case file ``curve_pdf``) with the page range of the ``digitize_pages`` state
key, so it takes no params. Results and figures read the stored digitized
document (artifact ``digitized``, the user's edits included), the same data
the review table and the point editor show.

Units are always explicit: flows are in each plot's ``flow_units``, curve
values in its ``units`` and speeds in rpm, as printed on the vendor sheet.
"""

from ccp_web.agent.adapters import json_safe
from ccp_web.core.models import Job
from ccp_web.services import digitizer

from .views import load_data, start_digitize

PARAMS = {}
SPEED_UNITS = "rpm"
CALIBRATION = (
    "page pixel = offset + slope * value, at the plot's dpi (x: flow, y: value)"
)


def start(case, params):
    """Start the digitize job; the pages come from ``digitize_pages``."""
    unknown = sorted(set(params or {}) - set(PARAMS))
    if unknown:
        raise ValueError(
            f"unknown params {unknown}; the digitizer takes none (set the "
            "'digitize_pages' state key to choose the pages)"
        )
    return start_digitize(case)


def has_results(case):
    return case.artifact("digitized") is not None


def _last_job(case):
    return (
        Job.objects.filter(case=case, kind="digitize_pdf").order_by("-created").first()
    )


def _range(values, units):
    if not values:
        return None
    return {"min": min(values), "max": max(values), "units": units}


def _quantity(value):
    """``[value, units]`` of the sheet's conditions -> ``{value, units}``."""
    if (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and isinstance(value[1], (str, type(None)))
        and not isinstance(value[0], str)
    ):
        return {"value": value[0], "units": value[1]}
    return value


def _speed_name(curve):
    speed = curve.get("speed")
    name = "no speed" if speed is None else f"{speed:g} {SPEED_UNITS}"
    return f"{curve['label']} {name}" if curve.get("label") else name


def _axis(plot, axis):
    cal = plot.get(f"{axis}_axis")
    if not cal:
        return None
    return {
        "offset": cal.get("offset"),
        "slope": cal.get("slope"),
        "residual_px": plot.get(f"{axis}_residual"),
        # tick values read on the sheet that the calibration was fitted on
        "ticks": [t[0] for t in plot.get(f"{axis}_ticks") or []],
        "title": plot.get(f"{axis}_title") or "",
    }


def _plot_summary(plot, case_names):
    flow_units = plot.get("flow_units") or None
    value_units = plot.get("units") or None
    curves = []
    all_flow, all_value = [], []
    for c in plot.get("curves", []):
        all_flow += c["flow"]
        all_value += c["value"]
        curves.append(
            {
                "name": _speed_name(c),
                "speed": c.get("speed"),
                "speed_units": SPEED_UNITS,
                "n_points": len(c["flow"]),
                "flow_range": _range(c["flow"], flow_units),
                "value_range": _range(c["value"], value_units),
            }
        )
    reference = plot.get("reference")
    return {
        "id": plot["id"],
        "page": plot["page"],
        "param": plot.get("param"),
        "label": digitizer.plot_label(plot),
        "units": value_units,
        "flow_units": flow_units,
        "cases": case_names,
        "edited": bool(plot.get("edited", False)),
        "source": plot.get("source"),
        "legend_speeds": plot.get("speeds") or [],
        "speed_units": SPEED_UNITS,
        "n_curves": len(curves),
        "n_points": sum(c["n_points"] for c in curves),
        "flow_range": _range(all_flow, flow_units),
        "value_range": _range(all_value, value_units),
        "curves": curves,
        "n_envelopes": len(plot.get("envelopes") or []),
        "reference_point": (
            {"flow": reference[0], "value": reference[1]} if reference else None
        ),
        "calibration": {
            "dpi": plot.get("dpi"),
            "convention": CALIBRATION,
            "x": _axis(plot, "x"),
            "y": _axis(plot, "y"),
        },
        "warnings": plot.get("warnings") or [],
        "notes": plot.get("notes") or [],
    }


def _case_names(data):
    names = {}
    for c in data.get("cases", []):
        for plot_id in c.get("plots", {}).values():
            names.setdefault(plot_id, []).append(c["name"])
    return names


def results(case):
    """Digitized cases and, per plot, its curves, ranges and calibration.

    Each curve gives its speed, point count and flow/value ranges; the full
    points are the plot's figure (``figures/<plot id>``). ``edited`` tells
    the plots whose points the user changed in the editor.
    """
    data = load_data(case)
    job = _last_job(case)
    if data is None:
        if case.file("curve_pdf") is None:
            reason = "no curve PDF uploaded yet: the user uploads it on the page"
        else:
            reason = "not digitized yet: POST calculate"
        out = {"available": False, "reason": reason}
        if job is not None and job.status == Job.FAILED:
            out["reason"] = f"the last digitization failed: {job.error}"
            out["errors"] = (job.result or {}).get("errors") or {}
        return out
    rows, unassigned = digitizer.cases_overview(data)
    names = _case_names(data)
    plots = [_plot_summary(p, names.get(p["id"], [])) for p in data.get("plots", [])]
    pdf = case.file("curve_pdf")
    original = case.artifact("digitized_original")
    edited = case.artifact("digitized")
    out = {
        "available": True,
        "app_type": case.app_type,
        "pdf": pdf.name if pdf else None,
        "pages": case.state.get("digitize_pages") or "all",
        "n_pages": data.get("n_pages"),
        "units": {
            "speed": SPEED_UNITS,
            "flow": "per plot: flow_units",
            "value": "per plot: units",
        },
        "n_plots": len(plots),
        "n_edited": sum(1 for p in plots if p["edited"]),
        "cases": [
            {
                "name": r["name"],
                "slug": r["slug"],
                "pages": r["pages"],
                "conditions": {k: _quantity(v) for k, v in r["conditions"].items()},
                "speeds": r["speeds"],
                "speed_units": SPEED_UNITS,
                # the two plots that define the map in a curves conversion
                "pair": list(r["pair"]) if r["pair"] else None,
                "plots": {p["param"]: p["id"] for p in r["plots"]},
                "warnings": r["warnings"],
                "n_warnings": r["n_warnings"],
            }
            for r in rows
        ],
        "plots": plots,
        "unassigned": {
            "plots": [p["id"] for p in unassigned["plots"]],
            "pages": unassigned["pages"],
        },
        "digitized": original.created if original else None,
        "saved": edited.created if edited else None,
    }
    if job is not None:
        out["job"] = {
            "id": job.pk,
            "status": job.status,
            "warnings": list(job.warnings or []),
            "result": job.result,
        }
    return json_safe(out)


def _plots(case):
    data = load_data(case)
    return [] if data is None else data.get("plots", [])


def figures(case):
    """One figure per plot with digitized curves; the id is the plot id."""
    data = load_data(case)
    if data is None:
        return []
    names = _case_names(data)
    return [
        {
            "id": p["id"],
            "title": f"{digitizer.plot_label(p)} (page {p['page']})",
            "section": ", ".join(names.get(p["id"], [])) or "unassigned",
        }
        for p in data.get("plots", [])
        if p.get("curves")
    ]


def _title(name, units):
    return f"{name} ({units})" if units else name


def figure(case, figure_id):
    """The digitized curves of one plot, in the sheet's units."""
    import plotly.graph_objects as go

    plot = next(
        (p for p in _plots(case) if p["id"] == figure_id and p.get("curves")), None
    )
    if plot is None:
        raise KeyError(figure_id)
    fig = go.Figure()
    for c in plot["curves"]:
        fig.add_trace(
            go.Scatter(
                x=c["flow"], y=c["value"], mode="lines+markers", name=_speed_name(c)
            )
        )
    for i, env in enumerate(plot.get("envelopes") or [], start=1):
        fig.add_trace(
            go.Scatter(
                x=env["flow"], y=env["value"], mode="lines", name=f"envelope {i}"
            )
        )
    if plot.get("reference"):
        flow, value = plot["reference"]
        fig.add_trace(
            go.Scatter(x=[flow], y=[value], mode="markers", name="reference point")
        )
    label = digitizer.plot_label(plot)
    fig.update_layout(
        title=f"{label} (page {plot['page']})"
        + (" (edited)" if plot.get("edited") else ""),
        xaxis_title=_title("Flow", plot.get("flow_units")),
        yaxis_title=_title(label, plot.get("units")),
    )
    return fig
