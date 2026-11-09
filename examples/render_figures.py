"""Render the F1 LapLab figures to PNG files.

By default this runs against the same synthetic fixture as
``synthetic_pipeline.py``: offline, no network request, no FastF1 cache access.

Passing ``--session`` loads a real session through FastF1 instead. That path
reads the configured FastF1 cache and, if the session is not already cached,
makes network requests and writes to it.

    python examples/render_figures.py
    python examples/render_figures.py --session 2024 "Monaco Grand Prix" R \
        --highlight LEC PIA SAI
"""

from __future__ import annotations

import argparse
from pathlib import Path

from synthetic_pipeline import build_synthetic_session

from f1strategy.config.settings import Settings
from f1strategy.domain.enums import SessionType
from f1strategy.domain.models import LoadedSession, SessionRef
from f1strategy.features import build_lap_features
from f1strategy.telemetry.loader import FastF1SessionLoader
from f1strategy.telemetry.validation import validate_laps_with_report
from f1strategy.visualization import (
    THEMES,
    Theme,
    add_caption,
    feature_target_figure,
    history_depth_figure,
    lap_time_trace_figure,
    pipeline_overview_figure,
    validation_breakdown_figure,
)

DEFAULT_OUT = Path("docs") / "images"
SYNTHETIC_NOTE = "Synthetic demonstration data, not real Formula 1 timing."


def _load_real_session(year: int, grand_prix: str, session_code: str) -> LoadedSession:
    """Load one session through the FastF1 boundary. Touches the cache."""
    ref = SessionRef(year, grand_prix, SessionType(session_code))
    return FastF1SessionLoader(Settings.load()).load(ref)


def _render(
    out_dir: Path,
    theme: Theme,
    session: LoadedSession,
    *,
    prefix: str,
    label: str,
    caption: str,
    highlight: list[str] | None,
) -> list[Path]:
    report = validate_laps_with_report(session.laps)
    dataset = build_lap_features(session)

    figures = {
        "pipeline-overview": pipeline_overview_figure(
            session,
            report,
            dataset,
            highlight=highlight,
            theme=theme,
            title=f"F1 LapLab pipeline - {label}",
        ),
        "lap-times": lap_time_trace_figure(
            session, highlight=highlight, theme=theme, title=f"Lap times - {label}"
        ),
        "validation": validation_breakdown_figure(
            report, theme=theme, title=f"Validation outcome - {label}"
        ),
        "history-depth": history_depth_figure(
            dataset, theme=theme, title=f"Prior-history depth - {label}"
        ),
        "feature-target": feature_target_figure(
            dataset, theme=theme, title=f"Predictor vs label - {label}"
        ),
    }

    written: list[Path] = []
    for name, figure in figures.items():
        add_caption(figure, caption, theme)
        path = out_dir / f"{prefix}{name}-{theme.name}.png"
        figure.savefig(
            path, facecolor=theme.surface, bbox_inches="tight", pad_inches=0.3
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
    parser.add_argument(
        "--session",
        nargs=3,
        metavar=("YEAR", "GRAND_PRIX", "SESSION"),
        help="load a real session via FastF1 instead of the synthetic fixture; "
        "reads (and may write to) the FastF1 cache",
    )
    parser.add_argument(
        "--highlight",
        nargs="*",
        metavar="DRIVER",
        help="driver codes to emphasise (default: most eligible laps)",
    )
    parser.add_argument(
        "--prefix", default="", help="filename prefix for the rendered PNGs"
    )
    args = parser.parse_args()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.session:
        year, grand_prix, session_code = args.session
        print(f"Loading {year} {grand_prix} {session_code} through FastF1 (uses cache).")
        session = _load_real_session(int(year), grand_prix, session_code)
        label = f"{session.metadata.event_name} {year}"
        caption = (
            "Rendered from a FastF1 session held in a local cache. The underlying "
            "timing data is not distributed with this repository."
        )
    else:
        print("Rendering from the synthetic fixture (no network, no cache access).")
        session = build_synthetic_session()
        label = "synthetic demonstration"
        caption = SYNTHETIC_NOTE

    for theme in THEMES.values():
        for path in _render(
            out_dir,
            theme,
            session,
            prefix=args.prefix,
            label=label,
            caption=caption,
            highlight=args.highlight,
        ):
            print(f"  {path}  ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
