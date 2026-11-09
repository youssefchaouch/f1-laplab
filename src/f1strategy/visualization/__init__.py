"""Visualization layer - typed domain objects in, matplotlib figures out.

This layer never loads data and never writes files: it receives already-validated
domain objects and returns ``Figure`` instances for the caller to save or embed.
Static images are deliberate - the figures are published in a README and in
posts, where interactive output does not render.
"""

from f1strategy.visualization.figures import (
    EXCLUSION_REASONS,
    add_caption,
    default_highlight,
    feature_target_figure,
    history_depth_figure,
    lap_time_trace_figure,
    pipeline_overview_figure,
    validation_breakdown_figure,
)
from f1strategy.visualization.theme import DARK, LIGHT, THEMES, Theme

__all__ = [
    "DARK",
    "EXCLUSION_REASONS",
    "LIGHT",
    "THEMES",
    "Theme",
    "add_caption",
    "default_highlight",
    "feature_target_figure",
    "history_depth_figure",
    "lap_time_trace_figure",
    "pipeline_overview_figure",
    "validation_breakdown_figure",
]
