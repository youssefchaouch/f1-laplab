"""Render the F1 LapLab figures to PNG files.

Runs offline against the same synthetic fixture as ``synthetic_pipeline.py``, so
it makes no network request and never touches a FastF1 cache. Each figure is
rendered once per theme, because a README is read on both light and dark pages.

    python examples/render_figures.py [--out DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from synthetic_pipeline import build_synthetic_session

from f1strategy.features import build_lap_features
from f1strategy.telemetry.validation import validate_laps_with_report
from f1strategy.visualization import (
    THEMES,
    Theme,
    feature_target_figure,
    history_depth_figure,
    lap_time_trace_figure,
    pipeline_overview_figure,
    validation_breakdown_figure,
)

DEFAULT_OUT = Path("docs") / "images"


def _render(out_dir: Path, theme: Theme) -> list[Path]:
    session = build_synthetic_session()
    report = validate_laps_with_report(session.laps)
    dataset = build_lap_features(session)
    suffix = "Synthetic demonstration data, not real Formula 1 timing."

    figures = {
        "pipeline-overview": pipeline_overview_figure(
            session, report, dataset, theme=theme, title=f"F1 LapLab pipeline - {suffix}"
        ),
        "lap-times": lap_time_trace_figure(
            session, theme=theme, title=f"Lap times - {suffix}"
        ),
        "validation": validation_breakdown_figure(
            report, theme=theme, title=f"Validation outcome - {suffix}"
        ),
        "history-depth": history_depth_figure(
            dataset, theme=theme, title=f"Prior-history depth - {suffix}"
        ),
        "feature-target": feature_target_figure(
            dataset, theme=theme, title=f"Predictor vs label - {suffix}"
        ),
    }

    written: list[Path] = []
    for name, figure in figures.items():
        path = out_dir / f"{name}-{theme.name}.png"
        figure.savefig(
            path,
            facecolor=theme.surface,
            bbox_inches="tight",
            pad_inches=0.3,
        )
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Rendering F1 LapLab figures from the synthetic fixture (no network).")
    for theme in THEMES.values():
        for path in _render(out_dir, theme):
            size_kb = path.stat().st_size / 1024
            print(f"  {path}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
