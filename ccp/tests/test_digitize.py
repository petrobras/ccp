"""Tests for ccp.digitize on a synthetic vendor-style curve sheet.

The sheet is drawn with pypdfium2 (frame, dashed grid, tick labels, rotated axis
titles, legend box, red surge line, curve letters, reference-point square and
the suction-conditions block), so the expected curves are known exactly and no
vendor document is needed.
"""

import ctypes
import json
import math

import numpy as np
import pytest

pdfium = pytest.importorskip("pypdfium2")
pdfium_c = pytest.importorskip("pypdfium2.raw")
pytest.importorskip("skimage")
pytest.importorskip("pytesseract")

from ccp.digitize import digitize_pdf  # noqa: E402
from ccp.digitize._ocr import ocr_available  # noqa: E402

pytestmark = pytest.mark.skipif(not ocr_available(), reason="tesseract not installed")

# ------------------------------------------------------------ drawing helpers


class Point(tuple):
    """Page point (top-left origin, y down) that adds offsets like a vector."""

    def __new__(cls, x, y):
        return super().__new__(cls, (x, y))

    x = property(lambda self: self[0])
    y = property(lambda self: self[1])

    def __add__(self, other):
        return Point(self[0] + other[0], self[1] + other[1])


class Rect:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.width, self.height = x1 - x0, y1 - y0


class Sheet:
    """A one-page PDF drawn with pypdfium2, in top-left page coordinates."""

    def __init__(self, width=595, height=842):
        self.pdf = pdfium.PdfDocument.new()
        self.page = self.pdf.new_page(width, height)
        self.height = height
        self.font = pdfium_c.FPDFText_LoadStandardFont(self.pdf, b"Helvetica")

    def _y(self, y):
        return self.height - y

    @staticmethod
    def _rgb(color):
        return [round(255 * c) for c in color]

    def _stroke(self, obj, color, width, dashes=None, fill=None):
        pdfium_c.FPDFPageObj_SetStrokeColor(obj, *self._rgb(color), 255)
        pdfium_c.FPDFPageObj_SetStrokeWidth(obj, width)
        if dashes:
            array = (ctypes.c_float * len(dashes))(*dashes)
            pdfium_c.FPDFPageObj_SetDashArray(obj, array, len(dashes), 0)
        if fill is not None:
            pdfium_c.FPDFPageObj_SetFillColor(obj, *self._rgb(fill), 255)
        mode = pdfium_c.FPDF_FILLMODE_ALTERNATE if fill is not None else 0
        pdfium_c.FPDFPath_SetDrawMode(obj, mode, True)
        pdfium_c.FPDFPage_InsertObject(self.page, obj)

    def draw_polyline(self, points, color=(0, 0, 0), width=1, dashes=None):
        (x, y), *rest = points
        obj = pdfium_c.FPDFPageObj_CreateNewPath(x, self._y(y))
        for x, y in rest:
            pdfium_c.FPDFPath_LineTo(obj, x, self._y(y))
        self._stroke(obj, color, width, dashes)

    def draw_line(self, p0, p1, color=(0, 0, 0), width=1, dashes=None):
        self.draw_polyline([p0, p1], color, width, dashes)

    def draw_rect(self, r, color=(0, 0, 0), width=1, fill=None):
        obj = pdfium_c.FPDFPageObj_CreateNewRect(r.x0, self._y(r.y1), r.width, r.height)
        self._stroke(obj, color, width, fill=fill)

    def insert_text(self, point, text, fontsize=11, rotate=0, color=(0, 0, 0)):
        """Text with its baseline starting at ``point``, turned ``rotate``
        degrees counter-clockwise."""
        obj = pdfium_c.FPDFPageObj_CreateTextObj(self.pdf, self.font, fontsize)
        buffer = ctypes.create_string_buffer((text + "\0").encode("utf-16-le"))
        pdfium_c.FPDFText_SetText(obj, ctypes.cast(buffer, pdfium_c.FPDF_WIDESTRING))
        pdfium_c.FPDFPageObj_SetFillColor(obj, *self._rgb(color), 255)
        a = math.radians(rotate)
        cos, sin = math.cos(a), math.sin(a)
        x, y = point
        pdfium_c.FPDFPageObj_Transform(obj, cos, sin, -sin, cos, x, self._y(y))
        pdfium_c.FPDFPage_InsertObject(self.page, obj)

    def save(self, path):
        self.page.gen_content()
        self.pdf.save(str(path))


