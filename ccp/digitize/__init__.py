"""Automatic digitizing of compressor performance curves from PDF documents.

Upload a full curve document and get every operating case back as curves that
``ccp.Impeller`` can load::

    from ccp.digitize import digitize_pdf

    doc = digitize_pdf("expected_performance_curves.pdf")
    for case in doc.cases:
        print(case.name, case.conditions, case.curve_pair())
    doc.save("digitized/")  # <case>-head.csv, <case>-eff.csv, digitized.json
    imp = doc.cases[0].impeller(suc=suc)

Plots drawn as vector graphics with a text layer (plotting software,
spreadsheet exports) are read from the PDF itself: frames and grid from the
line segments, tick labels and titles from the text, each speed line from its
polyline and its speed from the label printed at one of its ends (a speed, a
percent of the 100 % speed, or a legend letter). Plots embedded as images
(embedded raster images, scans) are read from the rendered page: plot
frames are found from the axis lines, both axes are calibrated from OCR'd
tick labels snapped to the grid, the y-axis title tells which curve it is
(head, efficiency, pressure ratio, discharge pressure or temperature, power),
the legend gives the speeds, and every speed line is traced on a skeleton of
the cleaned plot. Both give the same results; ``digitize_pdf(mode=...)``
forces one path. Requires the ``digitize`` extra (pypdfium2, scikit-image,
pytesseract) and the Tesseract OCR binary.
"""

from ._document import DigitizedCase, DigitizedDocument, DigitizedPlot, digitize_pdf

__all__ = ["digitize_pdf", "DigitizedDocument", "DigitizedCase", "DigitizedPlot"]
