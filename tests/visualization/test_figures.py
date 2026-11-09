"""Offline tests for figure construction.

Figures are asserted by inspecting the built ``Figure`` object - artist counts,
colours, labels - rather than by rendering pixels. That keeps the tests fast,
deterministic, and free of any display backend or file output.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.features import build_lap_features
from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.validation import validate_laps, validate_laps_with_report
from f1strategy.visualization import (
    DARK,
    EXCLUSION_REASONS,
    LIGHT,
    default_highlight,
    feature_target_figure,
    history_depth_figure,
    lap_time_trace_figure,
    pipeline_overview_figure,
    validation_breakdown_figure,
)


def _plotted_points(ax: Axes) -> int:
    """Total scatter points across an axes, via a concrete array."""
    return sum(
        int(np.asarray(collection.get_offsets()).shape[0])
        for collection in ax.collections
    )


def _raw_rows(
    template: pd.DataFrame, laps: Iterable[dict[str, object]]
) -> pd.DataFrame:
    base = template.iloc[0]
    rows: list[pd.Series] = []
    for lap in laps:
        row = base.copy()
        row["Driver"] = str(lap.get("driver", "VER"))
        row["Team"] = str(lap.get("team", "Red Bull Racing"))
        lap_number = lap["lap"]
        assert isinstance(lap_number, int)
        row["LapNumber"] = lap_number
        seconds = lap.get("time_s")
        row["LapTime"] = (
            pd.NaT if seconds is None else pd.Timedelta(seconds=float(seconds))  # type: ignore[arg-type]
        )
        row["IsAccurate"] = bool(lap.get("accurate", True))
        row["Deleted"] = bool(lap.get("deleted", False))
        row["PitInTime"] = pd.Timedelta(seconds=1) if lap.get("pit_in") else pd.NaT
        row["PitOutTime"] = pd.Timedelta(seconds=1) if lap.get("pit_out") else pd.NaT
        row["TrackStatus"] = str(lap.get("track_status", "1"))
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


def _loaded_session(raw: pd.DataFrame) -> LoadedSession:
    laps = validate_laps(fastf1_laps_to_frame(raw))
    ref = SessionRef(2024, "Monaco", SessionType.RACE)
    metadata = SessionMetadata(
        ref=ref,
        event_name="Monaco Grand Prix",
        circuit="Monaco",
        country="Monaco",
        n_drivers=int(laps[S.DRIVER].nunique()),
        n_laps=len(laps),
        loaded_with_telemetry=False,
    )
    return LoadedSession(metadata=metadata, laps=laps)


@pytest.fixture
def session(raw_fastf1_laps: pd.DataFrame) -> LoadedSession:
    """Two drivers, one deleted lap, one pit-out lap, one inaccurate lap."""
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 90.0, "pit_out": True},
            {"lap": 2, "time_s": 91.0},
            {"lap": 3, "time_s": 92.0, "deleted": True},
            {"lap": 4, "time_s": 94.0},
            {"lap": 5, "time_s": 95.0},
            {"lap": 1, "time_s": 93.0, "driver": "LEC", "team": "Ferrari"},
            {"lap": 2, "time_s": 92.5, "driver": "LEC", "team": "Ferrari"},
            {"lap": 3, "time_s": 99.0, "driver": "LEC", "team": "Ferrari",
             "accurate": False},
        ],
    )
    return _loaded_session(raw)


def test_exclusion_reason_split_matches_the_validation_module(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    """Guard: a warning reason must never be classified as an exclusion.

    If ``validate_laps_with_report`` gains a reason, this fails until the
    figure-side classification is updated, so a warning cannot silently start
    being charted as an exclusion.
    """
    warning_only = _loaded_session(
        _raw_rows(
            raw_fastf1_laps,
            [
                {"lap": 1, "time_s": 90.0, "pit_out": True},
                {"lap": 2, "time_s": 91.0, "pit_in": True, "track_status": "4"},
            ],
        )
    )
    report = validate_laps_with_report(warning_only.laps)
    assert report.excluded_rows == 0
    observed = {reason for issue in report.issues for reason in issue.reasons}
    assert observed  # the fixture does trigger warnings
    assert observed.isdisjoint(EXCLUSION_REASONS)

    excluded = _loaded_session(
        _raw_rows(
            raw_fastf1_laps,
            [
                {"lap": 1, "time_s": 90.0},
                {"lap": 2, "time_s": 91.0, "deleted": True},
                {"lap": 3, "time_s": None},
                {"lap": 4, "time_s": 92.0, "accurate": False},
            ],
        )
    )
    excluded_report = validate_laps_with_report(excluded.laps)
    excluded_reasons = {
        reason
        for issue in excluded_report.issues
        if issue.excluded
        for reason in issue.reasons
    }
    assert excluded_reasons <= EXCLUSION_REASONS


def test_default_highlight_is_deterministic_and_capped(session: LoadedSession) -> None:
    first = default_highlight(session)
    assert first == default_highlight(session)
    assert len(first) <= 3
    # VER has 3 eligible laps, LEC has 2, so VER leads.
    assert first[0] == "VER"


def test_lap_time_trace_marks_excluded_laps_and_labels_series(
    session: LoadedSession,
) -> None:
    figure = lap_time_trace_figure(session)
    assert isinstance(figure, Figure)
    ax = figure.axes[0]

    # One line per driver in the session.
    assert len(ax.lines) == 2

    # The deleted and inaccurate laps both have times, so both are marked.
    marked = _plotted_points(ax)
    assert marked == 2

    labels = [text.get_text() for text in ax.texts]
    assert "VER" in labels  # direct label, the relief for the contrast warning
    legend = ax.get_legend()
    assert legend is not None
    legend_labels = [text.get_text() for text in legend.get_texts()]
    assert "excluded lap (timed)" in legend_labels


def test_lap_time_trace_respects_explicit_highlight(session: LoadedSession) -> None:
    figure = lap_time_trace_figure(session, highlight=["LEC"])
    ax = figure.axes[0]

    # A lone emphasised series carries a direct label, not a one-swatch legend
    # entry that would only restate it.
    direct = [text.get_text() for text in ax.texts]
    assert "LEC" in direct
    assert "VER" not in direct

    legend = ax.get_legend()
    assert legend is not None
    labels = [text.get_text() for text in legend.get_texts()]
    assert "other drivers" in labels
    assert "LEC" not in labels


def test_lap_time_trace_legends_multiple_emphasised_drivers(
    session: LoadedSession,
) -> None:
    figure = lap_time_trace_figure(session, highlight=["VER", "LEC"])
    legend = figure.axes[0].get_legend()
    assert legend is not None
    labels = [text.get_text() for text in legend.get_texts()]
    assert "VER" in labels and "LEC" in labels


def test_validation_breakdown_separates_exclusions_from_warnings(
    session: LoadedSession,
) -> None:
    report = validate_laps_with_report(session.laps)
    figure = validation_breakdown_figure(report)
    ax = figure.axes[0]

    reasons = [reason for reason, _ in report.reason_counts]
    assert len(ax.patches) == len(reasons)

    exclusion_colour = LIGHT.series[0]
    warning_colour = LIGHT.deemphasis
    tick_labels = [label.get_text() for label in ax.get_yticklabels()]
    for patch, label in zip(ax.patches, tick_labels, strict=True):
        reason = label.replace(" ", "_")
        expected = exclusion_colour if reason in EXCLUSION_REASONS else warning_colour
        assert patch.get_facecolor()[:3] == pytest.approx(
            _rgb(expected), abs=1e-3
        ), f"{reason} drawn in the wrong group colour"


def _rgb(hex_colour: str) -> tuple[float, float, float]:
    raw = hex_colour.lstrip("#")
    return tuple(int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def test_validation_breakdown_handles_a_clean_session(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    clean = _loaded_session(
        _raw_rows(raw_fastf1_laps, [{"lap": 1, "time_s": 90.0}, {"lap": 2, "time_s": 91.0}])
    )
    report = validate_laps_with_report(clean.laps)
    assert report.reason_counts == ()
    figure = validation_breakdown_figure(report)
    ax = figure.axes[0]
    assert not ax.patches
    assert any("no validation issues" in text.get_text() for text in ax.texts)


def test_feature_target_plots_only_rows_with_a_predecessor(
    session: LoadedSession,
) -> None:
    dataset = build_lap_features(session)
    figure = feature_target_figure(dataset)
    ax = figure.axes[0]

    plotted = _plotted_points(ax)
    expected = int(dataset.features["previous_lap_time_s"].notna().sum())
    assert plotted == expected
    # Missing predecessors are absent, never imputed.
    assert plotted < len(dataset.labels)
    assert len(ax.lines) == 1  # the y = x reference line


def test_history_depth_counts_every_level(session: LoadedSession) -> None:
    dataset = build_lap_features(session)
    figure = history_depth_figure(dataset)
    ax = figure.axes[0]

    assert len(ax.patches) == 4  # levels 0..3 always shown, including empty ones
    heights = [
        bar.get_height() for bar in ax.patches if isinstance(bar, Rectangle)
    ]
    depth = dataset.features["prior_3lap_valid_count"].astype("int64")
    assert heights == [float((depth == level).sum()) for level in range(4)]
    assert sum(heights) == len(dataset.labels)


def test_pipeline_overview_has_all_four_panels(session: LoadedSession) -> None:
    report = validate_laps_with_report(session.laps)
    dataset = build_lap_features(session)
    figure = pipeline_overview_figure(session, report, dataset)
    assert len(figure.axes) == 4
    titles = [ax.get_title(loc="left") for ax in figure.axes]
    assert titles == [
        "1. Validated lap times",
        "2. Validation outcome",
        "3. Prior-history depth",
        "4. Predictor vs label",
    ]


@pytest.mark.parametrize("theme", [LIGHT, DARK])
def test_both_themes_paint_their_own_surface(
    session: LoadedSession, theme: object
) -> None:
    from f1strategy.visualization.theme import Theme

    assert isinstance(theme, Theme)
    figure = lap_time_trace_figure(session, theme=theme)
    assert figure.get_facecolor()[:3] == pytest.approx(_rgb(theme.surface), abs=1e-3)
    assert figure.axes[0].get_facecolor()[:3] == pytest.approx(
        _rgb(theme.surface), abs=1e-3
    )


def test_figures_do_not_require_a_display_or_write_files(
    session: LoadedSession, tmp_path: object
) -> None:
    """The builders are pure: nothing reaches the filesystem until the caller saves."""
    import matplotlib

    assert matplotlib.get_backend() is not None
    report = validate_laps_with_report(session.laps)
    dataset = build_lap_features(session)
    before = sorted(p.name for p in __import__("pathlib").Path(".").iterdir())
    for figure in (
        lap_time_trace_figure(session),
        validation_breakdown_figure(report),
        feature_target_figure(dataset),
        history_depth_figure(dataset),
        pipeline_overview_figure(session, report, dataset),
    ):
        assert isinstance(figure, Figure)
    after = sorted(p.name for p in __import__("pathlib").Path(".").iterdir())
    assert before == after
