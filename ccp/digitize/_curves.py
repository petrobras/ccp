"""Curve extraction: clean the plot interior, skeletonize, trace speed lines.

The plot interior holds the speed lines plus clutter: grid lines, the
surge line (often coloured), legend or annotation boxes, line letters and
point markers. Clutter is removed by colour, by
rectangle detection and by component size; the remaining strokes are thinned
to a one-pixel skeleton, turned into a graph (end points, junctions, edges)
and traced end to end, going straight through junctions so that touching or
crossing lines (efficiency curves often do) come out as separate curves.
"""

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi

from ._image import Box, _segments, colored_mask, components, gray

__all__ = ["TracedCurve", "extract_curves", "find_rectangles"]

_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class TracedCurve:
    """Ordered pixel path (page frame) of one line, left to right."""

    x: np.ndarray
    y: np.ndarray
    cost: float = 0.0  # summed turning penalty at junctions
    endpoints: tuple = field(default=(None, None))

    @property
    def length(self):
        return float(np.hypot(np.diff(self.x), np.diff(self.y)).sum())


# --------------------------------------------------------------------- cleaning


def find_rectangles(mask, s):
    """Axis-aligned rectangles drawn with solid lines (legend, info boxes)."""
    hs = _segments(mask, int(60 * s), axis=1)
    rects = []
    for i, (ya, a1, b1, _, _) in enumerate(hs):
        for yb, a2, b2, _, _ in hs[i + 1 :]:
            if yb - ya < 20 * s or abs(a1 - a2) > 6 * s or abs(b1 - b2) > 6 * s:
                continue
            x0, x1 = int(min(a1, a2)), int(max(b1, b2)) - 1
            y0, y1 = int(ya), int(yb)
            left = mask[y0:y1, max(x0 - 1, 0) : x0 + 3].any(axis=1).mean()
            right = mask[y0:y1, max(x1 - 2, 0) : x1 + 2].any(axis=1).mean()
            if left > 0.9 and right > 0.9:
                rects.append(Box(x0, y0, x1, y1))
    # keep outermost rectangles only
    return [
        r for r in rects if not any(o is not r and o.contains(r, tol=2) for o in rects)
    ]


def clean_mask(img, box, s, threshold=150, blank=()):
    """Binary mask of the speed-line pixels inside ``box`` (box frame).

    ``blank`` holds extra page-frame rectangles to erase (text boxes found by
    OCR).
    """
    from ._image import dark_mask, frame_thickness

    t = max(int(round(3 * s)), frame_thickness(dark_mask(img, 190), box) + 1)
    sub = img[box.y0 + t : box.y1 - t + 1, box.x0 + t : box.x1 - t + 1]
    g = gray(sub)
    mask = (g < threshold) & ~colored_mask(sub, min_chroma=60)
    # pixels next to coloured lines are antialiasing of the surge line
    near_color = ndi.binary_dilation(colored_mask(sub, 60), iterations=max(1, int(s)))
    mask &= ~near_color
    h, w = mask.shape
    # box borders are often thin gray lines: detect them on a lenient mask
    light = (g < 200) & ~colored_mask(sub, min_chroma=60)
    rects = [r for r in find_rectangles(light, s) if r.width * r.height < 0.4 * h * w]
    pad = int(4 * s)
    ox, oy = box.x0 + t, box.y0 + t
    rects = rects + [Box(r.x0 - ox, r.y0 - oy, r.x1 - ox, r.y1 - oy) for r in blank]
    for r in rects:
        mask[
            max(r.y0 - pad, 0) : r.y1 + pad + 1, max(r.x0 - pad, 0) : r.x1 + pad + 1
        ] = False
    # drop grid dashes, dots, letters and the reference-point square when free
    labels, slices = components(mask)
    small = int(45 * s)
    for i, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if max(h, w) < small:
            mask[sl][labels[sl] == i] = False
    return mask, (box.x0 + t, box.y0 + t), rects