SPEEDS = [12000, 11000, 9500, 8000]
N0 = 12000
Q_SURGE, Q_CHOKE = 6000, 11000  # m3/h at N0


def head(q, n):
    r = n / N0
    qn = q / r
    return r**2 * (220 - 60 * (max(qn - Q_SURGE, 0) / (Q_CHOKE - Q_SURGE)) ** 2.2)


def eff(q, n):
    r = n / N0
    qn = q / r
    x = (qn - 8000) / 4000
    return 0.84 - 0.2 * x**2 - 0.25 * max(x, 0) ** 4


def flow_range(n):
    r = n / N0
    return Q_SURGE * r, Q_CHOKE * r


class Axes:
    def __init__(self, page, rect, xlim, ylim):
        self.page, self.rect, self.xlim, self.ylim = page, rect, xlim, ylim

    def p(self, x, y):
        r = self.rect
        px = r.x0 + (x - self.xlim[0]) / (self.xlim[1] - self.xlim[0]) * r.width
        py = r.y1 - (y - self.ylim[0]) / (self.ylim[1] - self.ylim[0]) * r.height
        return Point(px, py)

    def frame(self, xticks, yticks, ytitle, xtitle):
        pg, r = self.page, self.rect
        for x in xticks:
            pg.draw_line(
                self.p(x, self.ylim[0]),
                self.p(x, self.ylim[1]),
                color=(0.3, 0.3, 0.3),
                width=0.4,
                dashes=(1, 2),
            )
            s = f"{x:g}"
            pg.insert_text(self.p(x, self.ylim[0]) + (-2.1 * len(s), 10), s, fontsize=7)
        for y in yticks:
            pg.draw_line(
                self.p(self.xlim[0], y),
                self.p(self.xlim[1], y),
                color=(0.3, 0.3, 0.3),
                width=0.4,
                dashes=(1, 2),
            )
            s = f"{y:g}"
            pg.insert_text(
                self.p(self.xlim[0], y) + (-4 - 4 * len(s), 2.5), s, fontsize=7
            )
        pg.draw_rect(r, color=(0, 0, 0), width=0.8)
        pg.insert_text(Point(r.x0 - 34, r.y1 - 20), ytitle, fontsize=7, rotate=90)
        pg.insert_text(Point(r.x0 + r.width * 0.3, r.y1 + 22), xtitle, fontsize=7)

    def legend(self):
        r = self.rect
        box = Rect(r.x1 - 110, r.y0 + 6, r.x1 - 6, r.y0 + 12 + 10 * (len(SPEEDS) + 1))
        self.page.draw_rect(box, color=(0, 0, 0), width=0.6, fill=(1, 1, 1))
        for i, n in enumerate(SPEEDS):
            y = box.y0 + 10 + 10 * i
            self.page.draw_line(
                (box.x0 + 4, y - 2), (box.x0 + 30, y - 2), color=(0, 0, 0), width=1
            )
            self.page.insert_text((box.x0 + 34, y), f"{'ABCD'[i]}  {n} RPM", fontsize=7)
        y = box.y0 + 10 + 10 * len(SPEEDS)
        self.page.draw_line(
            (box.x0 + 4, y - 2), (box.x0 + 30, y - 2), color=(1, 0, 0), width=1
        )
        self.page.insert_text((box.x0 + 34, y), "Surge Line", fontsize=7)

    def curve(self, f, n, letter):
        q0, q1 = flow_range(n)
        q = np.linspace(q0, q1, 80)
        pts = [self.p(qi, f(qi, n)) for qi in q]
        self.page.draw_polyline(pts, color=(0.1, 0.1, 0.1), width=1.1)
        self.page.insert_text(pts[-1] + (3, 6), letter, fontsize=8)
        return pts


