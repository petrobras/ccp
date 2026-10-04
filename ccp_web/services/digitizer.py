"""Curves digitizer: vendor curve PDF -> editable, loadable curves.

Pure Python (no Django). The digitized document is kept as the JSON dict of
``ccp.digitize.DigitizedDocument.to_dict``; the editor changes the curves of
one plot at a time, in data coordinates (flow, value), and the page maps them
to the plot image through the stored axis calibration.
"""

import io
import json
import math
import os
import re
import tempfile
import zipfile
from pathlib import Path

from .units import InputError

PARAM_LABELS = {
    "head": "Polytropic head",
    "eff": "Polytropic efficiency",
    "pressure_ratio": "Pressure ratio",
    "disch_p": "Discharge pressure",
    "disch_T": "Discharge temperature",
    "power_shaft": "Shaft power",
    "power": "Gas power",
}

PARAM_SHORT = {
    "head": "Head",
    "eff": "Eff.",
    "pressure_ratio": "PR",
    "disch_p": "p disch.",
    "disch_T": "T disch.",
    "power_shaft": "Power",
    "power": "Power",
}

# image crop around a plot frame, in pixels at 300 dpi: room for the tick
# labels (left, bottom) so the calibration can be checked by eye
CROP_MARGIN = {"left": 150, "top": 24, "right": 24, "bottom": 70}
IMAGE_DPI = 150
# points traced per speed line (uniform in arc length), then thinned to about
# one point per THIN_SPACING page pixels (at 300 dpi) so short lines are not
# a solid chain of handles in the editor
POINTS_PER_LINE = 24
THIN_SPACING = 25
MIN_POINTS = 6


def available():
    """Whether the digitize extra and the Tesseract binary are installed."""
    try:
        import pypdfium2  # noqa: F401
        import skimage  # noqa: F401

        from ccp.digitize._ocr import ocr_available
    except ImportError:
        return False
    return ocr_available()


def parse_pages(text):
    """``"3-14, 20"`` -> ``[3, ..., 14, 20]``; blank -> ``None`` (all pages)."""
    text = (text or "").strip()
    if not text:
        return None
    pages = []
    for part in re.split(r"[,;\s]+", text):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise InputError({"digitize_pages": f"Invalid page range: {part!r}"})
        a = int(m.group(1))
        b = int(m.group(2) or a)
        if a < 1 or b < a:
            raise InputError({"digitize_pages": f"Invalid page range: {part!r}"})
        pages.extend(range(a, b + 1))
    return sorted(set(pages))


def default_workers():
    """Parallel pages: ``CCP_DIGITIZE_WORKERS`` or up to 4 (1 = serial)."""
    env = os.environ.get("CCP_DIGITIZE_WORKERS")
    if env:
        return max(1, int(env))
    return max(1, min(4, (os.cpu_count() or 2) - 1))


def digitize(pdf_bytes, pages=None, progress=None, workers=None):
    """Run ``ccp.digitize.digitize_pdf`` on PDF bytes; returns the result dict."""
    from ccp.digitize import digitize_pdf

    with tempfile.TemporaryDirectory(prefix="ccp-digitize-") as tmp:
        path = Path(tmp) / "curves.pdf"
        path.write_bytes(pdf_bytes)
        doc = digitize_pdf(
            path,
            pages=pages,
            progress=progress,
            workers=default_workers() if workers is None else workers,
            n_points=POINTS_PER_LINE,
        )
    data = doc.to_dict()
    data["path"] = ""
    for plot in data["plots"]:
        thin_plot(plot)
    return data


