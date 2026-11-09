"""Render tokens for figures.

WHY THIS FILE EXISTS
    Figures are rendered twice: once for a light page and once for a dark one, so
    a README can serve the right image per viewer theme. Rather than flipping
    colours programmatically (which lands outside the usable lightness band on
    the opposite surface), each mode is an explicitly chosen set of tokens.

PROVENANCE
    Values come from the project's visualization palette and were checked with
    the palette validator before use:
      - categorical slots 1-3 pass every gate in both modes (all-pairs)
      - the ordinal ramps pass monotonicity, step-gap, and light-end contrast
    Light-mode aqua sits below 3:1 against the surface, so every figure that
    uses the categorical slots also carries direct labels (the documented relief
    for a contrast warning). Status colours are fixed and never themed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    """Colour tokens for one render mode.

    ``series`` are identity colours, assigned in fixed order and never cycled.
    ``ordinal`` is a single-hue ramp for the 0-3 history-depth scale, ordered
    light to dark. ``excluded`` is a reserved status colour and is identical in
    both modes; it always ships with a label, never as colour alone.
    """

    name: str
    surface: str
    ink_primary: str
    ink_secondary: str
    ink_muted: str
    grid: str
    baseline: str
    series: tuple[str, str, str]
    deemphasis: str
    excluded: str
    ordinal: tuple[str, str, str, str]


LIGHT = Theme(
    name="light",
    surface="#fcfcfb",
    ink_primary="#0b0b0b",
    ink_secondary="#52514e",
    ink_muted="#898781",
    grid="#e1e0d9",
    baseline="#c3c2b7",
    series=("#2a78d6", "#eb6834", "#1baf7a"),
    deemphasis="#c3c2b7",
    excluded="#d03b3b",
    ordinal=("#86b6ef", "#5598e7", "#2a78d6", "#1c5cab"),
)

DARK = Theme(
    name="dark",
    surface="#1a1a19",
    ink_primary="#ffffff",
    ink_secondary="#c3c2b7",
    ink_muted="#898781",
    grid="#2c2c2a",
    baseline="#383835",
    series=("#3987e5", "#d95926", "#199e70"),
    deemphasis="#52514e",
    excluded="#d03b3b",
    ordinal=("#184f95", "#2a78d6", "#6da7ec", "#b7d3f6"),
)

THEMES: dict[str, Theme] = {LIGHT.name: LIGHT, DARK.name: DARK}
