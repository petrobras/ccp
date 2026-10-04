"""Axis calibration from OCR'd tick labels, refined by snapping to grid lines."""

import itertools
import re
from dataclasses import dataclass, field

import numpy as np

from ._ocr import ocr_text, ocr_words, parse_number

__all__ = [
    "AxisCalibration",
    "calibrate_axis",
    "grid_lines",
    "classify_y_title",
    "classify_x_title",
    "read_y_title",
    "read_x_title",
]


@dataclass
class AxisCalibration:
    """Linear map ``pixel = offset + slope * value``."""

    offset: float
    slope: float
    ticks: list = field(default_factory=list)  # (value, pixel) used in the fit
    residual: float = 0.0  # RMS of the fit in pixels

    def to_value(self, pixel):
        return (np.asarray(pixel, dtype=float) - self.offset) / self.slope

    def to_pixel(self, value):
        return self.offset + self.slope * np.asarray(value, dtype=float)


def grid_lines(dark, box, axis, min_fraction=0.15):
    """Pixel positions of grid lines inside ``box``.

    ``axis="x"`` returns columns (vertical grid lines), ``"y"`` rows. Dashed and
    dotted grids cover a large fraction of the plot height/width; curves do not.
    """
    inner = dark[box.y0 + 3 : box.y1 - 2, box.x0 + 3 : box.x1 - 2]
    profile = inner.mean(axis=0 if axis == "x" else 1)
    offset = (box.x0 if axis == "x" else box.y0) + 3
    idx = np.flatnonzero(profile > min_fraction)
    lines = []
    for _, grp in itertools.groupby(enumerate(idx), lambda t: t[1] - t[0]):
        g = np.array([v for _, v in grp])
        w = profile[g]
        lines.append(offset + float((g * w).sum() / w.sum()))
    return lines


def _fit(points, tol):
    """RANSAC over point pairs, then least squares on the inliers."""
    best = None
    for (v1, p1), (v2, p2) in itertools.combinations(points, 2):
        if v1 == v2:
            continue
        slope = (p2 - p1) / (v2 - v1)
        offset = p1 - slope * v1
        res = np.array([p - (offset + slope * v) for v, p in points])
        inl = np.abs(res) < tol
        score = (inl.sum(), -np.abs(res[inl]).sum())
        if best is None or score > best[0]:
            best = (score, inl)
    if best is None or best[0][0] < 2:
        return None
    inl = best[1]
    v = np.array([pt[0] for pt in points])[inl]
    p = np.array([pt[1] for pt in points])[inl]
    slope, offset = np.polyfit(v, p, 1)
    # one reading per label position: keep the one closest to the fit
    res = np.abs(p - (offset + slope * v))
    keep = {}
    for k in np.argsort(res):
        keep.setdefault(round(p[k]), k)
    idx = sorted(keep.values())
    v, p = v[idx], p[idx]
    if len(set(v.tolist())) < 2:
        return None
    slope, offset = np.polyfit(v, p, 1)
    res = p - (offset + slope * v)
    return AxisCalibration(
        float(offset),
        float(slope),
        list(zip(v.tolist(), p.tolist())),
        float(np.sqrt(np.mean(res**2))),
    )


def _decimals(v):
    t = f"{v:.10g}"
    return len(t.split(".")[1]) if "." in t and "e" not in t else 0


