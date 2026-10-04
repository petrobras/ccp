"""Vector plots: frames, axes, speed lines and labels read from the PDF itself.

When a curve sheet is drawn with vector graphics and real text (spreadsheet
or plotting-tool exports), nothing has to be guessed
from pixels: the frame and grid are line segments, the tick labels and the
axis titles are text, each speed line is a polyline and its speed is printed
next to one of its ends. This module turns that content into the same
``DigitizedPlot`` the raster pipeline produces, so case grouping, physics
checks, exports and the editor work unchanged.

The steps mirror the raster ones and keep their conventions (page pixels at
``dpi``, y down):

- frames: pairs of long verticals joined by a horizontal at the bottom or top;
  a solid major grid splits a plot into cells, so cells sharing their height
  and edges are merged back into one frame;
- axes: numeric words under the frame (x) and left of it (y), fitted with the
  raster RANSAC fit and snapped to the vector grid lines;
- titles: the rotated phrase left of the y labels, the phrase under the x
  labels, and the plot title above the frame;
- lines: polylines inside the frame chained in drawing order (filled outlines
  of thick lines give their centreline); axis-aligned ones (grid,
  reference-point guides), markers and short ones are dropped, and polylines
  joining the other lines (surge, choke and control lines) are kept apart as
  envelopes unless a speed label names them;
- speeds: a label printed at a line end names that line, at the same end for
  every line of a plot: a speed, a percent of the 100 % speed, or a letter of
  a legend printed on the page (``A=10000``); otherwise a legend inside the
  plot (``11000 RPM``) gives the speeds and the case-level assignment orders
  them by choke flow.
"""

import math
import re

import numpy as np

from ._axes import (
    _equally_spaced,
    _fit,
    classify_x_title,
    classify_y_title,
)
from ._ocr import parse_number
from ._pdf import join_words

__all__ = ["find_vector_frames", "vector_plots"]


# --------------------------------------------------------------------- frames


def _axis_lines(paths, min_h, min_v, tol=0.8):
    """Long horizontal and vertical segments, merged when collinear.

    Returns ``(horizontals, verticals)`` as lists of ``(pos, start, end)``.
    Filled thin rectangles (lines drawn as fills) give two close parallel
    edges that merge into one line.
    """
    hs, vs = [], []
    for p in paths:
        for sp in p.subpaths:
            for (x0, y0), (x1, y1) in zip(sp[:-1], sp[1:]):
                dx, dy = x1 - x0, y1 - y0
                if abs(dy) <= tol and abs(dx) >= 0.02 * min_h:
                    hs.append(((y0 + y1) / 2, min(x0, x1), max(x0, x1)))
                elif abs(dx) <= tol and abs(dy) >= 0.02 * min_v:
                    vs.append(((x0 + x1) / 2, min(y0, y1), max(y0, y1)))

    def merge(segs, min_len, gap):
        segs.sort()
        out = []
        for pos, a, b in segs:
            for s in out:
                if abs(pos - s[0]) <= 4 and a <= s[2] + gap and b >= s[1] - gap:
                    s[1], s[2] = min(s[1], a), max(s[2], b)
                    break
            else:
                out.append([pos, a, b])
        return [tuple(s) for s in out if s[2] - s[1] >= min_len]

    return merge(hs, min_h, 15), merge(vs, min_v, 15)


