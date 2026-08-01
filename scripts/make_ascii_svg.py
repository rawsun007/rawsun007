#!/usr/bin/env python3
"""Turn source-photo.jpg into an animated ASCII portrait SVG.

Pillow only, no rembg or OpenCV: the background is knocked out with a levels
curve (anything above the highlight point becomes pure white, so a busy wall
reduces to spaces and the subject isolates on its own).

Each row is drawn once and revealed by a SMIL clip-path wipe, staggered top to
bottom so the portrait types itself in, then freezes. SMIL is the one animation
GitHub reliably runs inside an <img>-embedded SVG.

Writes ascii-portrait.svg. Run by hand when the photo changes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-photo.jpg"
OUT = ROOT / "ascii-portrait.svg"
STATIC = os.environ.get("STATIC") == "1"

# bright (sparse) -> dark (dense)
RAMP = " .`:-=+*cs#%@"

COLS = 96
CHAR_W = 3.85
CHAR_H = 7.4
FONT_SIZE = 7.6
PAD = 20

# levels: below SHADOW is solid black, above HIGHLIGHT is dropped to white
SHADOW = 0.10
HIGHLIGHT = 0.80
GAMMA = 0.85


def prep(path: Path) -> Image.Image:
    im = Image.open(path).convert("L")
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(1.35)
    return im


def to_rows(im: Image.Image) -> list[str]:
    rows_n = max(1, round(COLS * im.height / im.width * (CHAR_W / CHAR_H)))
    small = im.resize((COLS, rows_n), Image.LANCZOS)
    px = small.load()

    rows: list[str] = []
    for y in range(rows_n):
        line = []
        for x in range(COLS):
            v = px[x, y] / 255.0
            v = (v - SHADOW) / (HIGHLIGHT - SHADOW)
            v = min(max(v, 0.0), 1.0) ** GAMMA
            idx = round((1.0 - v) * (len(RAMP) - 1))
            line.append(RAMP[idx])
        rows.append("".join(line).rstrip())
    return rows


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")

    rows = to_rows(prep(SRC))
    width = round(PAD * 2 + COLS * CHAR_W)
    height = round(PAD * 2 + len(rows) * CHAR_H) + 8

    parts: list[str] = []
    add = parts.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="ASCII art portrait of Roshan Ramani, typing itself in line by line">'
    )
    add(
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace;"
        f"font-size:{FONT_SIZE}px;white-space:pre}}"
        f"{theme.css()}"
        "</style>"
    )
    add(f'<rect class="card" width="{width}" height="{height}" rx="14"/>')
    add(f'<rect class="stroke" x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="none"/>')

    inner = width - PAD * 2
    add("<defs>")
    for i, row in enumerate(rows):
        if not row:
            continue
        if STATIC:
            add(f'<clipPath id="w{i}"><rect x="{PAD}" y="0" width="{inner}" height="{height}"/></clipPath>')
            continue
        begin = 0.15 + i * 0.035
        add(
            f'<clipPath id="w{i}"><rect x="{PAD}" y="0" width="0" height="{height}">'
            f'<animate attributeName="width" from="0" to="{inner}" begin="{begin:.2f}s" '
            f'dur="0.35s" fill="freeze"/></rect></clipPath>'
        )
    add("</defs>")

    for i, row in enumerate(rows):
        if not row:
            continue
        y = PAD + (i + 1) * CHAR_H
        add(
            f'<text class="ascii" clip-path="url(#w{i})" x="{PAD}" y="{y:.1f}" '
            f'textLength="{len(row) * CHAR_W:.1f}" lengthAdjust="spacing">{esc(row)}</text>'
        )

    add("</svg>")
    OUT.write_text("".join(parts) + "\n")
    print(f"wrote {OUT} ({COLS}x{len(rows)} chars, {width}x{height}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
