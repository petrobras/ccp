"""Raster helpers: page rendering, colour masks and plot-frame detection."""

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi

__all__ = ["Box", "render_page", "gray", "dark_mask", "red_mask", "find_plot_boxes"]


@dataclass(frozen=True)
class Box:
    """Axis-aligned pixel rectangle; ``x1``/``y1`` are inclusive."""

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    def contains(self, other, tol=0):
        return (
            self.x0 - tol <= other.x0
            and self.y0 - tol <= other.y0
            and other.x1 <= self.x1 + tol
            and other.y1 <= self.y1 + tol
        )

    def as_tuple(self):
        return (self.x0, self.y0, self.x1, self.y1)


def render_page(page, dpi=300):
    """Render a pypdfium2 page to an RGB ``uint8`` array (H, W, 3)."""
    img = page.render(scale=dpi / 72).to_numpy()
    if img.ndim == 2:
        img = np.repeat(img[..., None], 3, axis=2)
    return np.ascontiguousarray(img[..., :3])


def gray(img):
    return img.astype(np.int16).mean(axis=2)


def red_mask(img):
    """Saturated red pixels (the surge line on most vendor sheets)."""
    r, g, b = (img[..., i].astype(np.int16) for i in range(3))
    return (r > 120) & (r - g > 70) & (r - b > 70)


def colored_mask(img, min_chroma=60):
    """Any strongly coloured pixel (not gray/black/white)."""
    i = img.astype(np.int16)
    return (i.max(axis=2) - i.min(axis=2)) > min_chroma


def dark_mask(img, threshold=140):
    """Dark, uncoloured pixels: curves, text, frames and grid."""
    return (gray(img) < threshold) & ~colored_mask(img)


def _runs(line):
    """Start/end (exclusive) indexes of the True runs of a 1-D bool array."""
    d = np.diff(np.concatenate([[0], line.astype(np.int8), [0]]))
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1)


def _segments(mask, min_len, axis):
    """Long straight runs along ``axis`` (0: vertical, 1: horizontal).

    Returns a list of (position, start, end) with adjacent parallel runs merged
    (a 3 px thick line yields one segment).
    """
    m = mask if axis == 1 else mask.T
    raw = []
    for pos in range(m.shape[0]):
        s, e = _runs(m[pos])
        keep = (e - s) >= min_len
        for a, b in zip(s[keep], e[keep]):
            raw.append((pos, a, b))
    merged = []
    for pos, a, b in raw:
        for seg in merged:
            if pos - seg[1] <= 2 and abs(a - seg[2]) < 8 and abs(b - seg[3]) < 8:
                seg[1] = pos
                seg[2] = min(seg[2], a)
                seg[3] = max(seg[3], b)
                break
        else:
            merged.append([pos, pos, a, b])
    return [((p0 + p1) / 2, a, b, p0, p1) for p0, p1, a, b in merged]


def find_plot_boxes(img, min_size=0.12, dpi=300):
    """Find plot frames on a rendered page.

    A plot is bounded by two long vertical lines (left axis and right border) of
    matching extent with a horizontal line joining their lower ends (the x axis)
    or their upper ends (the frame). Either may be missing or broken: some
    vendors draw the top border as a dashed grid line.
    Boxes that contain another box (the page border) are dropped.
    """
    # lenient threshold: resampled sheets blur 1 px axis lines to mid gray
    dark = dark_mask(img, threshold=190)
    h, w = dark.shape
    # images stacked in strips leave 1-3 px seams across the axis lines
    # (grid dashes are separated by wider gaps and must stay open)
    k = max(2, int(round(4 * dpi / 300)))
    vclosed = ndi.binary_closing(dark, structure=np.ones((k, 1), bool))
    hclosed = ndi.binary_closing(dark, structure=np.ones((1, k), bool))
    vert = _segments(vclosed, int(min_size * h), axis=0)
    horiz = _segments(hclosed, int(min_size * w), axis=1)
    boxes = []
    for i, (xa, ya0, ya1, xa0, xa1) in enumerate(vert):
        for xb, yb0, yb1, xb0, xb1 in vert[i + 1 :]:
            if xb - xa < min_size * w:
                continue
            if abs(ya0 - yb0) > 10 or abs(ya1 - yb1) > 10:
                continue
            bottom = max(ya1, yb1)
            top = min(ya0, yb0)
            # a horizontal line must join the verticals at the bottom (x axis)
            # or at the top (frame); vendors omit either one
            has_axis = any(
                (abs(y - bottom) < 10 or abs(y - top) < 10)
                and a <= xa + 10
                and b >= xb - 10
                for y, a, b, _, _ in horiz
            )
            if has_axis:
                boxes.append(
                    Box(int(xa0), int(min(ya0, yb0)), int(xb1), int(bottom) - 1)
                )
    boxes = list(dict.fromkeys(boxes))
    inner = [
        b for b in boxes if not any(o is not b and b.contains(o, tol=2) for o in boxes)
    ]
    return sorted(inner, key=lambda b: (b.y0, b.x0))


def frame_thickness(dark, box):
    """Thickness (px) of the left axis line, used to strip the frame."""
    col = dark[(box.y0 + box.y1) // 2, box.x0 : box.x0 + 15]
    t = 0
    for v in col:
        if not v:
            break
        t += 1
    return max(t, 1)


def components(mask):
    """Label 8-connected components; returns (labels, slices)."""
    labels, n = ndi.label(mask, structure=np.ones((3, 3), bool))
    return labels, ndi.find_objects(labels)