def thin_plot(plot, spacing=THIN_SPACING, min_points=MIN_POINTS):
    """Keep a subset of each line's points about ``spacing`` px apart.

    The kept points are original traced points (no interpolation), chosen
    nearest to uniform arc-length targets in page pixels; both ends stay.
    """
    if not plot.get("x_axis") or not plot.get("y_axis"):
        return
    ax, ay = plot["x_axis"], plot["y_axis"]
    step = spacing * plot["dpi"] / 300
    for c in plot.get("curves", []):
        f, v = c["flow"], c["value"]
        if len(f) <= min_points:
            continue
        xs = [ax["offset"] + ax["slope"] * x for x in f]
        ys = [ay["offset"] + ay["slope"] * y for y in v]
        arc = [0.0]
        for i in range(1, len(xs)):
            arc.append(arc[-1] + math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]))
        n = max(min_points, min(len(f), int(round(arc[-1] / step)) + 1))
        if n >= len(f):
            continue
        keep = []
        j = 0
        for k in range(n):
            target = arc[-1] * k / (n - 1)
            while j + 1 < len(arc) and abs(arc[j + 1] - target) <= abs(arc[j] - target):
                j += 1
            if not keep or keep[-1] != j:
                keep.append(j)
        c["flow"] = [f[i] for i in keep]
        c["value"] = [v[i] for i in keep]


def load(data):
    from ccp.digitize import DigitizedDocument

    return DigitizedDocument.from_dict(data)


def dumps(data):
    return json.dumps(data, separators=(",", ":"))


def _plot_dict(data, plot_id):
    for p in data.get("plots", []):
        if p["id"] == plot_id:
            return p
    raise KeyError(plot_id)


def plot_label(plot):
    return PARAM_LABELS.get(plot.get("param"), plot.get("param") or "Unrecognized plot")


def cases_overview(data):
    """Rows for the page: one per case, with its plots and status."""
    doc = load(data)
    plots_by_id = {p["id"]: p for p in data.get("plots", [])}
    used = set()
    rows = []
    for case in doc.cases:
        pair = case.curve_pair()
        plots = []
        for param, plot in case.plots.items():
            raw = plots_by_id[plot.id]
            used.add(plot.id)
            plots.append(
                {
                    "id": plot.id,
                    "param": param,
                    "label": plot_label(raw),
                    "short": PARAM_SHORT.get(param, param),
                    "page": plot.page,
                    "n_curves": len(plot.curves),
                    "in_pair": bool(pair and param in pair),
                    "warnings": plot.warnings,
                    "notes": plot.notes,
                    "edited": raw.get("edited", False),
                }
            )
        plots.sort(key=lambda p: (not p["in_pair"], p["page"], p["id"]))
        n_warn = len(case.warnings) + sum(len(p["warnings"]) for p in plots)
        rows.append(
            {
                "name": case.name,
                "slug": case.slug,
                "pages": case.pages,
                "conditions": case.conditions,
                "speeds": case.speeds,
                "pair": pair,
                "warnings": case.warnings,
                "n_warnings": n_warn,
                "plots": plots,
            }
        )
    # recognized plots left out of every case; frames whose axis title was not
    # recognized (logos, tables) are only reported by page
    unassigned = {"plots": [], "pages": []}
    for p in data.get("plots", []):
        if p["id"] in used:
            continue
        if p.get("param"):
            unassigned["plots"].append(
                {
                    "id": p["id"],
                    "page": p["page"],
                    "label": plot_label(p),
                    "warnings": p.get("warnings") or [],
                }
            )
        else:
            unassigned["pages"].append(p["page"])
    unassigned["pages"] = sorted(set(unassigned["pages"]))
    return rows, unassigned


def crop_box(plot):
    """Crop rectangle (page pixels at the plot's dpi) shown by the editor."""
    s = plot["dpi"] / 300
    x0, y0, x1, y1 = plot["box"]
    return [
        max(0, int(x0 - CROP_MARGIN["left"] * s)),
        max(0, int(y0 - CROP_MARGIN["top"] * s)),
        int(x1 + CROP_MARGIN["right"] * s),
        int(y1 + CROP_MARGIN["bottom"] * s),
    ]


