#!/usr/bin/env python3
"""Render info-card.svg: a neofetch-style terminal panel next to the portrait.

Lines fade and slide in one after another, like output printing. Static content,
so this is run by hand when the facts change, not by the daily workflow.
Set STATIC=1 to emit a frozen frame for local preview.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme

OUT = Path(__file__).resolve().parent.parent / "info-card.svg"
STATIC = os.environ.get("STATIC") == "1"

WIDTH = 490
PAD = 22
LINE = 20
KEY_W = 96

# (key, value). key None renders a full-width dim line, "" renders a spacer.
ROWS: list[tuple[str | None, str]] = [
    ("user", "Roshan Ramani  ~  Surat, India"),
    (None, "-" * 46),
    ("now", "Web developer and automation engineer"),
    ("focus", "Privacy-first browser tools, macOS apps"),
    ("shipping", "ClaudeNotch, MetaStrip, GodPrompter"),
    ("", ""),
    ("langs", "Swift, Python, TypeScript, JavaScript, Bash"),
    ("frontend", "React, Next.js, Tailwind, SwiftUI, AppKit"),
    ("automate", "n8n, GitHub Actions, Jotform, Supabase"),
    ("agents", "Claude Code, Codex, Cursor  (human in loop)"),
    ("models", "Claude, Gemini, Grok, DeepSeek, OpenRouter"),
    ("", ""),
    ("n8n", "30+ templates, 32,000+ uses"),
    ("macos", "ClaudeNotch, Swift + AppKit, Homebrew cask"),
    ("policy", "No upload, no server, no account"),
    ("", ""),
    ("status", "Open to internships and startup roles"),
    ("links", "roshan-ramani.vercel.app  /  @roshanramani007"),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    body_top = 62
    height = body_top + len(ROWS) * LINE + 24

    parts: list[str] = []
    add = parts.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="Terminal card: Roshan Ramani, web developer and automation engineer '
        f'in Surat, India, open to internships and startup roles">'
    )

    anim = "" if STATIC else ".line{opacity:0;animation:print .45s ease-out both}"
    add(
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace}"
        f"{theme.css(levels=True)}"
        f"{anim}"
        "@keyframes print{from{opacity:0;transform:translateX(-8px)}"
        "to{opacity:1;transform:translateX(0)}}"
        "@media (prefers-reduced-motion:reduce){.line{animation:none;opacity:1;transform:none}}"
        "</style>"
    )

    add(f'<rect class="card" width="{WIDTH}" height="{height}" rx="14"/>')
    add(f'<rect class="stroke" x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="14" fill="none"/>')

    # title bar
    add('<circle cx="24" cy="23" r="5" fill="#ff5f57"/>')
    add('<circle cx="42" cy="23" r="5" fill="#febc2e"/>')
    add('<circle cx="60" cy="23" r="5" fill="#28c840"/>')
    add(
        f'<text class="line d" style="animation-delay:.05s" x="80" y="27" font-size="12">'
        "roshan@github ~ $ whoami</text>"
    )
    add(f'<line class="rule" x1="0" y1="44" x2="{WIDTH}" y2="44"/>')

    for i, (key, value) in enumerate(ROWS):
        if key == "" and value == "":
            continue
        y = body_top + i * LINE
        delay = 0.25 + i * 0.07
        style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
        if key is None:
            add(f'<text class="line f"{style} x="{PAD}" y="{y}" font-size="12">{esc(value)}</text>')
            continue
        cls = "a" if key == "status" else "t"
        add(
            f'<g class="line"{style}>'
            f'<text class="k" x="{PAD}" y="{y}" font-size="12">{esc(key)}</text>'
            f'<text class="d" x="{PAD + KEY_W - 12}" y="{y}" font-size="12">:</text>'
            f'<text class="{cls}" x="{PAD + KEY_W}" y="{y}" font-size="12">{esc(value)}</text>'
            "</g>"
        )

    # palette strip, the neofetch signature
    sy = body_top + len(ROWS) * LINE - 2
    swatches = [f"l{i}" for i in range(len(theme.DARK["levels"]))] + ["a", "t"]
    for k, cls in enumerate(swatches):
        style = "" if STATIC else f' style="animation-delay:{1.5 + k * .05:.2f}s"'
        add(
            f'<rect class="line {cls}"{style} x="{PAD + k * 18}" y="{sy}" width="14" height="10" rx="2"/>'
        )

    add("</svg>")
    OUT.write_text("".join(parts) + "\n")
    print(f"wrote {OUT} ({WIDTH}x{height}{', static' if STATIC else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
