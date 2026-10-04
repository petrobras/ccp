"""Document level: pages -> plots -> cases, metadata and exports."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ._axes import (
    calibrate_axis,
    classify_x_title,
    classify_y_title,
    read_x_title,
    read_y_title,
)
from ._curves import extract_curves
from ._image import Box, dark_mask, find_plot_boxes, render_page
from ._ocr import ocr_text, parse_number

__all__ = ["DigitizedPlot", "DigitizedCase", "DigitizedDocument", "digitize_pdf"]

PARAMS = ["head", "eff", "power", "power_shaft", "pressure_ratio", "disch_p", "disch_T"]


# --------------------------------------------------------------------- results


@dataclass
class DigitizedPlot:
    page: int  # 1-based page number
    index: int  # plot index on the page (top to bottom)
    box: tuple  # (x0, y0, x1, y1) pixels at ``dpi``
    dpi: int
    param: str = None
    units: str = None
    flow_units: str = None
    y_title: str = ""
    x_title: str = ""
    speeds: list = field(default_factory=list)  # legend speeds (RPM)
    legend_readings: list = field(default_factory=list)  # raw OCR variants
    candidates: list = field(default_factory=list)  # every traced stroke
    curves: list = field(default_factory=list)  # [{"speed", "flow", "value", "px"}]
    x_ticks: list = field(default_factory=list)
    y_ticks: list = field(default_factory=list)
    x_residual: float = None
    y_residual: float = None
    # page-pixel calibration at ``dpi``: pixel = offset + slope * value
    x_axis: dict = None
    y_axis: dict = None
    warnings: list = field(default_factory=list)  # things to check
    notes: list = field(default_factory=list)  # what the physics step changed
    source: str = "raster"  # "vector" when read from the PDF drawing itself
    labeled: bool = False  # every line carries its own speed label
    envelopes: list = field(default_factory=list)  # surge/choke/control lines
    reference: tuple = None  # rated point printed on the axes (flow, value)

    @property
    def ok(self):
        return self.param is not None and bool(self.curves)

    @property
    def id(self):
        return f"{self.page}-{self.index}"

    def to_pixels(self, flow, value):
        """Page pixels (at ``dpi``) of data points, using the axis calibration."""
        x = self.x_axis["offset"] + self.x_axis["slope"] * np.asarray(flow, float)
        y = self.y_axis["offset"] + self.y_axis["slope"] * np.asarray(value, float)
        return x, y

    def to_data(self, x, y):
        """Data values (flow, value) of page pixels at ``dpi``."""
        flow = (np.asarray(x, float) - self.x_axis["offset"]) / self.x_axis["slope"]
        value = (np.asarray(y, float) - self.y_axis["offset"]) / self.y_axis["slope"]
        return flow, value

    _FIELDS = (
        "page",
        "index",
        "dpi",
        "param",
        "units",
        "flow_units",
        "y_title",
        "x_title",
        "speeds",
        "legend_readings",
        "x_ticks",
        "y_ticks",
        "x_residual",
        "y_residual",
        "x_axis",
        "y_axis",
        "warnings",
        "notes",
        "source",
        "labeled",
        "reference",
    )

    def to_dict(self):
        """JSON-ready dict (the traced pixel paths and stroke candidates are
        left out: they only serve the digitization itself)."""
        out = {k: _plain(getattr(self, k)) for k in self._FIELDS}
        out["id"] = self.id
        out["box"] = [int(v) for v in self.box]
        out["curves"] = [
            {
                "speed": None if c["speed"] is None else float(c["speed"]),
                "flow": [float(v) for v in c["flow"]],
                "value": [float(v) for v in c["value"]],
                **({"label": c["label"]} if c.get("label") else {}),
            }
            for c in self.curves
        ]
        out["envelopes"] = [
            {"flow": _plain(e["flow"]), "value": _plain(e["value"])}
            for e in self.envelopes
        ]
        return out

    @classmethod
    def from_dict(cls, d):
        kwargs = {k: d.get(k) for k in cls._FIELDS if k in d}
        for k in (
            "speeds",
            "legend_readings",
            "x_ticks",
            "y_ticks",
            "warnings",
            "notes",
        ):
            kwargs[k] = list(kwargs.get(k) or [])
        if kwargs.get("reference") is not None:
            kwargs["reference"] = tuple(kwargs["reference"])
        plot = cls(box=tuple(d["box"]), **kwargs)
        plot.curves = [
            {
                "speed": c.get("speed"),
                "flow": np.asarray(c["flow"], float),
                "value": np.asarray(c["value"], float),
                **({"label": c["label"]} if c.get("label") else {}),
            }
            for c in d.get("curves", [])
        ]
        plot.envelopes = [
            {
                "flow": np.asarray(e["flow"], float),
                "value": np.asarray(e["value"], float),
            }
            for e in d.get("envelopes", [])
        ]
        return plot

    def curves_dict(self):
        """``{speed: {"x1": flow, "x2": value}}`` as used by ``load_from_dict``."""
        out = {}
        for c in self.curves:
            if c["speed"] is None:
                continue
            out[str(int(round(c["speed"])))] = {
                "x1": list(map(float, c["flow"])),
                "x2": list(map(float, c["value"])),
            }
        return out

    def to_engauge_csv(self, path=None):
        """Engauge-format CSV text (``x,<speed>`` blocks); written to ``path``
        when given."""
        lines = []
        for speed, d in self.curves_dict().items():
            lines.append(f"x,{speed}")
            lines += [f"{x:.6g},{y:.6g}" for x, y in zip(d["x1"], d["x2"])]
            lines.append("")
        text = "\n".join(lines)
        if path is not None:
            Path(path).write_text(text)
        return text

    def summary(self):
        return {
            "page": self.page,
            "index": self.index,
            "param": self.param,
            "units": self.units,
            "flow_units": self.flow_units,
            "speeds": self.speeds,
            "n_curves": len(self.curves),
            "x_ticks": [t[0] for t in self.x_ticks],
            "y_ticks": [t[0] for t in self.y_ticks],
            "x_residual_px": self.x_residual,
            "y_residual_px": self.y_residual,
            "warnings": self.warnings,
            "notes": self.notes,
            "source": self.source,
            "reference": self.reference,
        }


PAIR_PREFERENCE = (
    ("disch_p", "disch_T"),
    ("pressure_ratio", "disch_T"),
    ("head", "eff"),
    ("head", "power_shaft"),
    ("pressure_ratio", "eff"),
)


@dataclass
class DigitizedCase:
    name: str
    pages: list = field(default_factory=list)
    conditions: dict = field(default_factory=dict)
    plots: dict = field(default_factory=dict)  # param -> DigitizedPlot
    speeds: list = field(default_factory=list)  # legend consensus (RPM)
    flow_ranges: dict = field(default_factory=dict)  # speed -> (surge, choke)
    warnings: list = field(default_factory=list)

    @property
    def slug(self):
        return slugify(self.name)

    def curve_pair(self):
        """The two curves that define the map, in order of preference.

        Discharge pressure (or pressure ratio) and discharge temperature come
        first: their lines are ordered by speed and never cross, so they trace
        more reliably than efficiency lines, which overlap near surge.
        """
        for pair in PAIR_PREFERENCE:
            if all(p in self.plots and self.plots[p].ok for p in pair):
                return pair
        return None

    def load_kwargs(self, pair=None):
        """Keyword arguments for ``ccp.Impeller.load_from_dict`` (except ``suc``)."""
        pair = pair or self.curve_pair()
        if pair is None:
            raise ValueError(f"case {self.name!r} has no usable pair of curves")
        kw = {}
        flow_units = None
        for p in pair:
            plot = self.plots[p]
            kw[f"{p}_curves"] = plot.curves_dict()
            if plot.units:
                kw[f"{p}_units"] = plot.units
            flow_units = flow_units or plot.flow_units
            kw[f"flow_units_{p}"] = plot.flow_units
        kw["flow_units"] = flow_units
        if kw.get("eff_units") == "percent":
            # ccp detects percent efficiency itself (values above 1)
            kw.pop("eff_units")
        return kw

    def impeller(self, suc, pair=None, **kwargs):
        """Build a ``ccp.Impeller`` from the digitized curves."""
        import ccp

        kw = self.load_kwargs(pair)
        kw.update(kwargs)
        return ccp.Impeller.load_from_dict(suc=suc, **kw)

    def to_dict(self):
        return {
            "name": self.name,
            "pages": list(self.pages),
            "conditions": _plain(self.conditions),
            "speeds": _plain(self.speeds),
            "flow_ranges": {
                str(float(k)): [float(v) for v in r]
                for k, r in self.flow_ranges.items()
            },
            "warnings": list(self.warnings),
            "plots": {p: plot.id for p, plot in self.plots.items()},
        }

    @classmethod
    def from_dict(cls, d, plots_by_id):
        return cls(
            name=d["name"],
            pages=list(d.get("pages", [])),
            conditions=dict(d.get("conditions", {})),
            plots={p: plots_by_id[i] for p, i in d.get("plots", {}).items()},
            speeds=list(d.get("speeds", [])),
            flow_ranges={
                float(k): tuple(v) for k, v in d.get("flow_ranges", {}).items()
            },
            warnings=list(d.get("warnings", [])),
        )

    def summary(self):
        return {
            "name": self.name,
            "slug": self.slug,
            "pages": self.pages,
            "conditions": self.conditions,
            "speeds": self.speeds,
            "flow_ranges": {str(int(k)): v for k, v in self.flow_ranges.items()},
            "warnings": self.warnings,
            "pair": self.curve_pair(),
            "plots": {p: plot.summary() for p, plot in self.plots.items()},
        }


@dataclass
class DigitizedDocument:
    path: str
    n_pages: int
    cases: list = field(default_factory=list)
    plots: list = field(default_factory=list)
    toc: list = field(default_factory=list)

    def __getitem__(self, name):
        for c in self.cases:
            if name in (c.name, c.slug):
                return c
        raise KeyError(name)

    def plot(self, plot_id):
        for p in self.plots:
            if p.id == plot_id:
                return p
        raise KeyError(plot_id)

    def to_dict(self):
        """JSON-ready dict of the whole result (``from_dict`` reads it back)."""
        return {
            "format": "ccp-digitized/1",
            "path": str(self.path),
            "n_pages": self.n_pages,
            "toc": [list(t) for t in self.toc],
            "plots": [p.to_dict() for p in self.plots],
            "cases": [c.to_dict() for c in self.cases],
        }

    @classmethod
    def from_dict(cls, d):
        plots = [DigitizedPlot.from_dict(p) for p in d.get("plots", [])]
        by_id = {p.id: p for p in plots}
        return cls(
            path=d.get("path", ""),
            n_pages=d.get("n_pages", 0),
            toc=[tuple(t) for t in d.get("toc", [])],
            plots=plots,
            cases=[DigitizedCase.from_dict(c, by_id) for c in d.get("cases", [])],
        )

    def summary(self):
        return {
            "path": str(self.path),
            "n_pages": self.n_pages,
            "toc": self.toc,
            "cases": [c.summary() for c in self.cases],
        }

    def save(self, folder):
        """Write one Engauge CSV per case and curve plus ``digitized.json``.

        Files are named ``<case slug>-<param>.csv`` so that
        ``ccp.Impeller.load_from_engauge_csv(curve_name=<slug>, ...)`` reads
        them; only the map-defining pair is written at the top level, every
        other curve goes to ``extra/``.
        """
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "extra").mkdir(exist_ok=True)
        for case in self.cases:
            pair = case.curve_pair() or ()
            for p, plot in case.plots.items():
                if not plot.ok:
                    continue
                target = folder if p in pair else folder / "extra"
                plot.to_engauge_csv(target / f"{case.slug}-{p}.csv")
        (folder / "digitized.json").write_text(
            json.dumps(self.summary(), indent=2, default=_json_default)
        )
        return folder


def _plain(o):
    """Recursively convert numpy scalars/arrays and tuples to JSON types."""
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_plain(v) for v in o.tolist()]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return o


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def slugify(name):
    s = name.lower()
    s = re.sub(r"operating (condition|point)", "case", s)
    s = re.sub(r"\(.*?\)|<.*?>", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# --------------------------------------------------------------------- page text

_TOC_LINE = re.compile(
    r"^\s*(?:(?P<num>\d+(?:\.\d+)*)\s+)?(?P<title>\S.*?)\s*[._]{4,}\s*(?P<page>\d+)\s*$"
)

_COND = {
    "gas": r"GAS HANDLED\s*:?[ \t]*([^\n]+?)\s*$",
    "mw": r"MOL(?:ECULAR|\.)\s*WEIGHT\s*:?\s*([\d.,]+)\s*(\S+)?",
    "p": r"(?:INLET|SUCTION) PRESSURE\s*:?\s*([\d.,]+)\s*(\S+)?",
    "T": (
        r"(?:INLET|SUCTION) TEMP(?:ERATURE|\.)?\s*:?\s*([-\d.,]+)"
        r"\s*(\S+(?:\s+[CFK]\b)?)?"
    ),
    "z": r"COMPRESS(?:IBILITY|\.)(?: AT SUCTION)?\s*:?\s*([\d.,]+)",
    "speed": r"100\s*%\s*[-−–]?\s*SPEED\s*:?\s*([\d.,]+)\s*RPM",
}

# compact conditions table: Ps / Pd / Ts / Td / Flow / MW / Zs
# and the 100 % speed; the rated point is kept to check the curves against
_P_UNIT = r"(kPa|bar|MPa|psi|kgf/cm2|kgf/cm²)"
_T_UNIT = r"[°º*]?\s*([CFK])\b"
_COND_TABLE = {
    "p": rf"\bP[sS1]\b\s*[:=]?\s*([\d.,]+)\s*{_P_UNIT}",
    "T": rf"\bT[sS]\b\s*[:=]?\s*([-\d.,]+)\s*{_T_UNIT}",
    "mw": r"\bMW\b\s*[:=]?\s*([\d.,]+)",
    "z": r"\bZ[sS1]\b\s*[:=]?\s*([\d.,]+)",
    "disch_p": rf"\bP[dD]\b\s*[:=]?\s*([\d.,]+)\s*{_P_UNIT}",
    "disch_T": rf"\bT[dD]\b\s*[:=]?\s*([-\d.,]+)\s*{_T_UNIT}",
    "flow": (
        r"(?<![.\w])Flow\b\s*:?\s*([\d.,]+)"
        r"\s*(m[³3]\s*/\s*(?:min|h|hr|s)|ACFM|CFM|kg\s*/\s*h)"
    ),
    "speed": r"(?i)100\s*%\s*[-−–]?\s*Speed\s*[:=]?\s*([\d.,]+)\s*RPM",
}

_TEMP_UNITS = {"C": "degC", "F": "degF", "K": "degK"}


def _pressure_units(unit):
    """Units of a printed suction pressure (bar when not printed)."""
    if not unit:
        return "bar"
    u = unit.upper().replace(" ", "")
    for key, name in (
        ("KGF/CM", "kgf/cm²"),
        ("KG/CM", "kgf/cm²"),
        ("KPA", "kPa"),
        ("MPA", "MPa"),
        ("PSI", "psi"),
        ("BAR", "bar"),
    ):
        if key in u:
            return name
    return unit


def _units(text):
    t = re.sub(r"\s+", "", text)
    t = t.replace("m3", "m³").replace("hr", "h")
    return {"kgf/cm2": "kgf/cm²", "ACFM": "ft³/min", "CFM": "ft³/min"}.get(t, t)


_HEADER = re.compile(
    r"(?P<h>[^\n]*?\b(?:CASE|OPERATING\s+(?:CONDITION|POINT)|OVERALL|PHASE|SECTION|STAGE)\b[^\n]*)",
    re.IGNORECASE,
)


def parse_toc(texts):
    """Table-of-contents entries ``[(title, first_page)]`` from all pages.

    Numbered hierarchical entries (``2 COMPRESSOR X SECTION 1`` / ``2.1 CASE
    A``) are flattened to the leaf entries with their parent titles.
    """
    entries = []
    for text in texts:
        for line in text.splitlines():
            m = _TOC_LINE.match(line)
            if not m:
                continue
            title = re.sub(r"\s+", " ", m.group("title")).strip(" .")
            entries.append((m.group("num"), title, int(m.group("page"))))
    if not entries:
        return []
    leaves = []
    parents = {}
    for i, (num, title, page) in enumerate(entries):
        if num:
            parents[num] = title
            parent = ".".join(num.split(".")[:-1])
            has_child = any(
                n and n.startswith(num + ".") for n, _, _ in entries[i + 1 :]
            )
            if has_child:
                continue
            full = f"{parents[parent]} {title}" if parent in parents else title
            leaves.append((full, page))
        else:
            leaves.append((title, page))
    return leaves


def parse_conditions(text):
    """Suction conditions (and rated point, when printed) from a sheet's text.

    Two layouts are recognized: a block of labelled lines ("INLET PRESSURE :
    ...") and a compact symbol table (``Ps 20 bar``, ``Ts 30 C``, ``MW 20``).
    Pressures and temperatures are ``[value, units]``.
    """
    out = {}
    for key, pat in _COND.items():
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if not m:
            continue
        if key == "gas":
            out[key] = m.group(1).strip()
            continue
        try:
            val = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        if key == "p":
            out["p"] = [val, _pressure_units(unit)]
        elif key == "T":
            u = re.sub(r"[^A-Z]", "", (unit or "C").upper()).replace("DEG", "")
            out["T"] = [val, _TEMP_UNITS.get(u[:1], unit) if u else "degC"]
        else:
            out[key] = val
    if "p" in out or "T" in out:
        return out
    for key, pat in _COND_TABLE.items():
        m = re.search(pat, text)
        if not m:
            continue
        try:
            val = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        if key in ("p", "disch_p", "flow"):
            out[key] = [val, _units(m.group(2))]
        elif key in ("T", "disch_T"):
            out[key] = [val, _TEMP_UNITS[m.group(2).upper()]]
        else:
            out[key] = val
    return out


def page_header(text):
    """Case label printed on top of a curve sheet, if any."""
    for line in text.splitlines()[:40]:
        line = line.strip()
        if not line or len(line) > 90 or "CURVES ARE VALID" in line.upper():
            continue
        if re.search(r"TABLE OF CONTENTS|PERFORMANCE CURVES|TITLE", line, re.I):
            continue
        if _HEADER.search(line):
            return re.sub(r"\s+", " ", line)
    return None


# --------------------------------------------------------------------- per plot

_SPEED = re.compile(r"(?:\b([A-H])\b\W{0,3})?(\d{3,6})\s*R\s*P\s*M", re.IGNORECASE)


def read_legend(img, box, rects, offset, s):
    """Speed lists (RPM) read from the legend box, one per OCR variant.

    The legend is the rectangle whose text mentions RPM; it is read with
    several preprocessings because low-resolution sheets defeat any single one.
    The case-level vote (``legend_consensus``) picks the consistent reading.
    """
    import pytesseract

    from ._ocr import _prepare

    ox, oy = offset
    readings = []
    up = 1.0 if s >= 1.5 else 2.0
    for r in sorted(rects, key=lambda r: -(r.width * r.height)):
        crop = img[oy + r.y0 : oy + r.y1, ox + r.x0 : ox + r.x1]
        found = []
        for kw in (
            dict(scale=up),
            dict(scale=up, blur=1.0),
            dict(scale=1.5 * up, binarize=160),
        ):
            text = pytesseract.image_to_string(_prepare(crop, **kw), config="--psm 6")
            speeds = [float(m.group(2)) for m in _SPEED.finditer(text)]
            if speeds:
                found.append(speeds)
        if found:
            readings += found
            break
    return readings


_BOX_WORDS = re.compile(r"RPM|REFER|SURGE|POINT|COORD|LINE|STONEWALL|CHOKE|PSV", re.I)


def text_boxes(img, box, s):
    """Legend and info boxes inside a plot, located from their text.

    One OCR pass over the plot interior finds the legend words (RPM,
    reference point, surge line...) and other text boxes (notes); each
    group of lines is grown to its enclosing border. Returns
    ``(regions, legend_region)`` in page pixels.
    """
    from ._image import Box, dark_mask
    from ._ocr import ocr_words

    up = 2.0 if s < 1.5 else 1.0
    inner = img[box.y0 + 4 : box.y1 - 3, box.x0 + 4 : box.x1 - 3]
    words = [
        w.shifted(box.x0 + 4, box.y0 + 4)
        for w in ocr_words(inner, psm=11, scale=up, min_conf=30)
    ]
    hits = [w for w in words if _BOX_WORDS.search(w.text)]
    if not hits:
        return [], None
    line_h = np.median([w.y1 - w.y0 for w in hits])
    # cluster hit words into blocks (vertically close, horizontally overlapping)
    blocks = []
    for w in sorted(hits, key=lambda w: w.y0):
        for b in blocks:
            if (
                w.y0 - b[3] < 2.5 * line_h
                and w.x0 < b[2] + 200 * s
                and w.x1 > b[0] - 200 * s
            ):
                b[0], b[1] = min(b[0], w.x0), min(b[1], w.y0)
                b[2], b[3] = max(b[2], w.x1), max(b[3], w.y1)
                b[4].append(w)
                break
        else:
            blocks.append([w.x0, w.y0, w.x1, w.y1, [w]])
    dark = dark_mask(img, 200)
    regions = []
    legend = None
    for x0, y0, x1, y1, ws in blocks:
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        limit = int(0.4 * box.width)

        def grow(edge, step, lo, hi, vertical):
            pos = edge
            for _ in range(limit):
                nxt = pos + step
                if not (
                    box.x0 + 2 <= nxt <= box.x1 - 2
                    if vertical
                    else box.y0 + 2 <= nxt <= box.y1 - 2
                ):
                    break
                seg = dark[lo:hi, nxt] if vertical else dark[nxt, lo:hi]
                pos = nxt
                if seg.mean() > 0.8:
                    return pos
            return None

        left = grow(x0, -1, y0, y1, True)
        right = grow(x1, 1, y0, y1, True)
        r = Box(
            left if left is not None else x0 - int(130 * s),
            y0 - int(line_h),
            right if right is not None else x1 + int(10 * s),
            y1 + int(line_h),
        )
        top = grow(y0, -1, r.x0 + 3, r.x1 - 3, False)
        bottom = grow(y1, 1, r.x0 + 3, r.x1 - 3, False)
        r = Box(
            r.x0,
            top if top is not None else r.y0,
            r.x1,
            bottom if bottom is not None else r.y1,
        )
        if r.width > 0.5 * box.width or r.height > 0.5 * box.height:
            continue  # no border found: never blank half the plot
        regions.append(r)
        if any("RPM" in w.text.upper() for w in ws):
            legend = r
    return regions, legend


def _descending(values):
    return all(a > b for a, b in zip(values, values[1:]))


def legend_consensus(readings):
    """Speeds of a case from the legend readings of its plots.

    Every plot of a case repeats the same legend; OCR slips (``8500`` read as
    ``83500``) break the descending order the legends are printed in, so the
    most common descending reading wins. Without one, each position is voted.
    """
    from collections import Counter

    readings = [tuple(r) for r in readings if r]
    if not readings:
        return []
    good = [r for r in readings if _descending(r)]
    if good:
        # a dropped line is a more common OCR slip than an invented one
        n = max(len(r) for r in good)
        return list(Counter(r for r in good if len(r) == n).most_common(1)[0][0])
    n = Counter(len(r) for r in readings).most_common(1)[0][0]
    same = [r for r in readings if len(r) == n]
    out = []
    for i in range(n):
        for v, _ in Counter(r[i] for r in same).most_common():
            if not out or v < out[-1]:
                out.append(v)
                break
        else:
            return []
    return out


def _resample(x, y, n_max=40):
    """Thin a dense pixel path to at most ``n_max`` points with increasing x."""
    keep_x, keep_y = [x[0]], [y[0]]
    for xi, yi in zip(x[1:], y[1:]):
        if xi > keep_x[-1]:
            keep_x.append(xi)
            keep_y.append(yi)
    x, y = np.array(keep_x), np.array(keep_y)
    if len(x) <= n_max:
        return x, y
    # uniform in arc length (normalized), so steep parts keep enough points
    sx = (x - x.min()) / max(np.ptp(x), 1e-12)
    sy = (y - y.min()) / max(np.ptp(y), 1e-12)
    arc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(sx), np.diff(sy)))])
    idx = np.unique(
        np.searchsorted(arc, np.linspace(0, arc[-1], n_max)).clip(0, len(x) - 1)
    )
    return x[idx], y[idx]


def digitize_plot(img, box, page_no, index, dpi, n_points=40):
    s = dpi / 300
    dark = dark_mask(img)
    plot = DigitizedPlot(page=page_no, index=index, box=box.as_tuple(), dpi=dpi)
    plot.y_title = read_y_title(img, box, s).strip()
    plot.x_title = read_x_title(img, box, s).strip()
    plot.param, plot.units = classify_y_title(plot.y_title)
    plot.flow_units, _ = classify_x_title(plot.x_title)
    if plot.param is None:
        plot.warnings.append("y-axis title not recognized")
        return plot
    xcal = calibrate_axis(img, dark, box, "x", s)
    ycal = calibrate_axis(img, dark, box, "y", s)
    if xcal is None or ycal is None:
        plot.warnings.append(
            f"axis calibration failed (x: {xcal is not None}, y: {ycal is not None})"
        )
        return plot
    plot.x_ticks, plot.y_ticks = xcal.ticks, ycal.ticks
    plot.x_axis = {"offset": xcal.offset, "slope": xcal.slope}
    plot.y_axis = {"offset": ycal.offset, "slope": ycal.slope}
    plot.x_residual, plot.y_residual = xcal.residual, ycal.residual
    for name, cal in (("x", xcal), ("y", ycal)):
        if len(cal.ticks) < 3:
            plot.warnings.append(
                f"{name} axis calibrated from {len(cal.ticks)} ticks only"
            )
    # legend first: its speed count guides the curve selection
    from ._curves import clean_mask

    regions, legend = text_boxes(img, box, s)
    _, offset, rects = clean_mask(img, box, s)
    if legend is not None:
        ox, oy = offset
        rects = [Box(legend.x0 - ox, legend.y0 - oy, legend.x1 - ox, legend.y1 - oy)]
    plot.legend_readings = read_legend(img, box, rects, offset, s)
    plot.speeds = legend_consensus(plot.legend_readings)
    # cap the line count by the longest reading: a reading that missed a
    # speed must not make the tracer drop a (short, low-speed) line
    n = max((len(r) for r in plot.legend_readings), default=0) or None
    curves, dbg = extract_curves(img, box, s, n_expected=n, blank=regions)
    for c in dbg["candidates"]:
        px, py = _resample(c.x, c.y, n_points)
        plot.candidates.append(
            {"flow": xcal.to_value(px), "value": ycal.to_value(py), "cost": c.cost}
        )
    if plot.units is None:
        if plot.param == "eff":
            vals = ycal.to_value([box.y0, box.y1])
            plot.units = "percent" if max(vals) > 1.5 else "dimensionless"
        elif plot.param == "head":
            plot.units = "kJ/kg"
            plot.warnings.append("head units not read, assuming kJ/kg")
    if not plot.speeds:
        plot.warnings.append("legend speeds not read")
    for c in sorted(curves, key=lambda c: c.x[-1]):
        px, py = _resample(c.x, c.y, n_points)
        plot.curves.append(
            {
                "speed": None,
                "flow": xcal.to_value(px),
                "value": ycal.to_value(py),
                "px": np.column_stack([px, py]),
            }
        )
    return plot


# --------------------------------------------------------------------- document


def _open(path):
    import pypdfium2

    return pypdfium2.PdfDocument(str(path))


def _process_page(path, no, dpi, n_points, text, mode="auto", ocr_info=True):
    doc = _open(path)
    try:
        page = doc[no - 1]
        img = render_page(page, dpi)
        plots = []
        if mode != "raster":
            plots, text = _vector_page(page, img, no, dpi, n_points, text)
        if plots:
            boxes = [Box(*p.box) for p in plots]
        elif mode == "vector":
            return no, dict(header=None, conditions={}, n_plots=0), []
        else:
            boxes = find_plot_boxes(img, dpi=dpi)
            boxes = [b for b in boxes if b.width >= 0.3 * img.shape[1]]
        header, conditions = page_header(text), parse_conditions(text)
        readings = [conditions] if conditions else []
        if ocr_info and boxes and not header and not conditions:
            # titles and tables are sometimes drawn as outlines (no text
            # layer): read them from the image, without the plots (not
            # needed when a table of contents names the cases)
            header, readings = _ocr_page_info(page, boxes, dpi)
            conditions = vote_conditions(readings)
    finally:
        doc.close()
    info = dict(
        header=header,
        conditions=conditions,
        condition_readings=readings,
        n_plots=len(boxes),
    )
    if not plots:
        for i, box in enumerate(boxes):
            plots.append(digitize_plot(img, box, no, i, dpi, n_points))
    return no, info, plots


# physically sensible suction / rated values, to reject OCR slips (a lost
# decimal point turns 30.00 degC into 3000 degC)
_PLAUSIBLE = {
    "T": (-150, 400),
    "disch_T": (-100, 700),
    "mw": (1, 200),
    "z": (0.1, 1.5),
    "speed": (100, 100_000),
}


def _plausible(key, value):
    lo, hi = _PLAUSIBLE.get(key, (None, None))
    v = value[0] if isinstance(value, list) else value
    if not isinstance(v, (int, float)):
        return True
    if key in ("T", "disch_T") and isinstance(value, list) and value[1] != "degC":
        return True
    return (lo is None or v >= lo) and (hi is None or v <= hi)


def vote_conditions(readings):
    """Most common plausible value of each condition over several readings."""
    from collections import Counter

    out = {}
    keys = {k for r in readings for k in r}
    for k in keys:
        vals = [r[k] for r in readings if k in r and _plausible(k, r[k])]
        if not vals:
            continue
        counts = Counter(json.dumps(v) for v in vals)
        out[k] = json.loads(counts.most_common(1)[0][0])
    return out


def _ocr_page_info(page, boxes, dpi):
    """Case header and conditions read by OCR outside the plots.

    The page is rendered at twice the working resolution (decimal points of
    small table text vanish at 300 dpi) and read with sparse-text and
    block segmentation, which fail on different words; each value is voted
    over the readings once implausible ones are dropped.
    """
    from collections import Counter

    hi = min(2 * dpi, 600)
    k = hi / dpi
    img = render_page(page, hi)
    for b in boxes:
        img[
            int(b.y0 * k) : int((b.y1 + 1) * k), int(b.x0 * k) : int((b.x1 + 1) * k)
        ] = 255
    headers, readings = [], []
    for psm in (11, 6):
        text = ocr_text(img, psm=psm, scale=1.0)
        h = page_header(text)
        if h:
            headers.append(h)
        readings.append(parse_conditions(text))
    header = Counter(headers).most_common(1)[0][0] if headers else None
    return header, readings


def _vector_page(page, img, no, dpi, n_points, text):
    """Vector plots of a page and its text rebuilt in rows (see ``_vector``)."""
    from ._pdf import PageMap, page_paths, page_words, text_rows
    from ._vector import vector_plots

    h, w = img.shape[:2]
    pmap = PageMap(page, w, h)
    words = page_words(page, pmap)
    if sum(parse_number(t.text) is not None for t in words) < 6:
        return [], text  # no tick labels in the text layer
    rows = text_rows(words) or text
    plots, _ = vector_plots(
        no, words, page_paths(page, pmap), (w, h), dpi, n_points, text=rows
    )
    return plots, rows


def digitize_pdf(
    path, dpi=300, pages=None, progress=None, n_points=40, workers=None, mode="auto"
):
    """Digitize every performance plot of a curve PDF.

    Parameters
    ----------
    path : str or Path
        PDF file.
    dpi : int
        Rendering resolution. 300 dpi suits both high-resolution strips and
        low-resolution embedded images.
    pages : iterable of int, optional
        1-based page numbers to process (default: all).
    progress : callable, optional
        Called as ``progress(done, total)`` after each page. An exception
        raised by it stops the digitization (queued pages are dropped).
    n_points : int
        Maximum number of points kept per speed line.
    workers : int, optional
        Pages processed in parallel (spawned processes). Default: serial.
    mode : {"auto", "vector", "raster"}
        How plots are read. ``"auto"`` reads plots drawn as vector graphics
        with a text layer straight from the PDF (exact, no OCR) and falls back
        to the rendered image for the others; ``"raster"`` always uses the
        image, ``"vector"`` never does.

    Returns
    -------
    DigitizedDocument
    """
    doc = _open(path)
    try:
        texts = [p.get_textpage().get_text_range() for p in doc]
    finally:
        doc.close()
    toc = parse_toc(texts)
    page_numbers = list(pages) if pages else list(range(1, len(texts) + 1))
    result = DigitizedDocument(path=str(path), n_pages=len(texts), toc=toc)
    page_info = {}
    done = 0
    if mode not in ("auto", "vector", "raster"):
        raise ValueError(f"unknown mode {mode!r}")
    ocr_info = not toc
    jobs = [
        (path, no, dpi, n_points, texts[no - 1], mode, ocr_info) for no in page_numbers
    ]
    if workers and workers > 1:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed

        ex = ProcessPoolExecutor(workers, mp_context=mp.get_context("spawn"))
        try:
            futures = [ex.submit(_process_page, *j) for j in jobs]
            for fut in as_completed(futures):
                no, info, plots = fut.result()
                page_info[no] = info
                result.plots += plots
                done += 1
                if progress:
                    progress(done, len(jobs))
        except BaseException:
            # a progress callback may raise to cancel: drop the queued pages
            ex.shutdown(wait=False, cancel_futures=True)
            raise
        ex.shutdown()
    else:
        for j in jobs:
            no, info, plots = _process_page(*j)
            page_info[no] = info
            result.plots += plots
            done += 1
            if progress:
                progress(done, len(jobs))
    result.plots.sort(key=lambda p: (p.page, p.index))
    result.cases = group_cases(result.plots, page_info, toc)
    return result


def _toc_name(page_no, toc):
    name = None
    for title, first in sorted(toc, key=lambda t: t[1]):
        if first <= page_no:
            name = title
    return name


def group_cases(plots, page_info, toc):
    """Group plots into operating cases and give every line its speed.

    The case of a page comes from the table of contents (entry whose first
    page precedes it), else from the page header, else from the printed
    suction conditions; consecutive pages with the same key form one case.
    """
    cases = []
    current = None
    readings = {}  # id(case) -> condition readings of its pages
    for page_no in sorted({p.page for p in plots if p.param}):
        info = page_info.get(page_no, {})
        cond = info.get("conditions", {})
        name = _toc_name(page_no, toc) or info.get("header")
        if name:
            key = name
        else:
            key = tuple(sorted((k, str(v)) for k, v in cond.items() if k in ("p", "T")))
        if current is None or current[0] != key:
            label = name or f"case {len(cases) + 1:02d}"
            case = DigitizedCase(name=label, conditions=cond)
            cases.append(case)
            current = (key, case)
        case = current[1]
        case.pages.append(page_no)
        found = info.get("condition_readings", [cond] if cond else [])
        if found:
            readings.setdefault(id(case), []).extend(found)
            case.conditions = vote_conditions(readings[id(case)])
        for plot in (p for p in plots if p.page == page_no and p.param):
            prev = case.plots.get(plot.param)
            if prev is None or (not prev.ok and plot.ok):
                case.plots[plot.param] = plot
    seen = {}
    for c in cases:
        seen[c.name] = seen.get(c.name, 0) + 1
    for name, n in seen.items():
        if n > 1:
            for k, c in enumerate([c for c in cases if c.name == name]):
                c.name = f"{name} {k + 1}"
    for c in cases:
        assign_speeds(c)
    return [c for c in cases if any(p.ok for p in c.plots.values())]


def _fan_law_subset(curves, speeds):
    """Subset of ``speeds`` (ascending) whose flows scale best with the lines."""
    from itertools import combinations

    ends = np.array([[c["flow"][0], c["flow"][-1]] for c in curves])
    best, best_err = None, np.inf
    for sub in combinations(speeds, len(curves)):
        ratio = np.log(ends / np.array(sub)[:, None])
        err = ratio.var(axis=0).sum()
        if err < best_err:
            best, best_err = list(sub), err
    return best


REFERENCE_PARAMS = (
    "head",
    "pressure_ratio",
    "disch_p",
    "disch_T",
    "power_shaft",
    "eff",
)


def assign_speeds(case):
    """Give each traced line its speed and trim lines to the reference range.

    Faster lines reach larger flows, so in a plot whose line count matches the
    legend the lines (ordered by choke-end flow) take the sorted speeds. Plots
    with missing lines are matched to the reference plot by end-point flows.
    Then every line is trimmed to the flow range of the same speed on the
    reference plot (the one with the surge line, normally head), because
    overlapping lines (efficiency near surge) cannot be told apart.
    """
    if any(p.labeled for p in case.plots.values()):
        assign_labeled_speeds(case)
        return
    speeds = legend_consensus(
        [r for p in case.plots.values() for r in p.legend_readings]
    )
    case.speeds = speeds
    if not speeds:
        for p in case.plots.values():
            p.warnings.append("no legend speeds for the case")
        return
    asc = sorted(speeds)
    ref = None
    for name in REFERENCE_PARAMS:
        p = case.plots.get(name)
        if p is not None and len(p.curves) == len(asc):
            ref = p
            break
    if ref is None:
        # no plot shows every legend speed (two lines drawn on top of each
        # other): pick the speeds that best follow the fan law on the plot
        # with most lines, where surge and choke flows scale with speed
        best = max(
            (case.plots.get(n) for n in REFERENCE_PARAMS if case.plots.get(n)),
            key=lambda p: len(p.curves),
            default=None,
        )
        if best is not None and 1 < len(best.curves) < len(asc):
            asc = _fan_law_subset(best.curves, asc)
            ref = best
            best.warnings.append(
                f"{len(best.curves)} lines for {len(speeds)} legend speeds, "
                f"speeds chosen by fan law: {asc}"
            )
    for p in case.plots.values():
        if p is ref or len(p.curves) == len(asc):
            for c, sp in zip(p.curves, asc):
                c["speed"] = sp
        elif ref is not None and p.curves:
            ref_ends = np.array([[c["flow"][0], c["flow"][-1]] for c in ref.curves])
            span = np.ptp(ref_ends) or 1.0
            taken = set()
            for c in p.curves:
                d = np.abs(ref_ends[:, 1] - c["flow"][-1]) / span
                for k in np.argsort(d):
                    if k not in taken:
                        taken.add(k)
                        c["speed"] = asc[k]
                        break
            p.warnings.append(
                f"{len(p.curves)} lines for {len(asc)} speeds, matched by end flow"
            )
        else:
            p.warnings.append(
                f"{len(p.curves)} lines for {len(asc)} speeds, not assigned"
            )
        p.curves = [c for c in p.curves if c["speed"] is not None]
        p.curves.sort(key=lambda c: c["speed"])
    if ref is None:
        return
    apply_physics(case)


def assign_labeled_speeds(case):
    """Speeds of a case whose lines carry their own labels (vector sheets).

    Percent labels are converted with the 100 % speed of the sheet. Lines left
    without a label (and plots read from a legend) take the free speed whose
    surge/choke flows, on the labelled plots, are closest to their ends.
    """
    n100 = case.conditions.get("speed")
    for p in case.plots.values():
        for c in p.curves:
            label = c.get("label") or ""
            if n100 and label and not label.endswith("%") and float(label) <= 150:
                label = c["label"] = label + "%"  # no shaft runs at 150 RPM
            if label.endswith("%"):
                if n100:
                    c["speed"] = round(float(label[:-1]) / 100 * n100, 1)
                elif (
                    "100 % speed not found: percent labels not converted"
                    not in p.warnings
                ):
                    p.warnings.append(
                        "100 % speed not found: percent labels not converted"
                    )
    ends = {}
    for p in case.plots.values():
        for c in p.curves:
            if c["speed"] is not None:
                ends.setdefault(c["speed"], []).append((min(c["flow"]), max(c["flow"])))
    ranges = {sp: np.median(np.array(e), axis=0) for sp, e in ends.items()}
    case.speeds = sorted(ranges, reverse=True)
    for p in case.plots.values():
        free = [sp for sp in case.speeds if sp not in {c["speed"] for c in p.curves}]
        missing = [c for c in p.curves if c["speed"] is None]
        span = np.ptp(np.array(list(ranges.values()))) if ranges else 1.0
        for c in sorted(missing, key=lambda c: -max(c["flow"])):
            if not free:
                break
            lo, hi = min(c["flow"]), max(c["flow"])
            best = min(
                free, key=lambda sp: abs(ranges[sp][0] - lo) + abs(ranges[sp][1] - hi)
            )
            if (abs(ranges[best][0] - lo) + abs(ranges[best][1] - hi)) / (
                span or 1
            ) < 0.1:
                c["speed"] = best
                free.remove(best)
        unnamed = sum(c["speed"] is None for c in p.curves)
        if unnamed:
            p.warnings.append(f"{unnamed} lines without a speed, dropped")
        p.curves = sorted(
            (c for c in p.curves if c["speed"] is not None), key=lambda c: c["speed"]
        )
        if p.curves and not p.labeled:
            p.notes.append("speeds matched to the labelled plots by flow range")
    if ranges:
        apply_physics(case)


# plots drawn with the surge line: their line ends are the surge and choke flows
RANGE_PARAMS = ("head", "pressure_ratio", "disch_p", "disch_T")
# lines that rise with speed at a given flow and never cross
ORDERED_PARAMS = (
    "head",
    "pressure_ratio",
    "disch_p",
    "disch_T",
    "power_shaft",
    "power",
)


def _extend(flow, value, lo, hi, max_gap):
    """Trim a line to [lo, hi] and extend short gaps along the local slope."""
    f, v = np.asarray(flow, float), np.asarray(value, float)
    m = (f >= lo) & (f <= hi)
    if m.sum() >= 3:
        f, v = f[m], v[m]
    span = hi - lo
    added = False
    for end in ("lo", "hi"):
        gap = (f[0] - lo) if end == "lo" else (hi - f[-1])
        if gap <= 0.002 * span or gap > max_gap * span:
            continue
        # local slope from the nearest 6 % of the range: a short, straight
        # extension is safer than a curved one near steep ends
        near = (f <= f[0] + 0.06 * span) if end == "lo" else (f >= f[-1] - 0.06 * span)
        if near.sum() < 2:
            near = np.zeros_like(f, bool)
            near[:2] = end == "lo"
            near[-2:] = end == "hi"
        coef = np.polyfit(f[near], v[near], 1)
        new_f = (
            np.linspace(lo, f[0], 4)[:-1]
            if end == "lo"
            else np.linspace(f[-1], hi, 4)[1:]
        )
        new_v = np.polyval(coef, new_f)
        if end == "lo":
            f, v = np.concatenate([new_f, f]), np.concatenate([new_v, v])
        else:
            f, v = np.concatenate([f, new_f]), np.concatenate([v, new_v])
        added = True
    return f, v, added


def apply_physics(case, max_gap=0.08):
    """Use compressor physics to check and complete the traced lines.

    1. Same speed, same flow range: a speed line runs from its surge to its
       choke flow on every plot of a case. The range is the median of the line
       ends over the plots drawn with the surge line; other plots (efficiency,
       whose lines overlap near surge) are trimmed to it, and gaps up to
       ``max_gap`` of the range are closed by a smooth extrapolation.
    2. Fan law: surge and choke flows scale with speed. Lines whose ends stray
       from the family's Q/N by more than 5 % are flagged.
    3. Ordering: head, pressure ratio, discharge pressure and temperature and
       power rise with speed at a given flow, so lines of one plot never cross.
    """
    ranges = {}
    for sp in case.speeds:
        ends = [
            (min(c["flow"]), max(c["flow"]))
            for name in RANGE_PARAMS
            if name in case.plots
            for c in case.plots[name].curves
            if c["speed"] == sp
        ]
        if ends:
            ranges[sp] = tuple(np.median(np.array(ends), axis=0))
    case.flow_ranges = ranges
    # re-select lines whose ends miss their speed's surge/choke flows: at a
    # crossing the tracer may follow the wrong branch, while another stroke
    # (traced from the other end) has the right ends
    for name, p in case.plots.items():
        if name in RANGE_PARAMS or not p.candidates or p.source == "vector":
            continue
        swapped = []
        used = set()
        for c in sorted(p.curves, key=lambda c: -c["speed"]):
            if c["speed"] not in ranges:
                continue
            lo, hi = ranges[c["speed"]]
            span = hi - lo
            if span <= 0:
                continue

            def miss(f):
                return (abs(min(f) - lo) + abs(max(f) - hi)) / span

            current = miss(c["flow"])
            best = min(
                (k for k in range(len(p.candidates)) if k not in used),
                key=lambda k: (
                    round(miss(p.candidates[k]["flow"]), 2),
                    p.candidates[k]["cost"],
                ),
                default=None,
            )
            if best is None:
                continue
            cand = p.candidates[best]
            if miss(cand["flow"]) < min(0.05, current - 0.02):
                c["flow"], c["value"] = cand["flow"], cand["value"]
                used.add(best)
                swapped.append(int(c["speed"]))
        if swapped:
            p.notes.append(f"lines re-traced to match the surge/choke flows: {swapped}")
    for name, p in case.plots.items():
        if p.source == "vector":
            continue  # exact lines: nothing to re-trace or extend
        extended = []
        for c in p.curves:
            if c["speed"] not in ranges:
                continue
            lo, hi = ranges[c["speed"]]
            f, v, added = _extend(c["flow"], c["value"], lo, hi, max_gap)
            c["flow"], c["value"] = f, v
            if added:
                extended.append(int(c["speed"]))
        if extended:
            p.notes.append(f"lines extended to the surge/choke range: {extended}")
    # physical bounds: catch a misread axis (tick labels losing a digit
    # still form a valid-looking scale)
    cond = case.conditions
    bounds = {"head": (0, None), "pressure_ratio": (1, None), "power_shaft": (0, None)}
    if "p" in cond and cond["p"][1] == "bar":
        bounds["disch_p"] = (cond["p"][0], None)
    if "T" in cond and cond["T"][1] == "degC":
        bounds["disch_T"] = (cond["T"][0], None)
    for name, p in case.plots.items():
        if not p.curves:
            continue
        vals = np.concatenate([np.asarray(c["value"], float) for c in p.curves])
        if name == "eff":
            frac = vals / 100 if p.units == "percent" else vals
            lo_b, hi_b = 0.3, 1.0
            bad = np.mean((frac < lo_b) | (frac > hi_b))
        else:
            lo_b, hi_b = bounds.get(name, (None, None))
            bad = np.mean(
                ((vals < lo_b) if lo_b is not None else False)
                | ((vals > hi_b) if hi_b is not None else False)
            )
        if bad > 0.05:
            msg = (
                f"{name}: {100 * bad:.0f} % of the points are physically "
                "impossible (axis misread?)"
            )
            p.warnings.append(msg)
            case.warnings.append(msg)
    # fan law on the line ends (a check of inferred speeds; printed line
    # labels need none, and tested maps do not follow it closely)
    labeled = all(p.labeled for p in case.plots.values())
    if len(ranges) >= 3 and not labeled:
        sp = np.array(sorted(ranges))
        q = np.array([ranges[k] for k in sp])
        for j, label in ((0, "surge"), (1, "choke")):
            ratio = q[:, j] / sp
            dev = np.abs(ratio / np.median(ratio) - 1)
            bad = sp[dev > 0.05]
            if len(bad):
                case.warnings.append(
                    f"{label} flow off the fan law (Q/N > 5 % from the family) at "
                    f"{[int(b) for b in bad]} RPM: check the speed assignment"
                )
    check_reference(case)
    # speed ordering (no crossing lines)
    for name in ORDERED_PARAMS:
        p = case.plots.get(name)
        if p is None or len(p.curves) < 2:
            continue
        cs = sorted(p.curves, key=lambda c: c["speed"])
        for a, b in zip(cs, cs[1:]):
            if b["speed"] < 1.01 * a["speed"]:
                continue  # near-equal speeds: lines drawn on top of each other
            lo = max(min(a["flow"]), min(b["flow"]))
            hi = min(max(a["flow"]), max(b["flow"]))
            if hi <= lo:
                continue
            grid = np.linspace(lo, hi, 50)
            ya = np.interp(grid, *_sorted_xy(a))
            yb = np.interp(grid, *_sorted_xy(b))
            span = np.ptp(np.concatenate([a["value"], b["value"]])) or 1.0
            if np.mean(yb < ya - 0.005 * span) > 0.2:
                p.warnings.append(
                    f"lines {int(a['speed'])} and {int(b['speed'])} RPM cross: "
                    "speed assignment or tracing is doubtful"
                )


# plots whose value rises with speed at a given flow: a point on them has one
# interpolated speed
SPEED_MONOTONIC = (
    "head",
    "pressure_ratio",
    "disch_p",
    "disch_T",
    "power_shaft",
    "power",
)


def _speed_at(plot, flow, value):
    """Speed of the point (flow, value) interpolated between the lines."""
    pts = []
    for c in plot.curves:
        if c["speed"] is None:
            continue
        f, v = _sorted_xy(c)
        span = f[-1] - f[0]
        if not f[0] - 0.03 * span <= flow <= f[-1] + 0.03 * span:
            continue
        pts.append((float(np.interp(flow, f, v)), c["speed"]))
    pts.sort()
    for (v0, n0), (v1, n1) in zip(pts, pts[1:]):
        if v0 <= value <= v1 and v1 > v0:
            return n0 + (value - v0) / (v1 - v0) * (n1 - n0)
    return None


def check_reference(case):
    """Check the rated point printed on the plots against the digitized lines.

    The point is not necessarily on a drawn line, but it is one operating
    point: the speed interpolated between the lines at its flow must be the
    same on every plot whose value rises with speed (head, discharge
    pressure, power...). Disagreement means a misread axis or a wrong line.
    """
    found = {}
    for name, p in case.plots.items():
        if p.reference and name in SPEED_MONOTONIC:
            n = _speed_at(p, *p.reference)
            if n is not None:
                found[name] = n
    if not found:
        return
    med = float(np.median(list(found.values())))
    spread = max(abs(n / med - 1) for n in found.values()) * 100
    detail = ", ".join(f"{k} {v:.0f}" for k, v in found.items())
    msg = f"rated point at {med:.0f} RPM interpolated between the lines ({detail})"
    if len(found) >= 2 and spread > 1.0:
        case.warnings.append(f"{msg}: plots disagree by {spread:.1f} %")
    for name in found:
        case.plots[name].notes.append(msg)


def _sorted_xy(c):
    f, v = np.asarray(c["flow"], float), np.asarray(c["value"], float)
    o = np.argsort(f)
    return f[o], v[o]