def render_plot_png(pdf_bytes, plot, dpi=IMAGE_DPI):
    """PNG of the plot crop, rendered from the PDF page at ``dpi``."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(pdf_bytes)
    try:
        page = pdf[plot["page"] - 1]
        img = page.render(scale=dpi / 72).to_pil()
    finally:
        pdf.close()
    k = dpi / plot["dpi"]
    x0, y0, x1, y1 = crop_box(plot)
    img = img.crop((int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k)))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def editor_payload(data, plot_id):
    """Everything the editor needs for one plot (JSON for the page)."""
    plot = _plot_dict(data, plot_id)
    case_names = [
        c["name"]
        for c in data.get("cases", [])
        if plot_id in c.get("plots", {}).values()
    ]
    x0, y0, x1, y1 = crop_box(plot)
    return {
        # SVG viewBox = the crop in page pixels; the image fills it
        "viewbox": f"{x0} {y0} {x1 - x0} {y1 - y0}",
        "image_rect": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
        "id": plot["id"],
        "page": plot["page"],
        "param": plot.get("param"),
        "label": plot_label(plot),
        "units": plot.get("units") or "",
        "flow_units": plot.get("flow_units") or "",
        "crop": crop_box(plot),
        "box": plot["box"],
        "x_axis": plot.get("x_axis"),
        "y_axis": plot.get("y_axis"),
        "speeds": plot.get("speeds") or [],
        # tick values the calibration was fitted on: drawn at their calibrated
        # position so a misread axis shows against the printed labels
        "x_ticks": [t[0] for t in plot.get("x_ticks") or []],
        "y_ticks": [t[0] for t in plot.get("y_ticks") or []],
        "tick_labels": {
            "x": ", ".join(f"{t[0]:g}" for t in plot.get("x_ticks") or []),
            "y": ", ".join(f"{t[0]:g}" for t in plot.get("y_ticks") or []),
        },
        "warnings": plot.get("warnings") or [],
        "notes": plot.get("notes") or [],
        "edited": plot.get("edited", False),
        "cases": case_names,
        "curves": [
            {
                "speed": c.get("speed"),
                "points": [[f, v] for f, v in zip(c["flow"], c["value"])],
            }
            for c in plot.get("curves", [])
        ],
    }


def _finite(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def update_plot(data, plot_id, curves):
    """Replace a plot's curves with edited ones (data coordinates).

    ``curves`` is ``[{"speed": rpm, "points": [[flow, value], ...]}]``. Points
    are sorted by flow; lines with fewer than two points or no speed are
    dropped (a line needs a speed to become an ``Impeller`` curve).
    """
    plot = _plot_dict(data, plot_id)
    clean = []
    errors = []
    for i, c in enumerate(curves or []):
        speed = _finite(c.get("speed"))
        pts = []
        for p in c.get("points") or []:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                continue
            f, v = _finite(p[0]), _finite(p[1])
            if f is not None and v is not None:
                pts.append((f, v))
        pts.sort()
        if speed is None or speed <= 0:
            errors.append(f"line {i + 1}: no speed")
            continue
        if len(pts) < 2:
            errors.append(f"line {i + 1} ({speed:g} rpm): fewer than two points")
            continue
        clean.append(
            {
                "speed": speed,
                "flow": [p[0] for p in pts],
                "value": [p[1] for p in pts],
            }
        )
    speeds = [c["speed"] for c in clean]
    if len(set(speeds)) != len(speeds):
        raise InputError({"curves": "Two lines have the same speed"})
    clean.sort(key=lambda c: c["speed"])
    plot["curves"] = clean
    plot["edited"] = True
    return errors


def reset_plot(data, original, plot_id):
    """Restore a plot's curves from the original digitization."""
    plot = _plot_dict(data, plot_id)
    orig = _plot_dict(original, plot_id)
    plot["curves"] = orig["curves"]
    plot["edited"] = False