def find_vector_frames(paths, width, height, min_w=0.15, min_h=0.06):
    """Plot frames ``(x0, y0, x1, y1)`` from the vector line segments."""
    hs, vs = _axis_lines(paths, min_w * width, min_h * height)
    cells = []
    for i, (xa, ya0, ya1) in enumerate(vs):
        for xb, yb0, yb1 in vs[i + 1 :]:
            if xb - xa < 0.02 * width:
                continue
            if abs(ya0 - yb0) > 6 or abs(ya1 - yb1) > 6:
                continue
            top, bottom = min(ya0, yb0), max(ya1, yb1)
            if any(
                (abs(y - bottom) < 6 or abs(y - top) < 6)
                and a <= xa + 6
                and b >= xb - 6
                for y, a, b in hs
            ):
                cells.append((xa, top, xb, bottom))
    # a solid major grid makes cells: merge cells of equal height that share
    # vertical edges back into the frame
    cells = sorted(set(cells))
    merged = []
    for c in cells:
        for m in merged:
            if (
                abs(c[1] - m[1]) < 6
                and abs(c[3] - m[3]) < 6
                and c[0] <= m[2] + 3
                and c[2] >= m[0] - 3
            ):
                m[0], m[2] = min(m[0], c[0]), max(m[2], c[2])
                break
        else:
            merged.append(list(c))
    boxes = [tuple(m) for m in merged if m[2] - m[0] >= min_w * width]
    # the page border and title-block cells are boxes too: the caller keeps
    # the ones with tick labels along their axes
    return sorted(boxes, key=lambda b: (b[1], b[0]))


def _encloses(b, o, tol=3):
    return (
        b is not o
        and b[0] - tol <= o[0]
        and b[1] - tol <= o[1]
        and o[2] <= b[2] + tol
        and o[3] <= b[3] + tol
    )


# --------------------------------------------------------------------- axes


def _ticks(words, box, axis, s):
    """``(value, pixel, word)`` for the numeric labels of one axis."""
    x0, y0, x1, y1 = box
    out = []
    for w in words:
        if w.colored:
            continue  # reference-point values are printed in colour
        v = parse_number(w.text)
        if v is None:
            continue
        if axis == "x":
            if y1 < w.cy < y1 + 130 * s and x0 - 30 * s < w.cx < x1 + 30 * s:
                out.append((v, w.cx, w))
        else:
            if x0 - 200 * s < w.cx < x0 and y0 - 20 * s < w.cy < y1 + 20 * s:
                out.append((v, w.cy, w))
    # labels of one axis share a row (x) or a right edge (y)
    if len(out) > 2:
        key = (lambda t: t[2].y0) if axis == "x" else (lambda t: t[2].x1)
        ref = np.median([key(t) for t in out])
        out = [t for t in out if abs(key(t) - ref) < 25 * s]
    return out


def _calibrate(words, box, axis, s, lines):
    ticks = _ticks(words, box, axis, s)
    points = _equally_spaced([(v, p) for v, p, _ in ticks])
    length = box[2] - box[0] if axis == "x" else box[3] - box[1]
    cal = _fit(points, 0.006 * length)
    if cal is None:
        return None, ticks
    # the labels are centred on grid lines: snap to the exact vector lines
    lines = np.asarray(lines, float)
    if len(lines):
        snapped = []
        for v, _ in cal.ticks:
            p = cal.to_pixel(v)
            j = np.argmin(np.abs(lines - p))
            if abs(lines[j] - p) < max(4 * s, 0.01 * length):
                snapped.append((v, float(lines[j])))
        if len(snapped) >= max(3, len(cal.ticks) - 1):
            refit = _fit(snapped, 0.006 * length)
            if refit is not None:
                cal = refit
    if (axis == "x") != (cal.slope > 0):
        return None, ticks
    return cal, ticks


def _grid_positions(hs, vs, box):
    """Positions of the grid lines (and frame edges) crossing ``box``."""
    x0, y0, x1, y1 = box
    xs = [
        x
        for x, a, b in vs
        if x0 - 3 <= x <= x1 + 3 and min(b, y1) - max(a, y0) > 0.5 * (y1 - y0)
    ]
    ys = [
        y
        for y, a, b in hs
        if y0 - 3 <= y <= y1 + 3 and min(b, x1) - max(a, x0) > 0.5 * (x1 - x0)
    ]
    return xs, ys


# --------------------------------------------------------------------- titles


