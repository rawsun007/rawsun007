"""Shared palette and theme CSS for the generated SVGs.

The cards used to be hardcoded dark, which looks pasted-on for anyone browsing
GitHub in light mode. An SVG embedded through <img> still gets the viewer's
prefers-color-scheme, and CSS beats presentation attributes, so every colour is
applied by class here and re-declared inside a media query. Dark stays the
default, light is the override.

Note it follows the operating system preference, not the GitHub theme picker,
so a light OS with GitHub forced to dark sees light cards.
"""

from __future__ import annotations

DARK = {
    "bg": "#0d1117",
    "border": "#21262d",
    "fg": "#c9d1d9",
    "dim": "#8b949e",
    "faint": "#484f58",
    "rule": "#21262d",
    "key": "#39d353",
    "accent": "#fb4903",
    "ascii": "#8b949e",
    # none -> level 4, then a brighter top end for the busiest days
    "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"],
}

LIGHT = {
    "bg": "#ffffff",
    "border": "#d1d9e0",
    "fg": "#1f2328",
    "dim": "#59636e",
    "faint": "#818b98",
    "rule": "#d1d9e0",
    "key": "#1a7f37",
    "accent": "#bc4c00",
    "ascii": "#4b5563",
    "levels": ["#ebedf0", "#aceebb", "#4ac26b", "#2da44e", "#116329", "#04381f"],
}

# class name -> which palette key fills it
FILLS = {
    "card": "bg",
    "t": "fg",
    "d": "dim",
    "f": "faint",
    "k": "key",
    "a": "accent",
    "ascii": "ascii",
}


def _rules(pal: dict, extra_classes: bool) -> str:
    out = [f".{cls}{{fill:{pal[key]}}}" for cls, key in FILLS.items()]
    out.append(f".stroke{{stroke:{pal['border']}}}")
    out.append(f".rule{{stroke:{pal['rule']}}}")
    if extra_classes:
        out += [f".l{i}{{fill:{color}}}" for i, color in enumerate(pal["levels"])]
    return "".join(out)


def css(levels: bool = False) -> str:
    """Dark by default, light when the viewer's OS asks for it."""
    return (
        _rules(DARK, levels)
        + "@media (prefers-color-scheme:light){"
        + _rules(LIGHT, levels)
        + "}"
    )