def remove_grid(mask, s):
    """Remove dashed-grid pixels that touch the curves.

    Grid rows/columns are found from the projection profile; a grid pixel is
    only cleared when the curve mask is thin there in the orthogonal direction
    (so a curve running along a grid line survives).
    """
    out = mask.copy()
    for axis in (0, 1):
        prof = mask.mean(axis=axis)
        lines = np.flatnonzero(prof > 0.12)
        for k in lines:
            if axis == 0:  # vertical grid line at column k
                col = out[:, k]
                left = out[:, max(k - 2, 0)]
                right = out[:, min(k + 2, out.shape[1] - 1)]
                out[:, k] = col & (left | right)
            else:
                row = out[k, :]
                up = out[max(k - 2, 0), :]
                down = out[min(k + 2, out.shape[0] - 1), :]
                out[k, :] = row & (up | down)
    return out


# --------------------------------------------------------------------- skeleton graph


def _skeleton(mask):
    from skimage.morphology import skeletonize

    return skeletonize(mask)


def _neighbors(sk, y, x):
    h, w = sk.shape
    for dy, dx in _N8:
        yy, xx = y + dy, x + dx
        if 0 <= yy < h and 0 <= xx < w and sk[yy, xx]:
            yield yy, xx


def build_graph(sk):
    """Nodes (end points and junction clusters) and edges (pixel chains)."""
    deg = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    deg = (deg.astype(int) - 1) * sk
    node_px = sk & (deg != 2)
    node_lab, n_nodes = ndi.label(node_px, structure=np.ones((3, 3), bool))
    centers = ndi.center_of_mass(node_px, node_lab, range(1, n_nodes + 1))
    nodes = {i + 1: (c[1], c[0]) for i, c in enumerate(centers)}  # (x, y)
    edges = []
    visited = np.zeros_like(sk, bool)
    direct = set()
    ys, xs = np.nonzero(node_px)
    for y, x in zip(ys, xs):
        u = node_lab[y, x]
        for ny, nx in _neighbors(sk, y, x):
            v = node_lab[ny, nx]
            if v:
                if v != u and (min(u, v), max(u, v)) not in direct:
                    direct.add((min(u, v), max(u, v)))
                    edges.append((u, v, [(x, y), (nx, ny)]))
                continue
            if visited[ny, nx]:
                continue
            visited[ny, nx] = True
            path = [(x, y), (nx, ny)]
            prev, cur = (y, x), (ny, nx)
            end = None
            while end is None:
                nxt = None
                for q in _neighbors(sk, *cur):
                    if q == prev:
                        continue
                    lab = node_lab[q]
                    if lab:
                        if lab == u and len(path) <= 2:
                            continue
                        end = lab
                        path.append((q[1], q[0]))
                        break
                    if not visited[q]:
                        nxt = q
                if end is not None or nxt is None:
                    break
                visited[nxt] = True
                prev, cur = cur, nxt
                path.append((cur[1], cur[0]))
            if end is not None:
                edges.append((u, end, path))
    return nodes, edges


def _degree(edges):
    d = defaultdict(int)
    for u, v, _ in edges:
        d[u] += 1
        d[v] += 1
    return d


def _contract(nodes, edges, merge_len):
    """Merge junctions joined by a stub: an X crossing thins into two Y's."""
    changed = True
    while changed:
        changed = False
        deg = _degree(edges)
        for k, (u, v, path) in enumerate(edges):
            if u != v and len(path) <= merge_len and deg[u] >= 3 and deg[v] >= 3:
                (x0, y0), (x1, y1) = nodes[u], nodes[v]
                nodes[u] = ((x0 + x1) / 2, (y0 + y1) / 2)
                new = []
                for j, (a, b, p) in enumerate(edges):
                    if j == k:
                        continue
                    a = u if a == v else a
                    b = u if b == v else b
                    new.append((a, b, p))
                edges = new
                changed = True
                break
    return edges