def _titles(words, box, x_ticks, y_ticks, s):
    """(y title, x title, plot title) phrases around ``box``."""
    x0, y0, x1, y1 = box
    used = {id(t[2]) for t in x_ticks + y_ticks}
    phrases = join_words([w for w in words if id(w) not in used and not w.colored])
    left = min((t[2].x0 for t in y_ticks), default=x0)
    below = max((t[2].y1 for t in x_ticks), default=y1)
    y_title = [
        p
        for p in phrases
        if abs(abs(p.angle) - 90) < 10
        and p.x1 <= left + 5 * s
        and p.cx > left - 150 * s
        and y0 - 20 * s < p.cy < y1 + 20 * s
    ]
    x_title = [
        p
        for p in phrases
        if abs(p.angle) < 10
        and below - 5 * s <= p.y0 < below + 120 * s
        and x0 < p.cx < x1
    ]
    title = [
        p
        for p in phrases
        if abs(p.angle) < 10 and y0 - 150 * s < p.y1 <= y0 + 5 * s and x0 < p.cx < x1
    ]

    if x_title:
        # the title is the first row under the labels, not the table below
        first = min(p.y0 for p in x_title)
        x_title = [p for p in x_title if p.y0 < first + 0.8 * max(p.size, 1.0)]

    def pick(cands, key):
        return " ".join(c.text for c in sorted(cands, key=key)) if cands else ""

    return (
        pick(y_title, lambda p: -p.cy if p.angle > 0 else p.cy),
        pick(x_title, lambda p: p.y0),
        pick(title, lambda p: -p.y1)[:200],
    )


# --------------------------------------------------------------------- lines


def _inside(points, box, pad):
    x0, y0, x1, y1 = box
    return (
        (points[:, 0] >= x0 - pad)
        & (points[:, 0] <= x1 + pad)
        & (points[:, 1] >= y0 - pad)
        & (points[:, 1] <= y1 + pad)
    )


def _chains(paths, box, s):
    """Polylines inside ``box``: consecutive subpaths joined end to start.

    Plotting tools draw a line as many short segments, in order; chaining in
    drawing order follows each line exactly, without guessing at junctions.
    Filled outlines of thick lines (polygons) give their centreline.
    """
    tol = 0.6 * s
    chains = []
    for p in paths:
        subs = p.subpaths
        if p.fill is not None:
            # a filled outline of a thick line (stroked or not): its centreline
            centres = [_centreline(sp, box, s) for sp in subs]
            if p.stroke is None or all(c is not None for c in centres):
                subs = [c for c in centres if c is not None]
                paint = ("fill", p.fill)
            else:
                paint = ("stroke", p.stroke, round(p.width, 1))
        elif p.stroke is not None:
            paint = ("stroke", p.stroke, round(p.width, 1))
        else:
            continue
        for sp in subs:
            inside = _inside(sp, box, 2 * s)
            # split where the path leaves the frame
            runs = np.split(
                np.arange(len(sp)), np.flatnonzero(np.diff(inside.astype(int))) + 1
            )
            for r in runs:
                if not inside[r[0]] or len(r) < 2:
                    continue
                seg = sp[r]
                last = chains[-1] if chains else None
                if (
                    last is not None
                    and last["paint"] == paint
                    and np.hypot(*(last["pts"][-1] - seg[0])) < tol
                ):
                    last["pts"] = np.vstack([last["pts"], seg[1:]])
                else:
                    chains.append({"pts": seg.copy(), "paint": paint, "order": p.order})
    return chains


def _centreline(poly, box, s):
    """Centreline of a closed polygon outlining a thick line, or None.

    The outline runs along one side of the line and back along the other: it
    is split at its two most distant vertices (the line ends) and the two
    sides, resampled by arc length, are averaged.
    """
    poly = np.asarray(poly, float)
    if len(poly) < 8 or not _inside(poly, box, 2 * s).all():
        return None
    if np.hypot(*(poly[0] - poly[-1])) < 1e-6:
        poly = poly[:-1]
    d = np.hypot(
        poly[:, None, 0] - poly[None, :, 0], poly[:, None, 1] - poly[None, :, 1]
    )
    i, j = np.unravel_index(np.argmax(d), d.shape)
    i, j = min(i, j), max(i, j)
    side_a = poly[i : j + 1]
    side_b = np.vstack([poly[j:], poly[: i + 1]])[::-1]

    def resample(p, n=200):
        arc = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
        t = np.linspace(0, arc[-1], n)
        return np.column_stack([np.interp(t, arc, p[:, 0]), np.interp(t, arc, p[:, 1])])

    a, b = resample(side_a), resample(side_b)
    width = np.median(np.hypot(*(a - b).T))
    length = d[i, j]
    if width > 12 * s or length < 8 * width:
        return None  # a filled area, not a line
    return (a + b) / 2