def export_zip(data):
    """Zip of the Engauge CSVs (``<case>-<param>.csv``) and ``digitized.json``."""
    doc = load(data)
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory(prefix="ccp-digitize-") as tmp:
        folder = doc.save(tmp)
        (Path(folder) / "digitized.json").write_text(json.dumps(data, indent=1))
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(Path(folder).rglob("*")):
                if path.is_file():
                    z.write(path, path.relative_to(folder).as_posix())
    return buf.getvalue()


# ----------------------------------------------------------------- hand-off

# Units the curves conversion page reads its design-case CSVs in.
CONVERSION_UNITS = {
    "flow": "m³/h",
    "head": "kJ/kg",
    "power_shaft": "kW",
    "power": "kW",
    "disch_p": "bar",
    "disch_T": "degC",
}
CONVERSION_STATE_UNITS = {
    "loaded_curves_speed_units": "rpm",
    "loaded_curves_flow_units": "m³/h",
    "loaded_curves_head_units": "kJ/kg",
    "loaded_curves_power_units": "kW",
    "loaded_curves_disch_p_units": "bar",
    "loaded_curves_disch_T_units": "degC",
    "design_suc_p_unit": "bar",
    "design_suc_T_unit": "degC",
}


def _convert(values, src, dst):
    if not src or not dst or src == dst:
        return list(values)
    import ccp

    return list(ccp.Q_(list(values), src).to(dst).m)


def _csv_for_conversion(plot):
    """Engauge CSV text of a plot in the conversion page's units."""
    lines = []
    dst = CONVERSION_UNITS.get(plot.param)
    for c in sorted(plot.curves, key=lambda c: c["speed"] or 0):
        if c["speed"] is None:
            continue
        flow = _convert(c["flow"], plot.flow_units, CONVERSION_UNITS["flow"])
        value = _convert(c["value"], plot.units if dst else None, dst)
        lines.append(f"x,{int(round(c['speed']))}")
        lines += [f"{f:.6g},{v:.6g}" for f, v in zip(flow, value)]
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def conversion_cases(data, slugs, letters=("A", "B", "C", "D", "E")):
    """Design cases for a new curves conversion case.

    Returns ``(state_updates, files)`` where ``files`` is a list of
    ``(key, name, bytes)`` for the ``curves_file_<n>_case_<X>`` slots. Each
    digitized case gets its own named gas (label and molecular weight from the
    sheet); its composition must be filled in on the conversion page.
    """
    doc = load(data)
    by_slug = {c.slug: c for c in doc.cases}
    chosen = [by_slug[s] for s in slugs if s in by_slug][: len(letters)]
    if not chosen:
        raise InputError({"to_conversion": "Select at least one digitized case"})
    state = dict(CONVERSION_STATE_UNITS)
    files = []
    from . import gas as gas_service

    table = gas_service.default_table()
    for i, (letter, case) in enumerate(zip(letters, chosen)):
        pair = case.curve_pair()
        if pair is None:
            raise InputError(
                {"to_conversion": f"{case.name}: no pair of curves to define the map"}
            )
        cond = case.conditions
        gas_label = cond.get("gas") or "gas"
        mw = cond.get("mw")
        name = f"{letter} {gas_label}" + (f" MW {mw:g}" if mw else "")
        state[f"gas_{i}"] = name
        table[f"gas_{i}"]["name"] = name
        state[f"gas_case_{letter}"] = name
        p = cond.get("p")
        T = cond.get("T")
        if p:
            state[f"suc_p_case_{letter}"] = _convert([p[0]], p[1], "bar")[0]
        if T:
            state[f"suc_T_case_{letter}"] = _convert([T[0]], T[1], "degC")[0]
        for n, param in enumerate(pair, start=1):
            files.append(
                (
                    f"curves_file_{n}_case_{letter}",
                    f"{case.slug}-{param}.csv",
                    _csv_for_conversion(case.plots[param]),
                )
            )
    state["gas_compositions_table"] = table
    return state, files