def prune(nodes, edges, spur_len, loop_len, merge_len=0):
    """Remove short spurs and collapse small loops (reference-point squares)."""
    changed = True
    while changed:
        changed = False
        if merge_len:
            n_before = len(edges)
            edges = _contract(nodes, edges, merge_len)
            changed = changed or len(edges) != n_before
        deg = _degree(edges)
        keep = []
        for e in edges:
            u, v, path = e
            n = len(path)
            if u == v and n < loop_len:  # small self loop
                changed = True
                continue
            if n < spur_len and ((deg[u] == 1) != (deg[v] == 1)):
                changed = True
                continue
            keep.append(e)
        edges = keep
        # parallel short edges between the same pair: a loop around a marker
        by_pair = defaultdict(list)
        for i, (u, v, path) in enumerate(edges):
            by_pair[(min(u, v), max(u, v))].append(i)
        drop = set()
        for (u, v), idx in by_pair.items():
            if u != v and len(idx) > 1:
                short = [i for i in idx if len(edges[i][2]) < loop_len]
                if len(short) > 1:
                    # replace by the straight chord between the two nodes
                    drop.update(short)
                    (x0, y0), (x1, y1) = nodes[u], nodes[v]
                    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 2
                    chord = list(zip(np.linspace(x0, x1, n), np.linspace(y0, y1, n)))
                    edges.append((u, v, chord))
                    changed = True
        edges = [e for i, e in enumerate(edges) if i not in drop]
        # merge chains through degree-2 nodes
        deg = _degree(edges)
        for node in [n for n, d in deg.items() if d == 2]:
            inc = [i for i, (u, v, _) in enumerate(edges) if node in (u, v)]
            if len(inc) != 2:
                continue
            i, j = inc
            if i == j:
                continue
            a, b = edges[i], edges[j]
            if a[0] == a[1] or b[0] == b[1]:
                continue
            pa = a[2] if a[1] == node else a[2][::-1]
            pb = b[2] if b[0] == node else b[2][::-1]
            ua = a[0] if a[1] == node else a[1]
            vb = b[1] if b[0] == node else b[0]
            new = (ua, vb, list(pa) + list(pb[1:]))
            edges = [e for k, e in enumerate(edges) if k not in (i, j)] + [new]
            changed = True
            break
    return edges


# --------------------------------------------------------------------- tracing


def _leaving_direction(path, node_xy, look):
    """Unit vector leaving ``node_xy`` along ``path`` (oriented from the node)."""
    p = np.asarray(path, float)
    if np.hypot(*(p[0] - node_xy)) > np.hypot(*(p[-1] - node_xy)):
        p = p[::-1]
    k = min(len(p) - 1, look)
    d = p[k] - p[0]
    n = np.hypot(*d)
    return d / n if n else d


@dataclass
class Stroke:
    nodes: list  # visited nodes, start to end
    edges: list  # (edge index, reversed?) between consecutive nodes
    scores: list  # straightness at each interior node (len(nodes) - 2)

    @property
    def start(self):
        return self.nodes[0]

    @property
    def end(self):
        return self.nodes[-1]

    def reversed(self):
        return Stroke(
            self.nodes[::-1],
            [(i, not r) for i, r in self.edges[::-1]],
            self.scores[::-1],
        )

    def truncated(self, k):
        """Drop the last ``k`` edges."""
        n = len(self.edges) - k
        return Stroke(self.nodes[: n + 1], self.edges[:n], self.scores[: max(n - 1, 0)])

    def points(self, edges):
        pts = []
        for i, rev in self.edges:
            seq = edges[i][2][::-1] if rev else edges[i][2]
            pts.extend(seq if not pts else seq[1:])
        return np.asarray(pts, float)

    @property
    def cost(self):
        return float(sum(1 - sc for sc in self.scores))


