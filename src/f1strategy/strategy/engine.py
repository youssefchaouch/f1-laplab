"""Explainable one-stop strategy calculations from explicit assumptions.

The baseline model assumes a constant reference lap time, an optional fixed
per-compound pace offset, and linear tire degradation. Tire age is zero on the
first lap of each stint, so a stint of ``n`` laps adds degradation for ages
``0`` through ``n - 1``. These are illustrative inputs, not a calibrated model
of real race pace.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isclose, isfinite

from f1strategy.domain.enums import TireCompound


def _require_integer(value: int, *, name: str, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")


def _require_finite_number(value: float, *, name: str, minimum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < minimum:
        raise ValueError(f"{name} must be greater than or equal to {minimum}")


@dataclass(frozen=True, slots=True)
class TireDegradation:
    """Configured compound pace and linear lap-time increase per lap of tire age.

    ``pace_offset_s`` is added to every lap on this compound, relative to the
    baseline lap time. A negative value is a faster compound. With the default
    of ``0.0`` every compound shares the baseline pace.
    """

    compound: TireCompound
    seconds_per_lap: float
    pace_offset_s: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.compound, TireCompound) or self.compound is TireCompound.UNKNOWN:
            raise ValueError("compound must be a known tire compound")
        _require_finite_number(
            self.seconds_per_lap,
            name="seconds_per_lap",
            minimum=0.0,
        )
        if (
            isinstance(self.pace_offset_s, bool)
            or not isinstance(self.pace_offset_s, (int, float))
            or not isfinite(self.pace_offset_s)
        ):
            raise ValueError("pace_offset_s must be a finite number")


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """Race length, model assumptions, and legal one-stop search constraints.

    ``pit_lap`` means the number of completed laps before the stop. Pit-window
    endpoints are inclusive. Compound changes are not required: this engine
    models timing only and does not encode sporting regulations.
    """

    race_laps: int
    baseline_lap_time_s: float
    pit_stop_loss_s: float
    tire_degradation: tuple[TireDegradation, ...]
    min_stint_laps: int = 1
    max_stint_laps: int | None = None
    pit_window_start_lap: int = 1
    pit_window_end_lap: int | None = None

    def __post_init__(self) -> None:
        _require_integer(self.race_laps, name="race_laps", minimum=2)
        _require_finite_number(
            self.baseline_lap_time_s,
            name="baseline_lap_time_s",
            minimum=0.0,
        )
        if self.baseline_lap_time_s == 0:
            raise ValueError("baseline_lap_time_s must be greater than zero")
        _require_finite_number(
            self.pit_stop_loss_s,
            name="pit_stop_loss_s",
            minimum=0.0,
        )
        _require_integer(self.min_stint_laps, name="min_stint_laps", minimum=1)

        max_stint_laps = self.max_stint_laps
        if max_stint_laps is None:
            max_stint_laps = self.race_laps
            object.__setattr__(self, "max_stint_laps", max_stint_laps)
        _require_integer(max_stint_laps, name="max_stint_laps", minimum=1)
        if max_stint_laps < self.min_stint_laps:
            raise ValueError("max_stint_laps cannot be less than min_stint_laps")
        if 2 * self.min_stint_laps > self.race_laps:
            raise ValueError("race_laps is too short to satisfy both minimum stint lengths")

        pit_window_end = self.pit_window_end_lap
        if pit_window_end is None:
            pit_window_end = self.race_laps - 1
            object.__setattr__(self, "pit_window_end_lap", pit_window_end)
        _require_integer(
            self.pit_window_start_lap,
            name="pit_window_start_lap",
            minimum=1,
        )
        if not isinstance(pit_window_end, int) or isinstance(pit_window_end, bool):
            raise ValueError("pit_window_end_lap must be an integer")
        if not self.pit_window_start_lap <= pit_window_end < self.race_laps:
            raise ValueError("pit window must be within laps 1 through race_laps - 1")

        models = tuple(self.tire_degradation)
        if not models:
            raise ValueError("at least one tire degradation assumption is required")
        compounds = [model.compound for model in models]
        if len(compounds) != len(set(compounds)):
            raise ValueError("tire_degradation cannot contain duplicate compounds")
        object.__setattr__(self, "tire_degradation", models)
        if any(self.baseline_lap_time_s + model.pace_offset_s <= 0 for model in models):
            raise ValueError("baseline_lap_time_s plus each pace_offset_s must be positive")

        if not any(
            self._stint_length_is_feasible(pit_lap)
            for pit_lap in range(self.pit_window_start_lap, pit_window_end + 1)
        ):
            raise ValueError("pit window contains no pit lap that satisfies stint-length limits")

    def _stint_length_is_feasible(self, pit_lap: int) -> bool:
        first_length = pit_lap
        second_length = self.race_laps - pit_lap
        maximum = self.max_stint_laps
        assert maximum is not None
        return all(
            self.min_stint_laps <= length <= maximum
            for length in (first_length, second_length)
        )


@dataclass(frozen=True, slots=True)
class Stint:
    """One contiguous, one-based race segment and its modeled time."""

    compound: TireCompound
    start_lap: int
    end_lap: int
    lap_count: int
    estimated_time_s: float

    def __post_init__(self) -> None:
        if not isinstance(self.compound, TireCompound) or self.compound is TireCompound.UNKNOWN:
            raise ValueError("compound must be a known tire compound")
        _require_integer(self.start_lap, name="start_lap", minimum=1)
        _require_integer(self.end_lap, name="end_lap", minimum=self.start_lap)
        _require_integer(self.lap_count, name="lap_count", minimum=1)
        if self.lap_count != self.end_lap - self.start_lap + 1:
            raise ValueError("lap_count must match the inclusive stint boundaries")
        _require_finite_number(
            self.estimated_time_s,
            name="estimated_time_s",
            minimum=0.0,
        )
        if self.estimated_time_s == 0:
            raise ValueError("estimated_time_s must be greater than zero")


@dataclass(frozen=True, slots=True)
class RaceStrategy:
    """A complete one-stop race plan and its estimated total time."""

    race_laps: int
    pit_lap: int
    stints: tuple[Stint, Stint]
    pit_stop_loss_s: float
    estimated_total_time_s: float

    def __post_init__(self) -> None:
        _require_integer(self.race_laps, name="race_laps", minimum=2)
        _require_integer(self.pit_lap, name="pit_lap", minimum=1)
        if len(self.stints) != 2:
            raise ValueError("a one-stop strategy must contain exactly two stints")
        first, second = self.stints
        if first.start_lap != 1 or first.end_lap != self.pit_lap:
            raise ValueError("first stint must cover laps 1 through pit_lap")
        if second.start_lap != self.pit_lap + 1 or second.end_lap != self.race_laps:
            raise ValueError("second stint must cover pit_lap + 1 through race_laps")
        _require_finite_number(
            self.pit_stop_loss_s,
            name="pit_stop_loss_s",
            minimum=0.0,
        )
        _require_finite_number(
            self.estimated_total_time_s,
            name="estimated_total_time_s",
            minimum=0.0,
        )
        expected = first.estimated_time_s + second.estimated_time_s + self.pit_stop_loss_s
        if not isclose(self.estimated_total_time_s, expected, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("estimated_total_time_s must include both stints and pit-stop loss")


@dataclass(frozen=True, slots=True)
class StrategyAlternative:
    """A ranked alternative and its time loss relative to the recommendation."""

    strategy: RaceStrategy
    time_delta_s: float


@dataclass(frozen=True, slots=True)
class StrategyRecommendation:
    """Fastest modeled strategy, alternatives, assumptions, and explanation."""

    recommended: RaceStrategy
    alternatives: tuple[StrategyAlternative, ...]
    assumptions: StrategyConfig
    explanation: str


def estimate_lap_time(
    baseline_lap_time_s: float,
    degradation_s_per_lap: float,
    tyre_age_laps: int,
) -> float:
    """Estimate lap time using linear degradation and zero-based tire age."""
    _require_finite_number(
        baseline_lap_time_s,
        name="baseline_lap_time_s",
        minimum=0.0,
    )
    if baseline_lap_time_s == 0:
        raise ValueError("baseline_lap_time_s must be greater than zero")
    _require_finite_number(
        degradation_s_per_lap,
        name="degradation_s_per_lap",
        minimum=0.0,
    )
    _require_integer(tyre_age_laps, name="tyre_age_laps", minimum=0)
    return baseline_lap_time_s + degradation_s_per_lap * tyre_age_laps


def estimate_stint(
    compound: TireCompound,
    start_lap: int,
    lap_count: int,
    baseline_lap_time_s: float,
    degradation_s_per_lap: float,
) -> Stint:
    """Estimate a stint by summing the modeled lap time at each tire age."""
    _require_integer(start_lap, name="start_lap", minimum=1)
    _require_integer(lap_count, name="lap_count", minimum=1)
    total_time = sum(
        estimate_lap_time(baseline_lap_time_s, degradation_s_per_lap, age)
        for age in range(lap_count)
    )
    return Stint(
        compound=compound,
        start_lap=start_lap,
        end_lap=start_lap + lap_count - 1,
        lap_count=lap_count,
        estimated_time_s=total_time,
    )


def generate_one_stop_strategies(config: StrategyConfig) -> tuple[RaceStrategy, ...]:
    """Generate every unique feasible one-stop compound/pit-lap combination."""
    models = sorted(config.tire_degradation, key=lambda model: model.compound.value)
    candidates: list[RaceStrategy] = []
    assert config.pit_window_end_lap is not None
    assert config.max_stint_laps is not None

    for pit_lap in range(config.pit_window_start_lap, config.pit_window_end_lap + 1):
        first_length = pit_lap
        second_length = config.race_laps - pit_lap
        if not all(
            config.min_stint_laps <= length <= config.max_stint_laps
            for length in (first_length, second_length)
        ):
            continue

        for first_model, second_model in product(models, repeat=2):
            first = estimate_stint(
                first_model.compound,
                1,
                first_length,
                config.baseline_lap_time_s + first_model.pace_offset_s,
                first_model.seconds_per_lap,
            )
            second = estimate_stint(
                second_model.compound,
                pit_lap + 1,
                second_length,
                config.baseline_lap_time_s + second_model.pace_offset_s,
                second_model.seconds_per_lap,
            )
            candidates.append(
                RaceStrategy(
                    race_laps=config.race_laps,
                    pit_lap=pit_lap,
                    stints=(first, second),
                    pit_stop_loss_s=config.pit_stop_loss_s,
                    estimated_total_time_s=(
                        first.estimated_time_s
                        + second.estimated_time_s
                        + config.pit_stop_loss_s
                    ),
                )
            )

    return tuple(sorted(candidates, key=_strategy_sort_key))


def recommend_strategy(config: StrategyConfig) -> StrategyRecommendation:
    """Rank feasible strategies and return the fastest plus time-delta alternatives."""
    ranked = generate_one_stop_strategies(config)
    if not ranked:
        raise ValueError("no feasible one-stop strategies for the supplied configuration")

    best = ranked[0]
    alternatives = tuple(
        StrategyAlternative(
            strategy=strategy,
            time_delta_s=strategy.estimated_total_time_s - best.estimated_total_time_s,
        )
        for strategy in ranked[1:]
    )
    explanation = (
        f"Ranks first at {best.estimated_total_time_s:.3f}s among {len(ranked)} feasible "
        "one-stop strategies under the configured compound-pace and linear "
        "tire-degradation assumptions."
    )
    return StrategyRecommendation(
        recommended=best,
        alternatives=alternatives,
        assumptions=config,
        explanation=explanation,
    )


def _strategy_sort_key(strategy: RaceStrategy) -> tuple[float, int, str, str]:
    first, second = strategy.stints
    return (
        strategy.estimated_total_time_s,
        strategy.pit_lap,
        first.compound.value,
        second.compound.value,
    )