def _equally_spaced(points):
    """Drop OCR misreads: keep values that sit on the dominant tick step.

    Labels may be rounded (a 0.0125 step printed as 0.600, 0.613, 0.625...):
    a value counts as on the step when it is within its own rounding of it,
    and rounded labels are replaced by the exact values of the fitted step.
    """
    vals = sorted({v for v, _ in points})
    if len(vals) < 3:
        return points
    step = np.median(np.diff(vals))
    if step <= 0:
        return points
    unit = 10.0 ** -max(_decimals(v) for v in vals)

    def fit_step(step):
        tol = max(0.02, 0.6 * unit / step)

        def on_step(v, base):
            k = (v - base) / step
            return abs(k - round(k)) < tol

        base = max(vals, key=lambda b: sum(on_step(v, b) for v in vals))
        return [v for v in vals if on_step(v, base)], base, tol

    # the median difference, or (rounded labels drift from it) the step over
    # the whole range; an outlier misread spoils the latter, so the one that
    # keeps more labels wins
    best = fit_step(step) + (step,)
    n = round((vals[-1] - vals[0]) / step)
    if n > 0:
        alt = (vals[-1] - vals[0]) / n
        cand = fit_step(alt) + (alt,)
        if len(cand[0]) > len(best[0]):
            best = cand
    ok, base, tol, step = best
    if len(ok) >= 3 and tol > 0.02:
        # refine over the good labels only
        n = round((ok[-1] - ok[0]) / step)
        if n > 0:
            ok2, base2, tol2 = fit_step((ok[-1] - ok[0]) / n)
            if len(ok2) >= len(ok):
                ok, base, tol, step = ok2, base2, tol2, (ok[-1] - ok[0]) / n
    out = [pt for pt in points if pt[0] in set(ok)]
    if len(ok) >= 3 and tol > 0.02:
        k = np.array([round((v - base) / step) for v in ok])
        b, a = np.polyfit(k, ok, 1)
        # a printed step is a round number: snap to it when within rounding
        mag = 10.0 ** np.floor(np.log10(abs(b)))
        nice = min(
            (m * mag for m in (1, 1.25, 2, 2.5, 5, 10)), key=lambda m: abs(m - b)
        )
        if abs(nice - b) * max(k.max(), 1) < unit:
            b = nice
            # the offset that rounds to every label; prefer one printed exactly
            offs = np.array(ok) - b * k
            lo, hi = offs.max() - 0.5 * unit, offs.min() + 0.5 * unit
            exact = [o for o in offs if lo - 1e-12 <= o <= hi + 1e-12]
            a = (
                min(exact, key=lambda o: _decimals(round(o, 10)))
                if exact
                else offs.mean()
            )
        exact = {v: float(a + b * kk) for v, kk in zip(ok, k)}
        if all(abs(exact[v] - v) <= 0.6 * unit for v in ok):
            out = [(exact[v], p) for v, p in out]
    return out


def _label_blobs(mask, gap):
    """Group dark pixels of a label strip into text blobs (one per tick label)."""
    from ._image import components

    _, slices = components(mask)
    boxes = [
        [sl[1].start, sl[0].start, sl[1].stop, sl[0].stop]
        for sl in slices
        if sl is not None
    ]
    merged = True
    while merged:
        merged = False
        out = []
        for b in boxes:
            for o in out:
                if (
                    b[0] <= o[2] + gap
                    and o[0] <= b[2] + gap
                    and b[1] <= o[3] + gap / 3
                    and o[1] <= b[3] + gap / 3
                ):
                    o[0], o[1] = min(o[0], b[0]), min(o[1], b[1])
                    o[2], o[3] = max(o[2], b[2]), max(o[3], b[3])
                    merged = True
                    break
            else:
                out.append(list(b))
        boxes = out
    return boxes


