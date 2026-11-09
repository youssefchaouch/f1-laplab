"""Figure builders for validated sessions and lap feature datasets.

WHY THIS FILE EXISTS
    The pipeline's output is a validated frame and a feature dataset, which are
    hard to assess by reading numbers. These builders turn the parts that carry
    the project's claims -- what validation excluded, how much prior history each
    target lap had, and how the predictor relates to the label -- into figures.

DESIGN
    Every public function is pure: typed domain objects in, a ``Figure`` out. No
    data loading, no file writing, no ``pyplot`` global state, and no display
    backend is required, so these run headless and are safe to unit test. The
    caller decides where (or whether) to save.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from f1strategy.domain import schemas as S
from f1strategy.domain.models import LoadedSession
from f1strategy.features.lap_features import LapFeatureDataset
from f1strategy.telemetry.validation import LapValidationReport
from f1strategy.visualization.theme import LIGHT, Theme

# Which validation reasons exclude a lap, as implemented by
# ``validate_laps_with_report``. The remaining reasons (pit in/out, non-clear
# track status) are warnings: the lap stays eligible. Charting them together
# without this split would misreport warnings as exclusions.
EXCLUSION_REASONS = frozenset(
    {"inaccurate_lap", "deleted_lap", "missing_lap_time", "duplicate_identity"}
)

MAX_HIGHLIGHT = 3  # identity colours available; past this, drivers stay de-emphasised


def _style_axes(ax: Axes, theme: Theme, *, xlabel: str, ylabel: str) -> None:
    """Apply recessive chrome: hairline solid grid, no top/right spines."""
    ax.set_facecolor(theme.surface)
    ax.set_xlabel(xlabel, color=theme.ink_secondary, fontsize=9)
    ax.set_ylabel(ylabel, color=theme.ink_secondary, fontsize=9)
    ax.tick_params(colors=theme.ink_muted, labelsize=8, length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(theme.baseline)
        ax.spines[side].set_linewidth(1.0)
    ax.grid(True, axis="y", color=theme.grid, linewidth=1.0, linestyle="-", zorder=0)
    ax.set_axisbelow(True)


def _new_figure(theme: Theme, *, size: tuple[float, float]) -> tuple[Figure, Axes]:
    """Create a standalone figure without touching pyplot's global state."""
    figure = Figure(figsize=size, dpi=200, facecolor=theme.surface)
    axes = figure.add_subplot(111)
    return figure, axes


def _title(ax: Axes, theme: Theme, title: str, subtitle: str | None = None) -> None:
    ax.set_title(title, color=theme.ink_primary, fontsize=12, loc="left", pad=28)
    if subtitle:
        ax.annotate(
            subtitle,
            xy=(0.0, 1.0),
            xycoords="axes fraction",
            xytext=(0, 8),
            textcoords="offset points",
            color=theme.ink_secondary,
            fontsize=9,
        )


def _legend(
    ax: Axes, theme: Theme, handles: Sequence[Line2D], *, below: bool = False
) -> None:
    """Place a frameless legend.

    ``below`` puts it under the axes, which is the only placement that cannot
    collide with the data or with direct labels - a real risk on a trace whose
    series end in the top-right corner.
    """
    placement: dict[str, object] = (
        {"loc": "upper left", "bbox_to_anchor": (0.0, -0.16), "ncols": len(handles)}
        if below
        else {"loc": "upper right"}
    )
    legend = ax.legend(
        handles=list(handles),
        frameon=False,
        fontsize=8,
        labelcolor=theme.ink_secondary,
        handlelength=1.6,
        **placement,
    )
    legend.set_zorder(6)


def _human(reason: str) -> str:
    return reason.replace("_", " ")


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def default_highlight(session: LoadedSession) -> tuple[str, ...]:
    """Pick the drivers to emphasise: most eligible laps, then alphabetical.

    Deterministic, so a figure built from the same session is reproducible.
    """
    eligible = session.laps.loc[session.laps[S.IS_VALID]]
    counts = Counter(str(driver) for driver in eligible[S.DRIVER])
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(driver for driver, _ in ranked[:MAX_HIGHLIGHT])