def _straight(pts, tol):
    """Whether a polyline is a straight segment (within ``tol`` px)."""
    a, b = pts[0], pts[-1]
    v = b - a
    n = np.hypot(*v)
    if n < 1e-9:
        return True
    dist = np.abs((pts[:, 0] - a[0]) * v[1] - (pts[:, 1] - a[1]) * v[0]) / n
    return dist.max() < tol


def _dist_to_polyline(pt, pts):
    a, b = pts[:-1], pts[1:]
    ab = b - a
    t = np.clip(((pt - a) * ab).sum(1) / np.maximum((ab**2).sum(1), 1e-12), 0, 1)
    proj = a + t[:, None] * ab
    return np.hypot(*(proj - pt).T).min() if len(a) else np.inf


def _vertices(pts, tol):
    """Corner points of a polyline (Douglas-Peucker simplification).

    A smooth curve keeps enough points to follow its bend within ``tol``;
    a polyline of straight segments reduces to its corners.
    """
    keep = np.zeros(len(pts), bool)
    keep[[0, -1]] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        v = b - a
        n = np.hypot(*v)
        seg = pts[i + 1 : j]
        if n < 1e-9:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs((seg[:, 0] - a[0]) * v[1] - (seg[:, 1] - a[1]) * v[0]) / n
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return pts[keep]


def split_lines(chains, box, s):
    """Separate speed-line candidates from envelopes and clutter.

    Returns ``(lines, envelopes)``, lists of (N, 2) arrays ordered left to
    right. Envelopes are polylines whose corners all lie on other lines: the
    surge line, the choke line and control lines join the speed lines' ends
    (or cross them at their corners).
    """
    w, h = box[2] - box[0], box[3] - box[1]
    cands = []
    for c in chains:
        p = c["pts"]
        if np.ptp(p[:, 0]) < 0.03 * w and np.ptp(p[:, 1]) < 0.03 * h:
            continue  # markers, letters, tick marks
        closed = np.hypot(*(p[0] - p[-1])) < 1.0 * s
        if closed and np.ptp(p[:, 0]) < 0.1 * w and np.ptp(p[:, 1]) < 0.1 * h:
            continue  # point markers (circles, squares)
        d = np.diff(p, axis=0)
        d = d[np.hypot(*d.T) > 0.5 * s]
        if (
            len(d)
            and (
                (np.abs(d[:, 1]) <= 0.02 * np.abs(d[:, 0]))
                | (np.abs(d[:, 0]) <= 0.02 * np.abs(d[:, 1]))
            ).all()
        ):
            continue  # grid, frame, reference-point guides (axis-aligned only)
        cands.append(p)
    lines, envelopes = [], []
    tol = 1.5 * s
    for k, p in enumerate(cands):
        others = [q for j, q in enumerate(cands) if j != k]
        # corners (collinear points merged: a centreline has many points)
        corners = _vertices(p, 1.0 * s)
        on_other = [any(_dist_to_polyline(v, q) < tol for q in others) for v in corners]
        # other lines ending along it, away from its own ends: the top speed
        # line carries the ends of the surge, control and choke lines at its
        # own ends, a surge line carries the speed lines' ends all along
        inner_ends = sum(
            any(
                _dist_to_polyline(e, p) < tol
                and min(np.hypot(*(e - p[0])), np.hypot(*(e - p[-1]))) > 3 * tol
                for e in (q[0], q[-1])
            )
            for q in others
        )
        if 3 <= len(corners) <= 40 and np.mean(on_other) >= 0.75:
            envelopes.append(p)  # joins other lines at every corner
        elif len(corners) <= 40 and inner_ends >= 2:
            envelopes.append(p)  # a surge or choke line through the line ends
        else:
            lines.append(p)
    order = lambda p: p if p[0, 0] <= p[-1, 0] else p[::-1]  # noqa: E731
    return [order(p) for p in lines], [order(p) for p in envelopes]