def ocr_blobs(gray_img, blobs, pad=12):
    """OCR many small blobs by stacking them vertically into one sheet.

    The sheet is read with two preprocessing variants (upscale + blur, and
    upscale + binarize) that fail on different glyphs of jagged low-dpi fonts;
    returns, per blob, the list of distinct strings read (possibly empty).
    """
    if not blobs:
        return []
    crops = [gray_img[y0:y1, x0:x1] for x0, y0, x1, y1 in blobs]
    hmax = max(c.shape[0] for c in crops)
    width = max(c.shape[1] for c in crops) + 2 * pad
    rows = []
    centers = []
    y = 0
    for c in crops:
        canvas = np.full((hmax + 2 * pad, width), 255, np.uint8)
        canvas[pad : pad + c.shape[0], pad : pad + c.shape[1]] = c
        rows.append(canvas)
        centers.append(y + pad + c.shape[0] / 2)
        y += canvas.shape[0]
    sheet = np.vstack(rows)
    row_h = hmax + 2 * pad
    variants = [dict(scale=2.0, blur=1.0), dict(scale=3.0, binarize=160)]
    texts = [[] for _ in blobs]
    for kw in variants:
        read = [""] * len(blobs)
        for w in ocr_words(sheet, psm=6, whitelist="0123456789.-", **kw):
            i = int(w.cy // row_h)
            if 0 <= i < len(blobs):
                read[i] += w.text
        for i, t in enumerate(read):
            if t and t not in texts[i]:
                texts[i].append(t)
    return texts


_RAW_CACHE = {}


def _tick_points(img, box, axis, s, band_gap=16):
    """(value, pixel) pairs for the tick labels of one axis."""
    points = []
    for b, reads, pos in _raw_ticks(img, box, axis, s, band_gap):
        for t in reads:
            v = parse_number(t)
            if v is not None:
                points.append((v, pos))
    return points


def _raw_ticks(img, box, axis, s, band_gap=16):
    """[(blob, readings, pixel position)] for the labels of one axis (cached)."""
    key = (id(img), box, axis, s, band_gap)
    if key in _RAW_CACHE:
        return _RAW_CACHE[key]
    if len(_RAW_CACHE) > 16:
        _RAW_CACHE.clear()
    from ._image import dark_mask, gray

    if axis == "x":
        y0, y1 = box.y1 + int(4 * s), box.y1 + int(60 * s)
        x0, x1 = max(box.x0 - int(120 * s), 0), box.x1 + int(120 * s)
    else:
        y0, y1 = max(box.y0 - int(30 * s), 0), box.y1 + int(30 * s)
        x0, x1 = max(box.x0 - int(150 * s), 0), box.x0 - int(4 * s)
    crop = img[y0:y1, x0:x1]
    mask = dark_mask(crop, threshold=200)
    if axis == "y":
        # keep only the band of ink touching the axis side: the rotated axis
        # title sits further left, separated by a blank column gap
        # long vertical runs are the axis line's antialiasing, not labels
        mask[:, mask.mean(axis=0) > 0.5] = False
        # and flat fragments (frame corners, tick marks, decimal points) do
        # not define the band
        from ._image import components

        glyphs = mask.copy()
        labels, slices = components(glyphs)
        for i, sl in enumerate(slices, start=1):
            if sl is not None and (sl[0].stop - sl[0].start) < 6 * s:
                glyphs[sl][labels[sl] == i] = False
        # a label column holds several labels; a stray glyph (x tick label
        # under the corner) only a few pixels
        ink = glyphs.sum(axis=0) >= max(3, 0.02 * glyphs.shape[0])
        # wide enough to keep a narrow leading "1" or "0." with its label,
        # narrow enough (second try) to drop a rotated title set close by
        gap_needed = int(band_gap * s)
        right = len(ink) - 1
        while right > 0 and not ink[right]:
            right -= 1
        left, blank = right, 0
        while left > 0 and blank < gap_needed:
            left -= 1
            blank = blank + 1 if not ink[left] else 0
        mask[:, : left + 1] = False
    blobs = _label_blobs(mask, gap=int(12 * s))
    char_h = 40 * s
    blobs = [
        b for b in blobs if 6 * s <= (b[3] - b[1]) <= char_h and (b[2] - b[0]) >= 3 * s
    ]
    # tick labels share one alignment (top edge for x, right edge for y);
    # keep the blobs on the most populated alignment, dropping stray glyphs
    # from the other axis or the titles
    if blobs:
        key = (lambda b: b[1]) if axis == "x" else (lambda b: b[2])
        tol = (12 if axis == "x" else 20) * s
        ref = max(blobs, key=lambda b: sum(abs(key(o) - key(b)) <= tol for o in blobs))
        blobs = [b for b in blobs if abs(key(b) - key(ref)) <= tol]
    g = np.clip(gray(crop), 0, 255).astype(np.uint8)
    texts = ocr_blobs(g, blobs)
    out = []
    for b, reads in zip(blobs, texts):
        pos = x0 + (b[0] + b[2]) / 2 if axis == "x" else y0 + (b[1] + b[3]) / 2
        out.append((b, reads, pos))
    _RAW_CACHE[key] = out
    return out


def calibrate_axis(img, dark, box, axis, scale_px):
    """Calibrate the x or y axis of ``box`` from its tick labels.

    ``scale_px`` is the rendering scale relative to 300 dpi, used to size the
    label search strips.
    """
    s = scale_px
    tol = 0.006 * (box.width if axis == "x" else box.height)
    cal = None
    for gap in (16, 6) if axis == "y" else (16,):
        points = _tick_points(img, box, axis, s, gap)
        points = _equally_spaced(list(dict.fromkeys(points)))
        c = _fit(points, tol)
        if c is not None and (
            axis == "x" and c.slope > 0 or axis == "y" and c.slope < 0
        ):
            if cal is None or (len(c.ticks), -c.residual) > (
                len(cal.ticks),
                -cal.residual,
            ):
                cal = c
    if cal is None:
        return None
    # snap ticks to grid lines (labels are centred on them) and refit
    lines = np.array(grid_lines(dark, box, axis))
    lines = np.concatenate(
        [lines, [box.x0, box.x1] if axis == "x" else [box.y0, box.y1]]
    )
    snapped = []
    for v, _ in cal.ticks:
        p = cal.to_pixel(v)
        j = np.argmin(np.abs(lines - p))
        if abs(lines[j] - p) < max(
            4 * s, 0.006 * (box.width if axis == "x" else box.height)
        ):
            snapped.append((v, float(lines[j])))
    if len(snapped) >= max(3, len(cal.ticks) - 1):
        refit = _fit(snapped, tol)
        if refit is not None and refit.residual < max(cal.residual, 0.5 * s):
            cal = refit
    if axis == "x" and cal.slope <= 0:
        return None
    if axis == "y" and cal.slope >= 0:
        return None
    return cal


# --------------------------------------------------------------------------- titles

_Y_PARAMS = [
    # (regex on the normalized title, parameter, default units)
    (r"EFFIC", "eff", None),
    (r"HEAD", "head", None),
    (r"PRESS\w*\s*RATIO|RATIO", "pressure_ratio", "dimensionless"),
    (r"(OUTLET|DISCH\w*)\s*TEMP|TEMPERAT", "disch_T", None),
    (r"(OUTLET|DISCH\w*)\s*PRESS|PRESSURE", "disch_p", None),
    (r"SHAFT\s*POWER|POWER", "power_shaft", None),
]

_UNITS = [
    (r"M\W*KGF\s*/\s*KG", "m*kgf/kg"),
    (r"KJ\s*/\s*K|KJKG", "kJ/kg"),
    (r"\bJ\s*/\s*KG", "J/kg"),
    (r"FT\W*LB", "ft*lbf/lb"),
    (r"FRACTION", "dimensionless"),
    (r"%", "percent"),
    (r"[BH]AR\W*A\b|BARA|\bBAR", "bar"),
    (r"KPA", "kPa"),
    (r"MPA", "MPa"),
    (r"PSIA|PSI", "psi"),
    (r"KW", "kW"),
    (r"MW\b", "MW"),
    (r"\bHP\b", "hp"),
    (r"°\s*C|DEG\s*C|\bC\b|\bºC", "degC"),
    (r"°\s*F|DEG\s*F|\bF\b", "degF"),
    (r"\bK\b", "degK"),
]


def _normalize(text):
    t = text.upper().replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    return t


def classify_y_title(text):
    """Return (parameter, units) parsed from a y-axis title, or (None, None)."""
    t = _normalize(text)
    param = None
    units = None
    for pat, name, default in _Y_PARAMS:
        if re.search(pat, t):
            param, units = name, default
            break
    if param is None:
        return None, None
    for pat, u in _UNITS:
        if re.search(pat, t):
            if param in ("eff",) and u not in ("dimensionless", "percent"):
                continue
            if param == "head" and u not in ("kJ/kg", "J/kg", "ft*lbf/lb", "m*kgf/kg"):
                continue
            if param == "disch_T" and u not in ("degC", "degF", "degK"):
                continue
            if param == "disch_p" and u not in ("bar", "kPa", "MPa", "psi"):
                continue
            if param == "power_shaft" and u not in ("kW", "MW", "hp"):
                continue
            units = u
            break
    return param, units


def classify_x_title(text):
    """Return the flow units of an x-axis title (default ``m³/h``)."""
    t = _normalize(text)
    if re.search(r"KG\s*/\s*H|KG/H", t):
        return "kg/h", "mass"
    if re.search(r"KG\s*/\s*S", t):
        return "kg/s", "mass"
    if re.search(r"M\W*[3³]\s*/\s*S\b|M[3³]/S", t):
        return "m³/s", "volume"
    if re.search(r"M\W*[3³]\s*/\s*MIN", t):
        return "m³/min", "volume"
    if re.search(r"ACFM|CFM", t):
        return "ft³/min", "volume"
    return "m³/h", "volume"


def read_y_title(img, box, scale_px):
    """OCR the rotated y-axis title to the left of the tick labels."""
    s = scale_px
    x0 = max(box.x0 - int(260 * s), 0)
    x1 = box.x0 - int(20 * s)
    crop = img[box.y0 : box.y1, x0:x1]
    best, best_score = "", (-1, -1)
    for k in (1, 3):  # text reads bottom-to-top (k=1) or top-to-bottom (k=3)
        rot = np.ascontiguousarray(np.rot90(crop, k=-k))
        text = ocr_text(rot, psm=6, scale=2.0 if s < 1.5 else 1.0)
        # upside-down text still yields letters: prefer the reading that
        # names a known quantity
        score = (classify_y_title(text)[0] is not None, sum(c.isalpha() for c in text))
        if score > best_score:
            best, best_score = text, score
        if score[0]:
            break
    return best


def read_x_title(img, box, scale_px):
    s = scale_px
    crop = img[box.y1 + int(25 * s) : box.y1 + int(90 * s), box.x0 : box.x1]
    return ocr_text(crop, psm=6, scale=2.0 if s < 1.5 else 1.0)