def _draw_lap_time_trace(
    ax: Axes, session: LoadedSession, highlight: Sequence[str], theme: Theme
) -> None:
    laps = session.laps
    emphasised = list(dict.fromkeys(highlight))[:MAX_HIGHLIGHT]
    has_others = False

    for driver in sorted({str(d) for d in laps[S.DRIVER]}):
        rows = laps.loc[laps[S.DRIVER] == driver].sort_values(S.LAP_NUMBER)
        x = rows[S.LAP_NUMBER].astype("int64")
        y = rows[S.LAP_TIME_S].astype("float64")
        if driver in emphasised:
            colour = theme.series[emphasised.index(driver)]
            ax.plot(x, y, color=colour, linewidth=2.0, solid_capstyle="round", zorder=3)
            visible = rows.loc[rows[S.LAP_TIME_S].notna()]
            if not visible.empty:
                last = visible.iloc[-1]
                # Direct label: the documented relief for a sub-3:1 series colour.
                ax.annotate(
                    driver,
                    xy=(int(last[S.LAP_NUMBER]), float(last[S.LAP_TIME_S])),
                    xytext=(6, 0),
                    textcoords="offset points",
                    color=theme.ink_secondary,
                    fontsize=8,
                    va="center",
                    zorder=4,
                )
        else:
            has_others = True
            ax.plot(x, y, color=theme.deemphasis, linewidth=1.0, zorder=1)

    invalid = laps.loc[~laps[S.IS_VALID] & laps[S.LAP_TIME_S].notna()]
    if not invalid.empty:
        ax.scatter(
            invalid[S.LAP_NUMBER].astype("int64"),
            invalid[S.LAP_TIME_S].astype("float64"),
            marker="x",
            s=44,
            color=theme.excluded,
            linewidths=1.6,
            zorder=5,
        )

    handles: list[Line2D] = []
    if len(emphasised) > 1:
        handles.extend(
            Line2D([], [], color=theme.series[index], linewidth=2.0, label=driver)
            for index, driver in enumerate(emphasised)
        )
    if has_others:
        handles.append(
            Line2D([], [], color=theme.deemphasis, linewidth=1.0, label="other drivers")
        )
    if not invalid.empty:
        handles.append(
            Line2D(
                [],
                [],
                color=theme.excluded,
                marker="x",
                linestyle="none",
                markersize=6,
                label="excluded lap (timed)",
            )
        )
    if handles:
        _legend(ax, theme, handles, below=True)

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.margins(x=0.07)
    _style_axes(ax, theme, xlabel="Lap number", ylabel="Lap time (s)")


def _draw_validation_breakdown(
    ax: Axes, report: LapValidationReport, theme: Theme
) -> None:
    excluding = sorted(
        ((r, c) for r, c in report.reason_counts if r in EXCLUSION_REASONS),
        key=lambda item: (item[1], item[0]),
    )
    warning = sorted(
        ((r, c) for r, c in report.reason_counts if r not in EXCLUSION_REASONS),
        key=lambda item: (item[1], item[0]),
    )
    ordered = warning + excluding
    if not ordered:
        ax.text(
            0.5,
            0.5,
            "no validation issues reported",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=theme.ink_secondary,
            fontsize=9,
        )
        _style_axes(ax, theme, xlabel="Laps", ylabel="")
        return

    positions = list(range(len(ordered)))
    colours = [
        theme.series[0] if reason in EXCLUSION_REASONS else theme.deemphasis
        for reason, _ in ordered
    ]
    ax.barh(
        positions,
        [count for _, count in ordered],
        color=colours,
        height=0.42,
        zorder=2,
    )
    ax.set_yticks(positions)
    ax.set_yticklabels([_human(reason) for reason, _ in ordered])
    largest = max(count for _, count in ordered)
    for position, (_, count) in zip(positions, ordered, strict=True):
        ax.annotate(
            str(count),
            xy=(count, position),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            color=theme.ink_secondary,
            fontsize=8,
        )
    ax.set_xlim(0, largest * 1.18)
    ax.set_ylim(-0.7, max(len(ordered) - 0.3, 4.7))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    handles = [
        Line2D([], [], color=theme.series[0], linewidth=6, label="excludes the lap"),
        Line2D([], [], color=theme.deemphasis, linewidth=6, label="warning, lap kept"),
    ]
    _legend(ax, theme, handles)
    _style_axes(ax, theme, xlabel="Laps", ylabel="")
    ax.grid(False, axis="y")
    ax.grid(True, axis="x", color=theme.grid, linewidth=1.0, linestyle="-", zorder=0)