def trace_strokes(nodes, edges, look, min_straightness=0.3):
    """Walk from every end point through junctions, going as straight as possible."""
    deg = _degree(edges)
    inc = defaultdict(list)
    for i, (u, v, _) in enumerate(edges):
        inc[u].append(i)
        if v != u:
            inc[v].append(i)
    ends = [n for n, d in deg.items() if d == 1]
    strokes = []
    for start in ends:
        (i,) = inc[start]
        node = start
        st = Stroke([start], [], [])
        used = defaultdict(int)
        while True:
            u, v, path = edges[i]
            used[i] += 1
            other = v if u == node else u
            st.edges.append((i, u != node))
            st.nodes.append(other)
            if deg[other] == 1:
                break
            arrive = -_leaving_direction(path, nodes[other], look)
            best, best_score = None, -2.0
            for j in inc[other]:
                if j == i or used[j] >= 2:
                    continue
                d = _leaving_direction(edges[j][2], nodes[other], look)
                score = float(np.dot(arrive, d))
                if score > best_score:
                    best, best_score = j, score
            if best is None or best_score < min_straightness:
                break
            st.scores.append(best_score)
            i, node = best, other
            if len(st.edges) > 2 * len(edges):
                break
        strokes.append(st)
    return strokes


def _shared_suffix(a, b):
    k = 0
    while (
        k < len(a.edges)
        and k < len(b.edges)
        and a.edges[-1 - k][0] == b.edges[-1 - k][0]
    ):
        k += 1
    return k


def resolve_shared_ends(strokes):
    """Give a shared tail to the stroke that enters it most smoothly.

    A line that starts on another line (touching efficiency curves) is traced
    into the other line's tail; the junction where the tails merge decides who
    owns the tail: the stroke with the lower straightness there is cut.
    """
    strokes = [s for s in strokes if s.edges]
    # deduplicate by end-point pair (each line is walked from both ends)
    uniq = {}
    for s in strokes:
        key = (min(s.start, s.end), max(s.start, s.end))
        if key not in uniq or s.cost < uniq[key].cost:
            uniq[key] = s
    strokes = list(uniq.values())
    for _ in range(10 * len(strokes) + 10):
        conflict = None
        for i, a in enumerate(strokes):
            for j in range(i + 1, len(strokes)):
                b = strokes[j]
                shared = {a.start, a.end} & {b.start, b.end}
                if shared:
                    conflict = (i, j, shared.pop())
                    break
            if conflict:
                break
        if conflict is None:
            break
        i, j, x = conflict
        a, b = strokes[i], strokes[j]
        a = a if a.end == x else a.reversed()
        b = b if b.end == x else b.reversed()
        k = _shared_suffix(a, b)
        if k == 0:
            # touch only at an end node: keep both, but mark by splitting the key
            strokes[j] = b.truncated(0)
            strokes[j].nodes[-1] = (x, "dup")
            continue
        sa = a.scores[len(a.edges) - k - 1] if len(a.edges) > k else -1
        sb = b.scores[len(b.edges) - k - 1] if len(b.edges) > k else -1
        if sa >= sb:
            strokes[j] = b.truncated(k)
        else:
            strokes[i] = a.truncated(k)
        strokes = [s for s in strokes if s.edges]
    return strokes