def make_sheet(path):
    page = Sheet()
    page.insert_text((60, 40), "TEST-1 CASE A", fontsize=10)
    top = Axes(page, Rect(140, 60, 520, 330), (0, 14000), (40, 240))
    top.frame(
        range(0, 14001, 2000),
        range(40, 241, 20),
        "POLYTROPIC HEAD  kJ/kg",
        "INLET VOLUME FLOW  m3/h",
    )
    surge = []
    for i, n in enumerate(SPEEDS):
        surge.append(top.curve(head, n, "ABCD"[i])[0])
    page.draw_polyline(surge, color=(1, 0, 0), width=1.2)
    # reference-point square on the top line
    c = top.p(9000, head(9000, SPEEDS[0]))
    page.draw_rect(Rect(c.x - 3, c.y - 3, c.x + 3, c.y + 3), color=(0, 0, 0), width=0.6)
    top.legend()
    bot = Axes(page, Rect(140, 380, 520, 650), (0, 14000), (0.6, 0.9))
    bot.frame(
        range(0, 14001, 2000),
        [round(0.6 + 0.05 * k, 2) for k in range(7)],
        "POLYTROPIC EFFICIENCY  fraction",
        "INLET VOLUME FLOW  m3/h",
    )
    for i, n in enumerate(SPEEDS):
        bot.curve(eff, n, "ABCD"[i])
    bot.legend()
    lines = [
        "SUCTION CONDITIONS",
        "GAS HANDLED : TEST GAS",
        "MOLECULAR WEIGHT : 20.50 g/mol",
        "INLET PRESSURE : 12.50 BAR-A",
        "INLET TEMPERATURE : 32.50 C",
    ]
    for k, t in enumerate(lines):
        page.insert_text((60, 690 + 11 * k), t, fontsize=8)
    page.save(path)


@pytest.fixture(scope="module", params=["raster", "auto"])
def digitized(request, tmp_path_factory):
    """The sheet read from its image (OCR) and from its vector content."""
    path = tmp_path_factory.mktemp("digitize") / "sheet.pdf"
    make_sheet(path)
    doc = digitize_pdf(path, mode=request.param)
    expected = "raster" if request.param == "raster" else "vector"
    assert {p.source for p in doc.plots if p.param} == {expected}
    return doc


def test_case_found(digitized):
    assert len(digitized.cases) == 1
    case = digitized.cases[0]
    assert "CASE A" in case.name
    assert case.conditions["p"] == [12.5, "bar"]
    assert case.conditions["T"] == [32.5, "degC"]
    assert case.speeds == SPEEDS
    assert case.curve_pair() == ("head", "eff")
    assert case.plots["head"].units == "kJ/kg"
    assert case.plots["eff"].units == "dimensionless"
    assert case.plots["head"].flow_units == "m³/h"


@pytest.mark.parametrize("param, func, span", [("head", head, 200), ("eff", eff, 0.3)])
def test_curves_match(digitized, param, func, span):
    plot = digitized.cases[0].plots[param]
    curves = plot.curves_dict()
    assert sorted(int(k) for k in curves) == sorted(SPEEDS)
    for sp, c in curves.items():
        n = float(sp)
        q = np.asarray(c["x1"])
        y = np.asarray(c["x2"])
        expected = np.array([func(qi, n) for qi in q])
        # within 0.5 % of the axis span everywhere along the line
        assert np.max(np.abs(y - expected)) < 0.005 * span, (param, sp)
        q0, q1 = flow_range(n)
        assert abs(q[0] - q0) < 0.03 * (q1 - q0), (param, sp, "surge end")
        assert abs(q[-1] - q1) < 0.03 * (q1 - q0), (param, sp, "choke end")


