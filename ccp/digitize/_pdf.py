"""PDF content layer: text with positions and vector paths, in page pixels.

Plots drawn as vector graphics (e.g. sheets exported by plotting software) carry
everything a digitizer needs without OCR: tick labels, axis titles and line
labels are text objects, and every speed line is a polyline. Both are mapped
to the pixel frame of the page rendered at ``dpi`` (y down), the frame used by
the raster pipeline, so plots from either source share one representation.
"""

import ctypes
import math
from dataclasses import dataclass

import numpy as np

__all__ = [
    "PageMap",
    "TextItem",
    "VectorPath",
    "page_words",
    "page_paths",
    "join_words",
]


class PageMap:
    """Affine map from PDF user space to the pixels of the rendered page.

    Built with ``FPDF_PageToDevice`` on a magnified virtual canvas (the call
    returns integers), so page rotation and box offsets are honoured exactly as
    when rendering.
    """

    _K = 64

    def __init__(self, page, width_px, height_px):
        import pypdfium2.raw as raw

        k = self._K
        pts = []
        for px, py in ((0.0, 0.0), (1000.0, 0.0), (0.0, 1000.0)):
            dx, dy = ctypes.c_int(), ctypes.c_int()
            raw.FPDF_PageToDevice(
                page.raw,
                0,
                0,
                int(width_px * k),
                int(height_px * k),
                0,
                px,
                py,
                ctypes.byref(dx),
                ctypes.byref(dy),
            )
            pts.append((dx.value / k, dy.value / k))
        (x0, y0), (x1, y1), (x2, y2) = pts
        self.m = np.array(
            [
                [(x1 - x0) / 1000, (x2 - x0) / 1000, x0],
                [(y1 - y0) / 1000, (y2 - y0) / 1000, y0],
            ]
        )
        self.scale = math.sqrt(abs(np.linalg.det(self.m[:, :2])))

    def __call__(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        m = self.m
        return m[0, 0] * x + m[0, 1] * y + m[0, 2], m[1, 0] * x + m[1, 1] * y + m[1, 2]


@dataclass
class TextItem:
    """A word (no spaces) or a joined phrase, with its pixel box.

    ``angle`` is the reading direction in degrees, counter-clockwise on the
    page: 0 for horizontal text, 90 for text read bottom to top.
    """

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    angle: float = 0.0
    color: tuple = (0, 0, 0)
    size: float = 0.0  # glyph height (px)
    source: str = "pdf"

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    @property
    def colored(self):
        r, g, b = self.color[:3]
        return max(r, g, b) - min(r, g, b) > 60

    def distance_to(self, x, y):
        """Distance (px) from a point to the box (0 inside)."""
        dx = max(self.x0 - x, 0, x - self.x1)
        dy = max(self.y0 - y, 0, y - self.y1)
        return math.hypot(dx, dy)


def _char_color(raw, tp, i):
    v = [ctypes.c_uint() for _ in range(4)]
    if raw.FPDFText_GetFillColor(tp, i, *(ctypes.byref(c) for c in v)):
        return tuple(c.value for c in v[:3])
    return (0, 0, 0)


def _composed_matrix(obj):
    """Object matrix composed with the matrices of its parent forms."""
    a, b, c, d, e, f = obj.get_matrix().get()
    parent = getattr(obj, "container", None)
    while parent is not None and hasattr(parent, "get_matrix"):
        pa, pb, pc, pd, pe, pf = parent.get_matrix().get()
        a, b, c, d, e, f = (
            a * pa + b * pc,
            a * pb + b * pd,
            c * pa + d * pc,
            c * pb + d * pd,
            e * pa + f * pc + pe,
            e * pb + f * pd + pf,
        )
        parent = getattr(parent, "container", None)
    return a, b, c, d, e, f


def _page_chars(page, pmap):
    """Characters in content order: ``dict(ch, box, origin, angle, color)``.

    pdfium drops a glyph from the text layer when it overlaps an identical
    previous glyph (its fake-bold heuristic), which hits steeply rotated
    labels drawn one glyph per text object: "10000" comes out as "1000". The
    text objects are still there, so an object left without characters gets
    the character of the object before it, moved to its own origin.
    """
    import pypdfium2.raw as raw

    tp = page.get_textpage()
    by_obj = {}
    for i in range(tp.count_chars()):
        obj = raw.FPDFText_GetTextObject(tp.raw, i)
        key = ctypes.cast(obj, ctypes.c_void_p).value
        by_obj.setdefault(key, []).append(i)

    def char(i):
        code = raw.FPDFText_GetUnicode(tp.raw, i)
        ch = chr(code) if code else ""
        if raw.FPDFText_IsGenerated(tp.raw, i):
            # pdfium guesses spaces from gaps (a dropped glyph leaves one);
            # the baseline geometry decides instead
            return "soft"
        if not ch.strip() or ch == "\ufffe":
            return None  # word break
        left, bottom, right, top = tp.get_charbox(i)
        xs, ys = pmap([left, right], [bottom, top])
        # the loose box spans the glyph advance, not just its ink
        left, bottom, right, top = tp.get_charbox(i, loose=True)
        lxs, lys = pmap([left, right], [bottom, top])
        ox, oy = ctypes.c_double(), ctypes.c_double()
        raw.FPDFText_GetCharOrigin(tp.raw, i, ctypes.byref(ox), ctypes.byref(oy))
        opx, opy = pmap(ox.value, oy.value)
        angle = math.degrees(raw.FPDFText_GetCharAngle(tp.raw, i))
        m = raw.FS_MATRIX()
        raw.FPDFText_GetMatrix(tp.raw, i, ctypes.byref(m))
        em = raw.FPDFText_GetFontSize(tp.raw, i) * math.sqrt(abs(m.a * m.d - m.b * m.c))
        return dict(
            em=em * pmap.scale,
            ch=ch,
            box=(float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))),
            loose=(float(min(lxs)), float(min(lys)), float(max(lxs)), float(max(lys))),
            origin=(float(opx), float(opy)),
            # pdfium angles run clockwise; keep counter-clockwise in (-180, 180]
            angle=(-angle + 180) % 360 - 180,
            color=_char_color(raw, tp.raw, i),
        )

    # glyphs dropped by pdfium, inserted after the last character of the
    # text object drawn before them
    extra = {}
    last = None  # last character index of the previous text object
    prev = None  # that character
    for obj in page.get_objects(filter=[raw.FPDF_PAGEOBJ_TEXT], max_depth=4):
        idx = by_obj.get(ctypes.cast(obj.raw, ctypes.c_void_p).value)
        if idx:
            last = idx[-1]
            prev = char(last)
            if not isinstance(prev, dict):
                prev = None
            continue
        left, bottom, right, top = obj.get_bounds()
        if prev is None or right - left <= 0 or top - bottom <= 0:
            prev = None  # no glyph drawn (empty or space-only object)
            continue
        *_, e, f = _composed_matrix(obj)
        ox, oy = (float(v) for v in pmap(e, f))
        dx, dy = ox - prev["origin"][0], oy - prev["origin"][1]
        size = max(prev["box"][2] - prev["box"][0], prev["box"][3] - prev["box"][1])
        if not 0 < math.hypot(dx, dy) < 2 * size:
            prev = None
            continue
        x0, y0, x1, y1 = prev["box"]
        lx0, ly0, lx1, ly1 = prev["loose"]
        prev = dict(
            prev,
            box=(x0 + dx, y0 + dy, x1 + dx, y1 + dy),
            loose=(lx0 + dx, ly0 + dy, lx1 + dx, ly1 + dy),
            origin=(ox, oy),
        )
        extra.setdefault(last, []).append(prev)
    out = []
    for i in range(tp.count_chars()):
        out.append(char(i))
        out += extra.get(i, [])
    return out


