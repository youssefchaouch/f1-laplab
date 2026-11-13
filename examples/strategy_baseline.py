"""Rank one-stop race strategies with the deterministic baseline engine.

Every number below is an illustrative assumption, not a calibrated value for any
real circuit, car, or tyre. The script makes no network request and reads no data.
"""

from __future__ import annotations

from f1strategy.domain.enums import TireCompound
from f1strategy.strategy import StrategyConfig, TireDegradation, recommend_strategy

TOP_ALTERNATIVES = 5


def build_config() -> StrategyConfig:
    """Return an explicitly illustrative one-stop race configuration."""
    return StrategyConfig(
        race_laps=57,
        baseline_lap_time_s=92.0,
        pit_stop_loss_s=21.0,
        tire_degradation=(
            TireDegradation(TireCompound.SOFT, seconds_per_lap=0.09, pace_offset_s=-0.7),
            TireDegradation(TireCompound.MEDIUM, seconds_per_lap=0.06, pace_offset_s=-0.3),
            TireDegradation(TireCompound.HARD, seconds_per_lap=0.04, pace_offset_s=0.0),
        ),
        min_stint_laps=10,
        max_stint_laps=40,
        pit_window_start_lap=15,
        pit_window_end_lap=42,
    )


def main() -> None:
    config = build_config()
    result = recommend_strategy(config)
    best = result.recommended

    print("F1 LapLab one-stop strategy baseline (illustrative assumptions; not real race data).")
    print(
        f"Race: {config.race_laps} laps, baseline {config.baseline_lap_time_s:.1f}s/lap, "
        f"pit loss {config.pit_stop_loss_s:.1f}s, pit window laps "
        f"{config.pit_window_start_lap}-{config.pit_window_end_lap}"
    )
    print()
    print("Recommended:")
    for stint in best.stints:
        print(
            f"  {stint.compound.value:<6} laps {stint.start_lap:>2}-{stint.end_lap:<2} "
            f"({stint.lap_count} laps, {stint.estimated_time_s:.3f}s)"
        )
    print(f"  Pit after lap {best.pit_lap}; total {best.estimated_total_time_s:.3f}s")
    print(f"  {result.explanation}")
    print()
    print(f"Next {TOP_ALTERNATIVES} alternatives:")
    for alternative in result.alternatives[:TOP_ALTERNATIVES]:
        plan = alternative.strategy
        compounds = " -> ".join(stint.compound.value for stint in plan.stints)
        print(
            f"  +{alternative.time_delta_s:7.3f}s  pit lap {plan.pit_lap:>2}  {compounds}"
        )


if __name__ == "__main__":
    main()