def test_impeller_and_csv(digitized, tmp_path):
    import ccp

    case = digitized.cases[0]
    folder = digitized.save(tmp_path / "out")
    slug = case.slug
    assert (folder / f"{slug}-head.csv").exists()
    assert (folder / f"{slug}-eff.csv").exists()
    kw = case.load_kwargs()
    assert kw["head_units"] == "kJ/kg"
    assert kw["flow_units"] == "m³/h"
    from ccp.data_io.read_csv import read_data_from_engauge_csv

    back = read_data_from_engauge_csv(folder / f"{slug}-head.csv")
    assert sorted(back) == sorted(str(s) for s in SPEEDS)
    del ccp


def test_round_trip_and_calibration(digitized):
    from ccp.digitize import DigitizedDocument

    data = digitized.to_dict()
    json.loads(json.dumps(data))  # JSON-ready
    back = DigitizedDocument.from_dict(data)
    case, case_back = digitized.cases[0], back.cases[0]
    assert case_back.name == case.name
    assert case_back.speeds == case.speeds
    assert case_back.curve_pair() == case.curve_pair()
    assert case_back.plots["head"] is back.plot(case.plots["head"].id)
    assert case_back.plots["head"].curves_dict() == case.plots["head"].curves_dict()
    plot = back.plot(case.plots["eff"].id)
    c = plot.curves[0]
    x, y = plot.to_pixels(c["flow"], c["value"])
    flow, value = plot.to_data(x, y)
    np.testing.assert_allclose(flow, c["flow"])
    np.testing.assert_allclose(value, c["value"])
    assert plot.to_engauge_csv().startswith("x,")


# ----------------------------------------------------------------- line labels


def make_labelled_sheet(path):
    """Sheet with speeds printed at the choke end of each line, a solid major
    grid, rotated x tick labels, a rated point with coloured guide lines and
    values, and a conditions table below the plot."""
    page = Sheet()
    page.insert_text((200, 40), "TEST-2 Case B", fontsize=10)
    ax = Axes(page, Rect(140, 80, 520, 380), (0, 14000), (40, 240))
    r = ax.rect
    for x in range(0, 14001, 1000):
        major = x % 2000 == 0
        page.draw_line(
            ax.p(x, 40),
            ax.p(x, 240),
            color=(0, 0, 0) if major else (0.83, 0.83, 0.83),
            width=0.5 if major else 0.3,
        )
        if major:
            s = f"{x:.2f}"
            page.insert_text(
                ax.p(x, 40) + (3, 6 + 4.2 * len(s)), s, fontsize=7, rotate=90
            )
    for y in range(40, 241, 10):
        major = y % 20 == 0
        page.draw_line(
            ax.p(0, y),
            ax.p(14000, y),
            color=(0, 0, 0) if major else (0.83, 0.83, 0.83),
            width=0.5 if major else 0.3,
        )
        if major:
            s = f"{y}"
            page.insert_text(ax.p(0, y) + (-4 - 4 * len(s), 2.5), s, fontsize=7)
    page.draw_rect(r, color=(0, 0, 0), width=0.8)
    page.insert_text(
        Point(r.x0 - 40, r.y1 - 40),
        "Head, kJ/kg",
        fontsize=7,
        rotate=90,
    )
    page.insert_text(Point(r.x0 + 150, r.y1 + 48), "Inlet flow, m³/h", fontsize=7)
    surge, choke = [], []
    for n in SPEEDS:
        q0, q1 = flow_range(n)
        q = np.linspace(q0, q1, 60)
        pts = [ax.p(qi, head(qi, n)) for qi in q]
        page.draw_polyline(pts, color=(0, 0, 0), width=0.6)
        page.insert_text(pts[-1] + (2, 3), f"{n}", fontsize=6)
        surge.append(pts[0])
        choke.append(pts[-1])
    page.draw_polyline(surge, color=(0, 0, 0), width=0.6)
    page.draw_polyline(choke, color=(0, 0, 0), width=0.6)
    # rated point on the 11000 RPM line, with red guides and values
    q_r = 8500
    h_r = head(q_r, 11000)
    c = ax.p(q_r, h_r)
    page.draw_line(ax.p(0, h_r), c, color=(1, 0, 0), width=0.6, dashes=(3, 2))
    page.draw_line(ax.p(q_r, 40), c, color=(1, 0, 0), width=0.6, dashes=(3, 2))
    page.insert_text(ax.p(0, h_r) + (12, -2), f"{h_r:.2f}", fontsize=6, color=(1, 0, 0))
    page.insert_text(
        ax.p(q_r, 40) + (-2, -30), f"{q_r:.2f}", fontsize=6, color=(1, 0, 0), rotate=90
    )
    rows = [
        ("100% Speed", "12000", "RPM", "", ""),
        ("Ts", "30.00", "°C", "Ps", "2000 kPaA"),
        ("Flow", "100.0", "m³/min", "MW", "20.00"),
        ("Zs", "0.950", "", "Pd", "8000 kPaA"),
    ]
    for k, row in enumerate(rows):
        for x, t in zip((60, 120, 160, 200, 240), row):
            page.insert_text((x, 700 + 11 * k), t, fontsize=8)
    page.save(path)