# --------------------------------------------------------------------- speeds

_RPM = re.compile(r"(?:\b([A-H])\b\W{0,3})?(\d{3,6}(?:[.,]\d+)?)\s*R\s*P\s*M", re.I)
# letter legend printed anywhere on the page: "A=10000", "A: 10000 RPM"
_LETTER = re.compile(r"(?<![A-Za-z])([A-H])\s*[=:]\s*(\d{3,6}(?:[.,]\d+)?)\b")


def letter_legend(text):
    """Speeds keyed by the letters that tag the lines ("A=10000 ... F=7000")."""
    out = {}
    for m in _LETTER.finditer(text):
        out.setdefault(m.group(1), float(m.group(2).replace(",", ".")))
    return out


def _line_labels(lines, words, used, box, s, letters=None, penalty=None):
    """Speed printed at a line end, per line (None when not found).

    Every number not used as a tick label, inside or just outside the frame,
    is matched to its nearest line end; pairs are taken nearest first, one
    label per line, within a few glyph heights.
    """
    x0, y0, x1, y1 = box
    near = [
        w
        for w in words
        if id(w) not in used
        and not w.colored
        and x0 - 20 * s < w.cx < x1 + 120 * s
        and y0 - 20 * s < w.cy < y1 + 60 * s
    ]
    # a "%" set apart from its number ("95 %") still belongs to it
    pct_words = [w for w in near if w.text.strip() == "%"]
    labels = []
    for w in near:
        t = w.text.strip()
        if letters and t in letters:
            labels.append((letters[t], w, False))  # letter tag of a legend
            continue
        v = parse_number(t.rstrip("%"))
        if v is None or v <= 0:
            continue
        pct = t.endswith("%")
        if not pct:
            for p in pct_words:
                if abs((p.angle - w.angle + 180) % 360 - 180) < 10 and _gap(
                    w, p
                ) < 1.2 * max(w.size, p.size):
                    pct = True
                    break
        labels.append((v, w, pct))

    def assign(end):
        pairs = []
        for i, p in enumerate(lines):
            pt = p[-1] if end == "hi" else p[0]
            for k, (v, w, pct) in enumerate(labels):
                d = w.distance_to(*pt)
                if d < 3 * max(w.size, 10 * s):
                    # envelope-like polylines take a label only when no
                    # speed line is as close (they share end points)
                    extra = penalty[i] * 3 * max(w.size, 10 * s) if penalty else 0
                    pairs.append((d + extra, i, k))
        found = [None] * len(lines)
        taken = set()
        cost = 0.0
        for d, i, k in sorted(pairs):
            if found[i] is None and k not in taken:
                found[i] = labels[k]
                taken.add(k)
                cost += d
        return found, (sum(f is not None for f in found), -cost)

    # a sheet prints every label at the same end (some at the choke end,
    # others at the surge end): where the surge end of one line
    # meets the choke end of the next, the consistent end settles which line
    # a label names
    (lo, score_lo), (hi, score_hi) = assign("lo"), assign("hi")
    return hi if score_hi >= score_lo else lo


def _gap(a, b):
    """Distance between two word boxes (0 when they touch or overlap)."""
    dx = max(a.x0 - b.x1, b.x0 - a.x1, 0)
    dy = max(a.y0 - b.y1, b.y0 - a.y1, 0)
    return math.hypot(dx, dy)