def _smooth(x, y, window):
    if len(x) < window or window < 2:
        return x, y
    k = np.ones(window) / window
    xp = np.concatenate([np.full(window // 2, x[0]), x, np.full(window // 2, x[-1])])
    yp = np.concatenate([np.full(window // 2, y[0]), y, np.full(window // 2, y[-1])])
    xs = np.convolve(xp, k, mode="valid")[: len(x)]
    ys = np.convolve(yp, k, mode="valid")[: len(y)]
    xs[0], ys[0], xs[-1], ys[-1] = x[0], y[0], x[-1], y[-1]
    return xs, ys


def select_curves(strokes, edges, min_extent, n_expected=None):
    """Choose one stroke per speed line, ordered by the x of their right end.

    Lines that touch or overlap (efficiency lines often run together near
    surge) keep the shared part on every stroke: the drawing cannot tell where
    each one starts, so the flow range is settled later against the plot with
    the surge line (``DigitizedCase``). Each right (choke) end keeps its
    straightest stroke.
    """
    best = {}
    for st in strokes:
        if not st.edges:
            continue
        p = st.points(edges)
        if np.ptp(p[:, 0]) < min_extent:
            continue
        a, b = st.start, st.end
        if p[0, 0] > p[-1, 0]:
            p = p[::-1]
            a, b = b, a
        key = b  # right end node
        score = (round(st.cost, 1), -np.ptp(p[:, 0]))
        if key not in best or score < best[key][0]:
            best[key] = (score, p, st, (a, b))
    cands = [(p, st, ends) for _, p, st, ends in best.values()]

    # near-duplicates (a letter touching a line end adds a second end point
    # whose stroke runs along the same line): drop a stroke whose pixels
    # mostly belong to a longer kept stroke
    def length(st):
        return sum(len(edges[e][2]) for e, _ in st.edges)

    cands.sort(key=lambda c: -length(c[1]))
    keep = []
    for p, st, ends in cands:
        own = {e for e, _ in st.edges}
        total = length(st)
        dup = False
        for _, st2, _ in keep:
            other = {e for e, _ in st2.edges}
            shared = sum(len(edges[e][2]) for e in own & other)
            if total and shared / total > 0.6:
                dup = True
                break
        if not dup:
            keep.append((p, st, ends))
    cands = keep
    if n_expected and len(cands) > n_expected:
        # keep the longest lines (in x extent): leftovers are letters or debris
        cands = sorted(cands, key=lambda c: -np.ptp(c[0][:, 0]))[:n_expected]
    cands.sort(key=lambda c: c[0][-1, 0])
    return [TracedCurve(p[:, 0], p[:, 1], st.cost, ends) for p, st, ends in cands]


def extract_curves(img, box, s=1.0, n_expected=None, blank=()):
    """Trace the speed lines of one plot.

    Returns ``(curves, debug)`` where ``curves`` are ``TracedCurve`` objects in
    page pixel coordinates sorted by their right-end x, and ``debug`` holds the
    intermediate masks for diagnostics.
    """
    mask, (ox, oy), rects = clean_mask(img, box, s, blank=blank)
    mask = remove_grid(mask, s)
    # re-drop fragments left by the grid removal
    labels, slices = components(mask)
    for i, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) < int(45 * s):
            mask[sl][labels[sl] == i] = False
    sk = _skeleton(mask)
    nodes, edges = build_graph(sk)
    edges = prune(
        nodes, edges, spur_len=int(18 * s), loop_len=int(90 * s), merge_len=int(12 * s)
    )
    strokes = trace_strokes(nodes, edges, look=int(20 * s))
    curves = select_curves(
        strokes, edges, min_extent=0.04 * box.width, n_expected=n_expected
    )
    # every distinct stroke, for re-selection against physics (flow ranges)
    candidates = []
    seen = set()
    for st in strokes:
        key = (
            min(st.start, st.end),
            max(st.start, st.end),
            tuple(sorted(e for e, _ in st.edges)),
        )
        if not st.edges or key in seen:
            continue
        seen.add(key)
        p = st.points(edges)
        if np.ptp(p[:, 0]) < 0.04 * box.width:
            continue
        if p[0, 0] > p[-1, 0]:
            p = p[::-1]
        x, y = _smooth(p[:, 0], p[:, 1], max(3, int(5 * s)))
        candidates.append(TracedCurve(x + ox, y + oy, st.cost, (st.start, st.end)))
    out = []
    for c in curves:
        x, y = _smooth(c.x, c.y, max(3, int(5 * s)))
        out.append(TracedCurve(x + ox, y + oy, c.cost, c.endpoints))
    debug = dict(
        mask=mask,
        skeleton=sk,
        rects=rects,
        offset=(ox, oy),
        n_strokes=len(strokes),
        candidates=candidates,
    )
    return out, debug
