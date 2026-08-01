#!/usr/bin/env python3
"""Render data/contributions.json into an animated contribution heatmap SVG.

GitHub strips <script> and inline styles from README markup, but it does render
SVG embedded through <img> and it does run CSS keyframes inside that SVG. So the
whole animation lives here: cells fade and pop in on a diagonal sweep, play once,
then freeze (animation-fill-mode: both, no iteration count).

Writes contrib-heatmap.svg.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

STATIC = os.environ.get("STATIC") == "1"  # frozen frame for local preview

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

# none -> level 4, plus a neon top end for the busiest days
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

CELL = 13
GAP = 2
STEP = CELL + GAP
PAD_X = 20
PAD_TOP = 58
LABEL_W = 28
WIDTH = 860  # matches portrait (370) + info card (490) so edges line up
DOW = {1: "Mon", 3: "Wed", 5: "Fri"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mono_w(text: str, size: float) -> float:
    """Width of a monospace run. Right-aligning by hand beats text-anchor here:
    some SVG rasterizers ignore the attribute and the label runs off the card."""
    return len(text) * size * 0.6


def level_of(day: dict) -> int:
    """Promote the very best days to the neon shade so the map has a peak."""
    if day["count"] >= 20:
        return 5
    return min(day["level"], 4)


def weeks(days: list[dict]) -> list[list[dict | None]]:
    """Bucket days into calendar weeks, Sunday first, padding the first week."""
    cols: list[list[dict | None]] = []
    col: list[dict | None] = []
    first_dow = datetime.strptime(days[0]["date"], "%Y-%m-%d").weekday()
    first_dow = (first_dow + 1) % 7  # Monday=0 -> Sunday=0
    col.extend([None] * first_dow)
    for d in days:
        col.append(d)
        if len(col) == 7:
            cols.append(col)
            col = []
    if col:
        col.extend([None] * (7 - len(col)))
        cols.append(col)
    return cols[-53:]


def main() -> int:
    payload = json.loads(DATA.read_text())
    cols = weeks(payload["days"])
    grid_w = len(cols) * STEP
    grid_x = PAD_X + LABEL_W
    height = PAD_TOP + 7 * STEP + 46

    parts: list[str] = []
    add = parts.append

    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="{payload["total"]} GitHub contributions by {esc(payload["user"])} '
        f'in the last year, current streak {payload["current_streak"]} days">'
    )
    anim = (
        ""
        if STATIC
        else (
            ".cell{opacity:0;animation:pop .5s ease-out both}"
            ".line{opacity:0;animation:fade .6s ease-out both}"
        )
    )
    add(
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace}"
        f"{anim}"
        "@keyframes pop{from{opacity:0;transform:translateY(-6px) scale(.4)}"
        "to{opacity:1;transform:translateY(0) scale(1)}}"
        "@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}"
        "@media (prefers-reduced-motion:reduce){"
        ".cell,.line{animation:none;opacity:1;transform:none}}"
        "</style>"
    )

    # card
    add(f'<rect width="{WIDTH}" height="{height}" rx="14" fill="#0d1117"/>')
    add(f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="14" fill="none" stroke="#21262d"/>')

    # terminal chrome
    add('<circle cx="26" cy="24" r="5" fill="#ff5f57"/>')
    add('<circle cx="44" cy="24" r="5" fill="#febc2e"/>')
    add('<circle cx="62" cy="24" r="5" fill="#28c840"/>')
    add(
        f'<text class="line" style="animation-delay:.05s" x="82" y="28" font-size="12" fill="#8b949e">'
        f'{esc(payload["user"])}@github ~ $ ./contributions.sh</text>'
    )
    stamp = f'updated {payload["generated_at"][:10]}'
    add(
        f'<text class="line" style="animation-delay:.1s" '
        f'x="{grid_x + grid_w - mono_w(stamp, 11):.0f}" y="28" '
        f'font-size="11" fill="#484f58">{stamp}</text>'
    )

    # month labels
    seen: set[str] = set()
    for i, col in enumerate(cols):
        first = next((d for d in col if d), None)
        if not first:
            continue
        month = first["date"][:7]
        if month in seen or int(first["date"][8:]) > 8:
            continue
        seen.add(month)
        label = MONTHS[int(first["date"][5:7]) - 1]
        add(
            f'<text class="line" style="animation-delay:{.3 + i * .012:.2f}s" '
            f'x="{grid_x + i * STEP}" y="{PAD_TOP - 8}" font-size="10" fill="#8b949e">{label}</text>'
        )

    # weekday labels
    for row, label in DOW.items():
        add(
            f'<text class="line" style="animation-delay:{.3 + row * .06:.2f}s" x="{PAD_X}" '
            f'y="{PAD_TOP + row * STEP + CELL - 2}" font-size="10" fill="#8b949e">{label}</text>'
        )

    # the grid, revealed on a diagonal sweep
    for i, col in enumerate(cols):
        for row, day in enumerate(col):
            if day is None:
                continue
            lvl = level_of(day)
            delay = 0.3 + (i * 0.014) + (row * 0.03)
            add(
                f'<rect class="cell" style="animation-delay:{delay:.2f}s" '
                f'x="{grid_x + i * STEP}" y="{PAD_TOP + row * STEP}" width="{CELL}" height="{CELL}" '
                f'rx="3" fill="{PALETTE[lvl]}"/>'
            )

    # footer stats
    fy = PAD_TOP + 7 * STEP + 24
    stats = (
        f'{payload["total"]:,} contributions in the last year'
        f' · streak {payload["current_streak"]}d'
        f' · best {payload["longest_streak"]}d'
        f' · peak {payload["best_day"]["count"]} on {payload["best_day"]["date"]}'
    )
    add(
        f'<text class="line" style="animation-delay:1.5s" x="{grid_x}" y="{fy}" '
        f'font-size="11" fill="#8b949e">{esc(stats)}</text>'
    )

    # legend, right-aligned to the grid edge
    less_w = mono_w("Less", 11)
    swatches = len(PALETTE) * 12
    lx = grid_x + grid_w - (less_w + 8 + swatches + 8 + mono_w("More", 11))
    add(
        f'<text class="line" style="animation-delay:1.55s" x="{lx:.0f}" y="{fy}" '
        f'font-size="11" fill="#8b949e">Less</text>'
    )
    sx = lx + less_w + 8
    for k, color in enumerate(PALETTE):
        add(
            f'<rect class="cell" style="animation-delay:{1.6 + k * .05:.2f}s" x="{sx + k * 12:.0f}" '
            f'y="{fy - 9}" width="10" height="10" rx="2" fill="{color}"/>'
        )
    add(
        f'<text class="line" style="animation-delay:1.9s" x="{sx + swatches + 8:.0f}" y="{fy}" '
        f'font-size="11" fill="#8b949e">More</text>'
    )

    add("</svg>")
    OUT.write_text("".join(parts) + "\n")
    print(f"wrote {OUT} ({len(cols)} weeks, {payload['total']} contributions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