def _draw_feature_target(ax: Axes, dataset: LapFeatureDataset, theme: Theme) -> None:
    previous = dataset.features["previous_lap_time_s"].astype("float64")
    target = dataset.labels.astype("float64")
    depth = dataset.features["prior_3lap_valid_count"].astype("int64")

    paired = previous.notna()
    if paired.any():
        low = float(min(previous[paired].min(), target[paired].min()))
        high = float(max(previous[paired].max(), target[paired].max()))
        ax.plot([low, high], [low, high], color=theme.baseline, linewidth=1.0, zorder=1)

    for level in sorted(set(depth[paired].tolist())):
        mask = paired & depth.eq(level)
        suffix = "" if level == 1 else "s"
        ax.scatter(
            previous[mask],
            target[mask],
            s=64,
            color=theme.ordinal[min(level, len(theme.ordinal) - 1)],
            edgecolors=theme.surface,
            linewidths=1.5,
            zorder=3,
            label=f"{level} prior lap{suffix}",
        )

    if paired.any():
        legend = ax.legend(
            loc="upper left",
            frameon=False,
            fontsize=8,
            labelcolor=theme.ink_secondary,
            title="history used",
            handletextpad=0.4,
        )
        title_text = legend.get_title()
        title_text.set_color(theme.ink_secondary)
        title_text.set_fontsize(8)

    _style_axes(
        ax,
        theme,
        xlabel="previous_lap_time_s (predictor)",
        ylabel="target_lap_time_s (label)",
    )


def _draw_history_depth(ax: Axes, dataset: LapFeatureDataset, theme: Theme) -> None:
    depth = dataset.features["prior_3lap_valid_count"].astype("int64")
    levels = list(range(len(theme.ordinal)))
    counts = [int((depth == level).sum()) for level in levels]
    ax.bar(levels, counts, color=list(theme.ordinal), width=0.42, zorder=2)
    ax.set_xticks(levels)
    ax.set_xticklabels([str(level) for level in levels])
    for level, count in zip(levels, counts, strict=True):
        ax.annotate(
            str(count),
            xy=(level, count),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            color=theme.ink_secondary,
            fontsize=8,
        )
    ceiling = max(counts) if any(counts) else 1
    ax.set_ylim(0, ceiling * 1.2)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    _style_axes(
        ax, theme, xlabel="Eligible prior laps in slots n-3 to n-1", ylabel="Target laps"
    )


def lap_time_trace_figure(
    session: LoadedSession,
    *,
    highlight: Sequence[str] | None = None,
    theme: Theme = LIGHT,
    title: str | None = None,
) -> Figure:
    """Lap times per lap number, emphasising a few drivers and marking exclusions.

    Up to three drivers carry identity colours and direct labels; the rest stay
    de-emphasised, so the chart does not spend eight hues on context. Excluded
    laps that still have a time are marked rather than silently dropped. Laps
    without a time appear as gaps.
    """
    figure, ax = _new_figure(theme, size=(9.0, 5.0))
    chosen = default_highlight(session) if highlight is None else highlight
    _draw_lap_time_trace(ax, session, chosen, theme)
    _title(
        ax,
        theme,
        title or f"Lap times - {session.metadata.event_name}",
        f"{_plural(session.metadata.n_drivers, 'driver')}, "
        f"{_plural(session.metadata.n_laps, 'lap record')}",
    )
    figure.tight_layout()
    return figure


