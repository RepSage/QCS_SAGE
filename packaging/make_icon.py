# -*- coding: utf-8 -*-
"""Draws the QCS icon and writes sourceCode/qcs_icon.png (256 px) and
sourceCode/qcs_icon.ico (16-256 px, each size drawn natively, not resampled).

v14.1.1 (owner, 2026-11-12): the previous raster icon - unchanged since v5.0,
with no source - carried a straight seam at 75% of its height (a thin light
stripe, and a differently composited band below it). It could not be
retouched cleanly, so the icon is now a vector drawing with the original's
sampled geometry and colours: a rounded square (8..248, radius 48) with a
diagonal gradient from dark blue through teal to gold, three white sliders,
a faint inner outline, a lighter wave bottom-left and a translucent darker
circle bottom-right. There are no straight seams.

Wired in three places (packaging/README.md, 'Icons'): the EXE icon= and the
datas of QCS.spec, and SetupIconFile= of the installer.

Run with the packaging venv (PySide6 + Pillow), from the repository root:
    packaging\\v12_env\\Scripts\\python.exe packaging\\make_icon.py
"""
import io
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image  # noqa: E402
from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter,  # noqa: E402
                           QPainterPath, QPen)
from PySide6.QtWidgets import QApplication  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "sourceCode"
CANVAS = 256
BOX = QRectF(8, 8, 240, 240)
RADIUS = 48
STOPS = [(0.00, (36, 82, 132)), (0.30, (9, 116, 142)), (0.50, (12, 150, 160)),
         (0.68, (88, 163, 116)), (0.85, (165, 160, 66)), (1.00, (176, 132, 36))]
SLIDERS = ((76, 154), (128, 102), (180, 146))       # (track y, knob x) on the 256 canvas
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw_icon(size):
    """The icon at `size` px, drawn in 256-px canvas units."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / CANVAS, size / CANVAS)
    shape = QPainterPath()
    shape.addRoundedRect(BOX, RADIUS, RADIUS)
    grad = QLinearGradient(QPointF(8, 8), QPointF(248, 248))
    for t, rgb in STOPS:
        grad.setColorAt(t, QColor(*rgb))
    p.fillPath(shape, QBrush(grad))
    p.setClipPath(shape)
    wave = QPainterPath(QPointF(0, 186))
    wave.cubicTo(QPointF(45, 176), QPointF(85, 182), QPointF(120, 198))
    wave.cubicTo(QPointF(150, 212), QPointF(185, 214), QPointF(256, 196))
    wave.lineTo(256, 256)
    wave.lineTo(0, 256)
    wave.closeSubpath()
    p.fillPath(wave, QColor(255, 255, 255, 26))
    p.setBrush(QColor(0, 0, 0, 28))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(232, 262), 128, 128)
    p.setClipping(False)
    p.setPen(QPen(QColor(255, 255, 255, 60), 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(BOX.adjusted(5, 5, -5, -5), RADIUS - 5, RADIUS - 5)
    p.setPen(QPen(QColor("white"), 15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for y, knob_x in SLIDERS:
        p.drawLine(QPointF(57, y), QPointF(198, y))
        p.drawLine(QPointF(knob_x, y - 18), QPointF(knob_x, y + 18))
    p.end()
    return img


def to_pil(qimage):
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    qimage.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def main():
    QApplication.instance() or QApplication(sys.argv)
    images = {s: to_pil(draw_icon(s)) for s in ICO_SIZES}
    images[256].save(SRC / "qcs_icon.png")
    images[256].save(SRC / "qcs_icon.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES],
                     append_images=[images[s] for s in ICO_SIZES if s != 256])
    check = Image.open(SRC / "qcs_icon.ico")
    print("qcs_icon.png", (SRC / "qcs_icon.png").stat().st_size, "bytes;",
          "qcs_icon.ico sizes", sorted(check.info["sizes"]))


if __name__ == "__main__":
    main()
