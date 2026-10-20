"""Offline tests for the deterministic baseline race strategy engine."""

from __future__ import annotations

import math

import pytest

from f1strategy.domain.enums import TireCompound
from f1strategy.strategy import (
    StrategyConfig,
    TireDegradation,
    estimate_lap_time,
    estimate_stint,
    generate_one_stop_strategies,
    recommend_strategy,
)


def _config(
    *,
    race_laps: int = 12,
    baseline_lap_time_s: float = 90.0,
    pit_stop_loss_s: float = 20.0,
    tire_degradation: tuple[TireDegradation, ...] | None = None,
    min_stint_laps: int = 3,
    max_stint_laps: int | None = 9,
    pit_window_start_lap: int = 3,
    pit_window_end_lap: int | None = 9,
) -> StrategyConfig:
    assumptions = (
        tire_degradation
        if tire_degradation is not None
        else (
            TireDegradation(TireCompound.SOFT, 0.08),
            TireDegradation(TireCompound.MEDIUM, 0.05),
            TireDegradation(TireCompound.HARD, 0.03),
        )
    )
    return StrategyConfig(
        race_laps=race_laps,
        baseline_lap_time_s=baseline_lap_time_s,
        pit_stop_loss_s=pit_stop_loss_s,
        tire_degradation=assumptions,
        min_stint_laps=min_stint_laps,
        max_stint_laps=max_stint_laps,
        pit_window_start_lap=pit_window_start_lap,
        pit_window_end_lap=pit_window_end_lap,
    )


def test_lap_time_increases_linearly_with_zero_based_tire_age() -> None:
    assert estimate_lap_time(90.0, 0.2, 0) == 90.0
    assert estimate_lap_time(90.0, 0.2, 3) == 90.6


def test_stint_time_sums_lap_time_for_each_tire_age() -> None:
    stint = estimate_stint(TireCompound.MEDIUM, 4, 3, 90.0, 0.5)

    assert stint.compound is TireCompound.MEDIUM
    assert (stint.start_lap, stint.end_lap, stint.lap_count) == (4, 6, 3)
    assert stint.estimated_time_s == 271.5


@pytest.mark.parametrize("race_laps", [0, 1, -4, True])
def test_invalid_race_distance_is_rejected(race_laps: int) -> None:
    with pytest.raises(ValueError, match="race_laps"):
        _config(race_laps=race_laps)


@pytest.mark.parametrize("baseline", [0.0, -1.0, math.inf, math.nan])
def test_invalid_baseline_lap_time_is_rejected(baseline: float) -> None:
    with pytest.raises(ValueError, match="baseline_lap_time_s"):
        _config(baseline_lap_time_s=baseline)


def test_negative_pit_loss_is_rejected() -> None:
    with pytest.raises(ValueError, match="pit_stop_loss_s"):
        _config(pit_stop_loss_s=-1.0)


def test_invalid_degradation_assumptions_are_rejected() -> None:
    with pytest.raises(ValueError, match="seconds_per_lap"):
        TireDegradation(TireCompound.SOFT, -0.1)
    with pytest.raises(ValueError, match="known tire compound"):
        TireDegradation(TireCompound.UNKNOWN, 0.1)


def test_duplicate_compound_assumptions_are_rejected() -> None:
    assumption = TireDegradation(TireCompound.SOFT, 0.1)
    with pytest.raises(ValueError, match="duplicate compounds"):
        _config(tire_degradation=(assumption, assumption))


def test_empty_compound_assumptions_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        _config(tire_degradation=())


def test_impossible_stint_constraints_are_rejected() -> None:
    with pytest.raises(ValueError, match="too short"):
        _config(race_laps=5, min_stint_laps=3)
    with pytest.raises(ValueError, match="max_stint_laps"):
        _config(min_stint_laps=5, max_stint_laps=4)
    with pytest.raises(ValueError, match="no pit lap"):
        _config(
            min_stint_laps=4,
            max_stint_laps=5,
            pit_window_start_lap=2,
            pit_window_end_lap=2,
        )


def test_invalid_pit_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="pit window"):
        _config(pit_window_start_lap=10, pit_window_end_lap=12)


def test_generator_respects_pit_window_and_stint_lengths() -> None:
    strategies = generate_one_stop_strategies(_config())

    assert strategies
    for strategy in strategies:
        assert 3 <= strategy.pit_lap <= 9
        assert all(3 <= stint.lap_count <= 9 for stint in strategy.stints)


def test_each_strategy_covers_race_once_and_has_consistent_time() -> None:
    config = _config()
    strategies = generate_one_stop_strategies(config)

    for strategy in strategies:
        first, second = strategy.stints
        assert (first.start_lap, first.end_lap) == (1, strategy.pit_lap)
        assert (second.start_lap, second.end_lap) == (
            strategy.pit_lap + 1,
            config.race_laps,
        )
        assert first.lap_count + second.lap_count == config.race_laps
        assert strategy.estimated_total_time_s == pytest.approx(
            first.estimated_time_s + second.estimated_time_s + config.pit_stop_loss_s
        )


def test_pit_stop_loss_is_included_once() -> None:
    config = _config(
        race_laps=6,
        baseline_lap_time_s=90.0,
        pit_stop_loss_s=17.0,
        tire_degradation=(TireDegradation(TireCompound.SOFT, 0.0),),
        min_stint_laps=3,
        max_stint_laps=3,
        pit_window_start_lap=3,
        pit_window_end_lap=3,
    )

    strategy = generate_one_stop_strategies(config)[0]

    assert strategy.estimated_total_time_s == 557.0


def test_generated_strategies_have_no_duplicates() -> None:
    strategies = generate_one_stop_strategies(_config())
    keys = {
        (strategy.pit_lap, strategy.stints[0].compound, strategy.stints[1].compound)
        for strategy in strategies
    }

    assert len(strategies) == len(keys)


def test_recommendation_ranks_fastest_and_reports_alternative_deltas() -> None:
    recommendation = recommend_strategy(_config())
    ranked = (recommendation.recommended,) + tuple(
        alternative.strategy for alternative in recommendation.alternatives
    )

    assert recommendation.recommended.estimated_total_time_s == min(
        strategy.estimated_total_time_s for strategy in ranked
    )
    assert all(
        alternative.time_delta_s
        == pytest.approx(
            alternative.strategy.estimated_total_time_s
            - recommendation.recommended.estimated_total_time_s
        )
        for alternative in recommendation.alternatives
    )
    assert recommendation.assumptions == _config()
    assert "Ranks first" in recommendation.explanation


def test_equal_time_strategies_are_all_retained_with_zero_deltas() -> None:
    config = _config(
        tire_degradation=(
            TireDegradation(TireCompound.SOFT, 0.0),
            TireDegradation(TireCompound.HARD, 0.0),
        ),
        pit_stop_loss_s=0.0,
    )

    recommendation = recommend_strategy(config)

    assert recommendation.recommended.estimated_total_time_s == 12 * 90.0
    assert all(alternative.time_delta_s == 0.0 for alternative in recommendation.alternatives)
    assert len({alternative.strategy for alternative in recommendation.alternatives}) == len(
        recommendation.alternatives
    )


def test_identical_inputs_produce_identical_rankings() -> None:
    config = _config()

    assert recommend_strategy(config) == recommend_strategy(config)