def validation_breakdown_figure(
    report: LapValidationReport,
    *,
    theme: Theme = LIGHT,
    title: str | None = None,
) -> Figure:
    """Validation reasons, separating exclusions from warnings.

    Reason counts are non-exclusive: one lap can carry several reasons, and a pit
    or non-clear-status marker is a warning that does not exclude the lap. The
    two groups are coloured and labelled separately for that reason.
    """
    figure, ax = _new_figure(theme, size=(9.0, 5.0))
    _draw_validation_breakdown(ax, report, theme)
    _title(
        ax,
        theme,
        title or "Canonical validation outcome",
        f"{report.input_rows} rows: {report.retained_rows} retained, "
        f"{report.excluded_rows} excluded",
    )
    figure.tight_layout()
    return figure


def feature_target_figure(
    dataset: LapFeatureDataset,
    *,
    theme: Theme = LIGHT,
    title: str | None = None,
) -> Figure:
    """The predictor against its label, shaded by how much history was available.

    The reference line is y = x: distance from it is how much the previous lap
    misses the target lap. Target laps whose ``n-1`` slot was ineligible have no
    predictor value and are absent by construction, never imputed.
    """
    figure, ax = _new_figure(theme, size=(7.0, 6.0))
    _draw_feature_target(ax, dataset, theme)
    _title(
        ax,
        theme,
        title or "Previous lap vs target lap",
        f"{_plural(len(dataset.labels), 'eligible target lap')}",
    )
    figure.tight_layout()
    return figure


def history_depth_figure(
    dataset: LapFeatureDataset,
    *,
    theme: Theme = LIGHT,
    title: str | None = None,
) -> Figure:
    """How many of the three prior slots were eligible, per target lap.

    This is a data-quality view: a tall ``0`` or ``1`` bar means most targets
    carry little usable history, which any later model has to answer for.
    """
    figure, ax = _new_figure(theme, size=(7.0, 5.0))
    _draw_history_depth(ax, dataset, theme)
    _title(
        ax,
        theme,
        title or "Prior-history depth",
        "window is fixed at lap slots n-3 to n-1; missing slots stay missing",
    )
    figure.tight_layout()
    return figure


def pipeline_overview_figure(
    session: LoadedSession,
    report: LapValidationReport,
    dataset: LapFeatureDataset,
    *,
    highlight: Sequence[str] | None = None,
    theme: Theme = LIGHT,
    title: str | None = None,
) -> Figure:
    """One figure covering the whole pipeline, for a README or a post.

    Panels, in reading order: lap times with exclusions marked, the validation
    outcome, prior-history depth, and predictor against label.
    """
    figure = Figure(figsize=(14.0, 9.0), dpi=200, facecolor=theme.surface)
    grid = figure.add_gridspec(2, 2, hspace=0.58, wspace=0.26)

    trace_ax = figure.add_subplot(grid[0, 0])
    chosen = default_highlight(session) if highlight is None else highlight
    _draw_lap_time_trace(trace_ax, session, chosen, theme)
    _title(trace_ax, theme, "1. Validated lap times", "exclusions marked, not dropped")

    breakdown_ax = figure.add_subplot(grid[0, 1])
    _draw_validation_breakdown(breakdown_ax, report, theme)
    _title(
        breakdown_ax,
        theme,
        "2. Validation outcome",
        f"{report.retained_rows} of {report.input_rows} rows retained",
    )

    depth_ax = figure.add_subplot(grid[1, 0])
    _draw_history_depth(depth_ax, dataset, theme)
    _title(depth_ax, theme, "3. Prior-history depth", "fixed window, no backfill")

    scatter_ax = figure.add_subplot(grid[1, 1])
    _draw_feature_target(scatter_ax, dataset, theme)
    _title(scatter_ax, theme, "4. Predictor vs label", "reference line is y = x")

    figure.suptitle(
        title or f"F1 LapLab - {session.metadata.event_name}",
        color=theme.ink_primary,
        fontsize=15,
        x=0.012,
        ha="left",
        y=0.985,
    )
    return figure