@pytest.fixture(scope="module")
def labelled(tmp_path_factory):
    path = tmp_path_factory.mktemp("digitize") / "labelled.pdf"
    make_labelled_sheet(path)
    return digitize_pdf(path)


def test_line_labels(labelled):
    assert len(labelled.cases) == 1
    case = labelled.cases[0]
    assert "Case B" in case.name
    assert case.conditions["p"] == [2000.0, "kPa"]
    assert case.conditions["T"] == [30.0, "degC"]
    assert case.conditions["speed"] == 12000
    assert case.speeds == SPEEDS
    plot = case.plots["head"]
    assert plot.source == "vector" and plot.labeled
    assert plot.flow_units == "m³/h"
    assert len(plot.envelopes) == 2  # surge and choke lines kept apart
    for sp, c in plot.curves_dict().items():
        n = float(sp)
        q = np.asarray(c["x1"])
        y = np.asarray(c["x2"])
        expected = np.array([head(qi, n) for qi in q])
        # read from the vector drawing: exact to the plotting precision
        assert np.max(np.abs(y - expected)) < 1e-3 * 200, sp
        q0, q1 = flow_range(n)
        assert abs(q[0] - q0) < 1e-3 * q1 and abs(q[-1] - q1) < 1e-3 * q1
    assert plot.reference == pytest.approx((8500, head(8500, 11000)), abs=0.01)
    assert any("rated point at 11000 RPM" in m for m in plot.notes)


def test_rounded_tick_labels():
    from ccp.digitize._axes import _equally_spaced

    labels = [0.6, 0.613, 0.625, 0.638, 0.65, 0.663, 0.675, 0.688, 0.7, 0.713]
    points = _equally_spaced([(v, 100 + 78.4 * i) for i, v in enumerate(labels)])
    values = [v for v, _ in points]
    np.testing.assert_allclose(values, [0.6 + 0.0125 * i for i in range(10)])


def test_conditions_table():
    from ccp.digitize._document import parse_conditions, vote_conditions

    text = "Ts 30.00 °C Ps 2000 kPaA\nMW 20.00\nZs 0.950 Pd 8000 kPaA\n"
    text += "Recycle Flow=40000 kg/h\nFlow 100.0 m³/min\n100% Speed 12500 RPM"
    cond = parse_conditions(text)
    assert cond["p"] == [2000.0, "kPa"] and cond["T"] == [30.0, "degC"]
    assert cond["flow"] == [100.0, "m³/min"] and cond["speed"] == 12500
    # an OCR reading that lost the decimal point is outvoted and implausible
    voted = vote_conditions([dict(cond, T=[3000.0, "degC"]), cond])
    assert voted["T"] == [30.0, "degC"]