def _reference_point(words, box, xcal, ycal, s):
    """Rated point printed in colour on the axes: (flow, value) or None.

    Some sheets mark the rated point with coloured guide lines and print
    its value at the y axis and its flow at the x axis.
    """
    x0, y0, x1, y1 = box
    ys, xs = [], []
    for w in words:
        if not w.colored or not (x0 - 5 * s < w.cx < x1 and y0 < w.cy < y1):
            continue
        v = parse_number(w.text)
        if v is None:
            continue
        if w.x0 < x0 + 0.2 * (x1 - x0) and abs(w.angle) < 10:
            ys.append((v, w))
        elif abs(abs(w.angle) - 90) < 10 and w.y1 > y0 + 0.5 * (y1 - y0):
            xs.append((v, w))
    if len(xs) != 1 or len(ys) != 1:
        return None
    flow, value = xs[0][0], ys[0][0]
    # the printed values sit next to their guide lines: the value's label
    # is centred on its height and the flow's on its abscissa
    if abs(ycal.to_pixel(value) - ys[0][1].cy) > 60 * s:
        return None
    if abs(xcal.to_pixel(flow) - xs[0][1].cx) > 60 * s:
        return None
    return float(flow), float(value)


# --------------------------------------------------------------------- plots


def vector_plots(page_no, words, paths, size, dpi, n_points=40, text=""):
    """``DigitizedPlot`` objects for every vector plot of a page.

    ``words`` and ``paths`` come from ``_pdf.page_words`` / ``page_paths``;
    ``size`` is the rendered page size (width, height) in pixels. Frames
    with tick labels but no line (an embedded raster plot inside a vector
    frame) are returned in the second list.
    """
    from ._document import DigitizedPlot, _resample

    s = dpi / 300
    width, height = size
    hs, vs = _axis_lines(paths, 0.05 * width, 0.05 * height)
    letters = letter_legend(text)
    found = []
    for box in find_vector_frames(paths, width, height):
        gx, gy = _grid_positions(hs, vs, box)
        xcal, xt = _calibrate(words, box, "x", s, gx)
        ycal, yt = _calibrate(words, box, "y", s, gy)
        found.append([box, xcal, xt, ycal, yt])
    # plots stacked on one x axis print its labels under the bottom plot only
    shared = set()
    for f in found:
        if f[3] is not None and len(f[4]) >= 3 and (f[1] is None or len(f[2]) < 3):
            for o in found:
                if (
                    o is not f
                    and o[1] is not None
                    and len(o[2]) >= 3
                    and abs(o[0][0] - f[0][0]) < 4 * s
                    and abs(o[0][2] - f[0][2]) < 4 * s
                    and o[0][1] > f[0][1]
                ):
                    f[1], f[2] = o[1], o[2]
                    shared.add(f[0])
                    break
    axes = [
        tuple(f[:5])
        for f in found
        if f[1] is not None and f[3] is not None and len(f[2]) >= 3 and len(f[4]) >= 3
    ]
    # a frame drawn around a plot (or the page border) may pick up the
    # plot's labels too: keep the innermost
    axes = [a for a in axes if not any(_encloses(a[0], o[0]) for o in axes)]
    plots, rejected = [], []
    for index, (box, xcal, xt, ycal, yt) in enumerate(axes):
        chains = _chains(paths, box, s)
        lines, envelopes = split_lines(chains, box, s)
        if not lines and not envelopes:
            rejected.append(box)
            continue
        ib = tuple(int(round(v)) for v in box)
        plot = DigitizedPlot(page=page_no, index=index, box=ib, dpi=dpi)
        plot.source = "vector"
        plot.y_title, plot.x_title, title = _titles(words, box, xt, yt, s)
        plot.param, plot.units = classify_y_title(plot.y_title)
        if plot.param is None:
            # the plot title names the curve too (e.g. "Head Vs Flow")
            plot.param, plot.units = classify_y_title(
                title.split(" VS ")[0].split(" Vs ")[0]
            )
        plot.flow_units, _ = classify_x_title(plot.x_title or title)
        if plot.param is None:
            plot.warnings.append("y-axis title not recognized")
            plots.append(plot)
            continue
        plot.x_ticks, plot.y_ticks = xcal.ticks, ycal.ticks
        plot.x_axis = {"offset": xcal.offset, "slope": xcal.slope}
        plot.y_axis = {"offset": ycal.offset, "slope": ycal.slope}
        plot.x_residual, plot.y_residual = xcal.residual, ycal.residual
        if box in shared:
            plot.notes.append("x axis read under the plot below (shared axis)")
        if plot.units is None:
            if plot.param == "eff":
                vals = ycal.to_value([box[1], box[3]])
                plot.units = "percent" if max(vals) > 1.5 else "dimensionless"
            elif plot.param == "head":
                plot.units = "kJ/kg"
                plot.warnings.append("head units not read, assuming kJ/kg")
        used = {id(t[2]) for t in xt + yt}
        # a printed label makes a speed line, whatever its shape: label every
        # candidate, then keep unlabelled envelope-like ones apart
        cands = lines + envelopes
        flags = [0] * len(lines) + [1] * len(envelopes)
        labels = _line_labels(cands, words, used, box, s, letters, penalty=flags)
        lines, envelopes, kept = [], [], []
        for p, f, lab in zip(cands, flags, labels):
            if f and lab is None:
                envelopes.append(p)
            else:
                lines.append(p)
                kept.append(lab)
        labels = kept
        if not lines:
            rejected.append(box)
            continue
        for p, lab in zip(lines, labels):
            flow, value = xcal.to_value(p[:, 0]), ycal.to_value(p[:, 1])
            plot.candidates.append({"flow": flow, "value": value, "cost": 0.0})
        n_labeled = sum(lab is not None for lab in labels)
        if n_labeled and (n_labeled < 2 or n_labeled < 0.5 * len(lines)):
            # one stray number near a line end is not a labelling scheme
            labels = [None] * len(lines)
            n_labeled = 0
        if n_labeled:
            # each line names its speed; % labels are resolved per case
            # (they need the 100 % speed printed on the sheet)
            for p, lab in zip(lines, labels):
                px, py = _resample(p[:, 0], p[:, 1], n_points)
                curve = {
                    "speed": None,
                    "flow": xcal.to_value(px),
                    "value": ycal.to_value(py),
                    "px": np.column_stack([px, py]),
                }
                if lab is not None:
                    v, _, pct = lab
                    curve["label"] = f"{v:g}%" if pct else f"{v:g}"
                    curve["speed"] = None if pct else float(v)
                plot.curves.append(curve)
            speeds = sorted(
                {v for v, _, pct in filter(None, labels) if not pct}, reverse=True
            )
            plot.speeds = speeds
            plot.legend_readings = [speeds] if speeds else []
            plot.labeled = True
            if n_labeled < len(lines):
                plot.warnings.append(
                    f"{len(lines) - n_labeled} of {len(lines)} lines without a speed "
                    "label (matched to the other plots of the case)"
                )
        else:
            phrases = join_words([w for w in words if id(w) not in used])
            x0, y0, x1, y1 = box
            legend = [
                float(m.group(2).replace(",", "."))
                for p in phrases
                if x0 < p.cx < x1 and y0 < p.cy < y1
                for m in _RPM.finditer(p.text)
            ]
            plot.legend_readings = [legend] if legend else []
            plot.speeds = sorted(legend, reverse=True)
            if not legend:
                plot.warnings.append("no line labels or legend speeds found")
            for p in sorted(lines, key=lambda p: p[-1, 0]):
                px, py = _resample(p[:, 0], p[:, 1], n_points)
                plot.curves.append(
                    {
                        "speed": None,
                        "flow": xcal.to_value(px),
                        "value": ycal.to_value(py),
                        "px": np.column_stack([px, py]),
                    }
                )
        plot.envelopes = [
            {"flow": xcal.to_value(p[:, 0]), "value": ycal.to_value(p[:, 1])}
            for p in envelopes
        ]
        ref = _reference_point(words, box, xcal, ycal, s)
        if ref is not None:
            plot.reference = ref
        plots.append(plot)
    return plots, rejected