def _glyph_metrics(c):
    """Advance and height (px) of a glyph from its axis-aligned boxes.

    The boxes of a rotated glyph are the bounds of a rotated rectangle:
    ``W = a |cos| + l |sin|`` and ``H = a |sin| + l |cos|``; solved for the
    advance ``a`` (loose box) and the ink height (tight box) when the angle is
    not close to 45 degrees, else estimated from the em size.
    """
    t = math.radians(c["angle"])
    cs, sn = abs(math.cos(t)), abs(math.sin(t))
    det = cs * cs - sn * sn
    em = c.get("em") or 0.0

    def unrotate(box):
        w, h = box[2] - box[0], box[3] - box[1]
        return (w * cs - h * sn) / det, (h * cs - w * sn) / det

    if abs(det) > 0.5:
        adv, _ = unrotate(c["loose"])
        _, height = unrotate(c["box"])
    else:
        adv = 0.6 * em if em else max(c["loose"][2] - c["loose"][0], 1.0)
        height = 0.7 * em if em else adv
    if em <= 0:
        em = max(height / 0.7, 1e-6)
    return max(adv, 0.0), max(height, 0.1 * em), em


def page_words(page, pmap):
    """Words of the page text layer, one ``TextItem`` per run of glyphs.

    Glyphs are linked spatially, not in content order: each one is followed
    by the glyph whose origin sits one advance further along its baseline
    (same direction and colour). Some plotting tools write glyphs of neighbouring
    labels interleaved, one per text object, and rotate them freely; a word
    ends where the next glyph is a space or more away.
    """
    chars = [c for c in _page_chars(page, pmap) if isinstance(c, dict)]
    for c in chars:
        c["adv"], c["h"], c["em_px"] = _glyph_metrics(c)
    cell = max(np.median([c["em_px"] for c in chars]) * 2, 1.0) if chars else 1.0
    grid = {}
    for i, c in enumerate(chars):
        key = (int(c["origin"][0] // cell), int(c["origin"][1] // cell))
        grid.setdefault(key, []).append(i)
    succ = {}
    for i, c in enumerate(chars):
        t = math.radians(c["angle"])
        d = (math.cos(t), -math.sin(t))  # baseline direction, y down
        gx, gy = int(c["origin"][0] // cell), int(c["origin"][1] // cell)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), ()):
                    if j == i:
                        continue
                    o = chars[j]
                    if o["color"] != c["color"]:
                        continue
                    if abs((o["angle"] - c["angle"] + 180) % 360 - 180) > 10:
                        continue
                    vx = o["origin"][0] - c["origin"][0]
                    vy = o["origin"][1] - c["origin"][1]
                    along = vx * d[0] + vy * d[1]
                    across = abs(vx * d[1] - vy * d[0])
                    em = max(c["em_px"], o["em_px"])
                    if (
                        across > 0.25 * em
                        or not 0.1 * em < along < c["adv"] + 0.15 * em
                    ):
                        continue
                    # the next glyph is the nearest one ahead on the baseline
                    # (loose boxes of rotated glyphs overstate the advance)
                    score = along + 2 * across
                    if best is None or score < best[0]:
                        best = (score, j)
        if best is not None:
            succ[i] = best
    # a glyph follows at most one glyph: keep the best claim
    pred = {}
    for i, (score, j) in succ.items():
        if j not in pred or score < pred[j][0]:
            pred[j] = (score, i)
    nxt = {i: j for j, (_, i) in pred.items()}
    words = []
    for start in range(len(chars)):
        if start in pred:
            continue
        run, k = [], start
        while k is not None and len(run) < 500:
            run.append(chars[k])
            k = nxt.get(k)
        xs = [v for c in run for v in (c["box"][0], c["box"][2])]
        ys = [v for c in run for v in (c["box"][1], c["box"][3])]
        words.append(
            TextItem(
                "".join(c["ch"] for c in run),
                min(xs),
                min(ys),
                max(xs),
                max(ys),
                run[0]["angle"],
                run[0]["color"],
                float(np.median([c["h"] for c in run])),
            )
        )
    return words


def join_words(words, max_gap=1.2):
    """Join words of one line of text (same direction, aligned) into phrases.

    ``max_gap`` is the largest blank between words, in glyph heights.
    """

    def direction(t):
        a = math.radians(t.angle)
        return math.cos(a), -math.sin(a)  # y down

    def along(t):
        d = direction(t)
        return t.cx * d[0] + t.cy * d[1]

    def half(t, d):
        return abs((t.x1 - t.x0) * d[0]) / 2 + abs((t.y1 - t.y0) * d[1]) / 2

    lines = []
    for w in sorted(words, key=lambda t: (round(t.angle / 15), along(t))):
        d = direction(w)
        for line in lines:
            last = line[-1]
            if abs((w.angle - last.angle + 180) % 360 - 180) > 10:
                continue
            vx, vy = w.cx - last.cx, w.cy - last.cy
            across = abs(vx * d[1] - vy * d[0])
            size = max(w.size, last.size, 1e-6)
            gap = vx * d[0] + vy * d[1] - half(w, d) - half(last, d)
            if across < 0.5 * size and -0.5 * size < gap < max_gap * size:
                line.append(w)
                break
        else:
            lines.append([w])
    out = []
    for line in lines:
        out.append(
            TextItem(
                " ".join(t.text for t in line),
                min(t.x0 for t in line),
                min(t.y0 for t in line),
                max(t.x1 for t in line),
                max(t.y1 for t in line),
                line[0].angle,
                line[0].color,
                float(np.median([t.size for t in line])),
                line[0].source,
            )
        )
    return out


@dataclass
class VectorPath:
    """One path object: its subpaths as (N, 2) pixel arrays."""

    subpaths: list
    stroke: tuple = None  # RGB when stroked
    fill: tuple = None  # RGB when filled
    width: float = 0.0  # stroke width (px)
    order: int = 0  # position in the content stream

    @property
    def points(self):
        return np.vstack(self.subpaths) if self.subpaths else np.zeros((0, 2))


def _bezier(p0, p1, p2, p3, n=8):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )


def page_paths(page, pmap):
    """Every path object of the page (forms included), in pixels.

    Curves (Bezier segments) are flattened. Only the geometry and the paint
    are kept; dash patterns are ignored (a dashed line is still one line).
    """
    import pypdfium2.raw as raw

    out = []
    for order, obj in enumerate(page.get_objects(max_depth=4)):
        if obj.type != raw.FPDF_PAGEOBJ_PATH:
            continue
        a, b, c, d, e, f = _composed_matrix(obj)
        fill_mode, stroke = ctypes.c_int(), ctypes.c_int()
        raw.FPDFPath_GetDrawMode(obj.raw, ctypes.byref(fill_mode), ctypes.byref(stroke))
        width = ctypes.c_float()
        raw.FPDFPageObj_GetStrokeWidth(obj.raw, ctypes.byref(width))
        subpaths, cur, pending = [], [], []
        for i in range(raw.FPDFPath_CountSegments(obj.raw)):
            seg = raw.FPDFPath_GetPathSegment(obj.raw, i)
            x, y = ctypes.c_float(), ctypes.c_float()
            raw.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y))
            ux, uy = a * x.value + c * y.value + e, b * x.value + d * y.value + f
            kind = raw.FPDFPathSegment_GetType(seg)
            if kind == raw.FPDF_SEGMENT_MOVETO:
                if len(cur) > 1:
                    subpaths.append(cur)
                cur, pending = [(ux, uy)], []
            elif kind == raw.FPDF_SEGMENT_BEZIERTO:
                pending.append((ux, uy))
                if len(pending) == 3 and cur:
                    pts = _bezier(np.array(cur[-1]), *map(np.array, pending))
                    cur += [tuple(p) for p in pts]
                    pending = []
            else:
                cur.append((ux, uy))
            if raw.FPDFPathSegment_GetClose(seg) and cur:
                cur.append(cur[0])
        if len(cur) > 1:
            subpaths.append(cur)
        if not subpaths:
            continue
        px = []
        for sp in subpaths:
            arr = np.asarray(sp, float)
            x, y = pmap(arr[:, 0], arr[:, 1])
            px.append(np.column_stack([x, y]))
        rgba = [ctypes.c_uint() for _ in range(4)]
        stroke_rgb = fill_rgb = None
        if stroke.value and raw.FPDFPageObj_GetStrokeColor(
            obj.raw, *(ctypes.byref(v) for v in rgba)
        ):
            stroke_rgb = tuple(v.value for v in rgba[:3])
        if fill_mode.value and raw.FPDFPageObj_GetFillColor(
            obj.raw, *(ctypes.byref(v) for v in rgba)
        ):
            fill_rgb = tuple(v.value for v in rgba[:3])
        scale = math.sqrt(abs(a * d - b * c)) * pmap.scale
        out.append(VectorPath(px, stroke_rgb, fill_rgb, width.value * scale, order))
    return out


def text_rows(words):
    """Page text rebuilt row by row from horizontal words (top to bottom).

    Table cells on one baseline end up on one line ("Ts 30 C Ps 1000 kPa"),
    which is what the condition parsers expect.
    """
    rows = []
    for w in sorted((w for w in words if abs(w.angle) < 10), key=lambda w: w.cy):
        for row in rows:
            if abs(row["cy"] - w.cy) < 0.5 * max(w.size, row["size"]):
                row["words"].append(w)
                break
        else:
            rows.append({"cy": w.cy, "size": w.size, "words": [w]})
    lines = []
    for row in rows:
        ws = sorted(row["words"], key=lambda w: w.x0)
        lines.append(" ".join(w.text for w in ws))
    return "\n".join(lines)
