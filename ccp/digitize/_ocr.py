"""Thin wrapper over Tesseract (via pytesseract) returning word boxes."""

import re
from dataclasses import dataclass

import numpy as np

__all__ = ["Word", "ocr_words", "parse_number", "ocr_available"]

_NUMBER = re.compile(r"^[-+]?\d+(?:[.,]\d+)?$")


@dataclass
class Word:
    text: str
    conf: float
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2

    def shifted(self, dx, dy, scale=1.0):
        return Word(
            self.text,
            self.conf,
            self.x0 / scale + dx,
            self.y0 / scale + dy,
            self.x1 / scale + dx,
            self.y1 / scale + dy,
        )


def ocr_available():
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def _prepare(img, scale, blur=0.0, binarize=None):
    from PIL import Image, ImageFilter

    im = Image.fromarray(np.asarray(img, dtype=np.uint8))
    if scale != 1.0:
        im = im.resize(
            (int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS
        )
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if binarize is not None:
        im = im.convert("L").point(lambda v: 255 if v > binarize else 0)
    return im


def ocr_words(
    img, psm=6, whitelist=None, scale=1.0, min_conf=0, blur=0.0, binarize=None
):
    """OCR an RGB or gray array, returning ``Word`` boxes in its pixel frame.

    ``scale`` upsamples the crop before OCR (helps low resolution sheets);
    ``blur`` (Gaussian radius, after scaling) smooths jagged low-dpi glyphs.
    The returned coordinates are mapped back to the input frame.
    """
    import pytesseract

    if img.size == 0:
        return []
    im = _prepare(img, scale, blur, binarize)
    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    data = pytesseract.image_to_data(
        im, config=config, output_type=pytesseract.Output.DICT
    )
    words = []
    for text, conf, left, top, width, height in zip(
        data["text"],
        data["conf"],
        data["left"],
        data["top"],
        data["width"],
        data["height"],
    ):
        text = text.strip()
        if not text or float(conf) < min_conf:
            continue
        words.append(
            Word(
                text,
                float(conf),
                left / scale,
                top / scale,
                (left + width) / scale,
                (top + height) / scale,
            )
        )
    return words


def ocr_text(img, psm=6, scale=1.0):
    """Plain text of a crop (lines joined with newlines)."""
    import pytesseract
    from PIL import Image

    if img.size == 0:
        return ""
    im = Image.fromarray(np.asarray(img, dtype=np.uint8))
    if scale != 1.0:
        im = im.resize(
            (int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS
        )
    return pytesseract.image_to_string(im, config=f"--psm {psm}")


def parse_number(text):
    """Parse a tick label; returns ``None`` when it is not a clean number."""
    t = text.strip().replace("O", "0").replace("o", "0")
    # axis labels never carry a leading zero: "075" is "0.75" with the
    # decimal point lost to OCR
    if re.fullmatch(r"0\d+", t):
        t = "0." + t[1:]
    if not _NUMBER.match(t):
        return None
    return float(t.replace(",", "."))
