#!/usr/bin/env python3
"""Render data/shiplog.json into an animated ship-log SVG.

Same rules as the heatmap: all animation inside the file, plays once, freezes,
and gives up entirely under prefers-reduced-motion. Rows print one after another
like a log scrolling past.

Writes shiplog.svg.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme

STATIC = os.environ.get("STATIC") == "1"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "shiplog.json"
OUT = ROOT / "shiplog.svg"

WIDTH = 860
PAD = 20
HEAD = 58
ROW = 22
FONT = 12
CHAR = FONT * 0.6          # monospace advance, for laying columns out by hand
AGE_W = 46
REPO_W = 150

# One glyph per kind of thing, so the column reads at a glance.
MARK = {"release": "▲", "commit": "•", "repo": "★", "merge": "⇢", "star": "☆"}
# Releases are the thing worth noticing; everything else recedes.
CLASS = {"release": "k", "commit": "d", "repo": "a", "merge": "d", "star": "a"}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def age(iso: str, now: datetime) -> str:
    """Relative and short: "2h", "3d". A log wants elapsed time, not a date."""
    try:
        when = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    secs = max(0, (now - when).total_seconds())
    if secs < 3600:
        return f"{int(secs // 60)}m"
    if secs < 86_400:
        return f"{int(secs // 3600)}h"
    if secs < 86_400 * 30:
        return f"{int(secs // 86_400)}d"
    return f"{int(secs // (86_400 * 30))}mo"


def clip(text: str, room: float) -> str:
    """Cut to what fits, with an ellipsis, since SVG text does not wrap."""
    limit = int(room / CHAR)
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "…"


def main() -> int:
    payload = json.loads(DATA.read_text())
    entries = payload["entries"]
    now = datetime.now(UTC)

    height = HEAD + len(entries) * ROW + 30
    text_x = PAD + 18 + AGE_W + REPO_W
    text_room = WIDTH - PAD - text_x

    parts: list[str] = []
    add = parts.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="The last {len(entries)} things {esc(payload["user"])} shipped, '
        f'newest first, refreshed daily">'
    )
    anim = "" if STATIC else ".line{opacity:0;animation:print .4s ease-out both}"
    add(
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace}"
        f"{theme.css()}"
        f"{anim}"
        "@keyframes print{from{opacity:0;transform:translateX(-6px)}"
        "to{opacity:1;transform:translateX(0)}}"
        "@media (prefers-reduced-motion:reduce){.line{animation:none;opacity:1;transform:none}}"
        "</style>"
    )

    add(f'<rect class="card" width="{WIDTH}" height="{height}" rx="14"/>')
    add(f'<rect class="stroke" x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="14" fill="none"/>')

    add('<circle cx="26" cy="24" r="5" fill="#ff5f57"/>')
    add('<circle cx="44" cy="24" r="5" fill="#febc2e"/>')
    add('<circle cx="62" cy="24" r="5" fill="#28c840"/>')
    add(
        f'<text class="line d" style="animation-delay:.05s" x="82" y="28" font-size="12">'
        f'{esc(payload["user"])}@github ~ $ git log --oneline --all</text>'
    )
    stamp = f'updated {payload["generated_at"][:10]}'
    add(
        f'<text class="line f" style="animation-delay:.1s" '
        f'x="{WIDTH - PAD - len(stamp) * 11 * 0.6:.0f}" y="28" font-size="11">{stamp}</text>'
    )
    add(f'<line class="rule" x1="0" y1="42" x2="{WIDTH}" y2="42"/>')

    for i, e in enumerate(entries):
        y = HEAD + i * ROW
        delay = 0.2 + i * 0.09
        style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
        kind = e.get("kind", "commit")
        add(
            f'<g class="line"{style}>'
            f'<text class="{CLASS.get(kind, "d")}" x="{PAD}" y="{y}" font-size="{FONT}">'
            f'{MARK.get(kind, "•")}</text>'
            f'<text class="f" x="{PAD + 18}" y="{y}" font-size="{FONT}">{age(e["at"], now)}</text>'
            f'<text class="k" x="{PAD + 18 + AGE_W}" y="{y}" font-size="{FONT}">'
            f'{esc(clip(e["repo"], REPO_W - 10))}</text>'
            f'<text class="{"t" if kind == "release" else "d"}" x="{text_x}" y="{y}" '
            f'font-size="{FONT}">{esc(clip(e["text"], text_room))}</text>'
            "</g>"
        )

    add(
        f'<text class="line f" style="animation-delay:{0.2 + len(entries) * 0.09 + 0.1:.2f}s" '
        f'x="{PAD}" y="{height - 12}" font-size="11">'
        f'releases and commits, newest first, refreshed daily by a workflow in this repo</text>'
    )
    add("</svg>")

    OUT.write_text("".join(parts) + "\n")
    print(f"wrote {OUT} ({len(entries)} rows, {WIDTH}x{height}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
