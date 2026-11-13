"""Offline tests for baseline lap-time models and weekend-held-out evaluation."""

from __future__ import annotations

import math
from collections.abc import Callable

import pandas as pd
import pytest

from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.errors import InsufficientDataError
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.features import LapFeatureDataset, build_lap_features
from f1strategy.modeling import (
    MODEL_NAMES,
    RidgeLapTimeModel,
    evaluate_leave_one_weekend_out,
    predict_naive_previous_lap,
    predict_naive_prior_mean,
)
from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.validation import validate_laps

LapTimeFn = Callable[[int, int], float]


def _dataset(
    grand_prix: str,
    lap_time: LapTimeFn,
    *,
    year: int = 2024,
    session: SessionType = SessionType.RACE,
    drivers: int = 3,
    laps: int = 12,
    deleted: frozenset[tuple[int, int]] = frozenset(),
) -> LapFeatureDataset:
    rows = [(d, n) for d in range(drivers) for n in range(1, laps + 1)]
    raw = pd.DataFrame(
        {
            S.DRIVER: [f"D{d:02d}" for d, _ in rows],
            S.TEAM: ["Synthetic Team"] * len(rows),
            S.LAP_NUMBER: [n for _, n in rows],
            S.STINT: [1] * len(rows),
            S.COMPOUND: ["MEDIUM"] * len(rows),
            S.TYRE_LIFE: [n for _, n in rows],
            "LapTime": pd.to_timedelta([lap_time(d, n) for d, n in rows], unit="s"),
            S.IS_ACCURATE: [True] * len(rows),
            S.DELETED: [(d, n) in deleted for d, n in rows],
            "PitInTime": pd.to_timedelta([pd.NaT] * len(rows)),
            "PitOutTime": pd.to_timedelta([pd.NaT] * len(rows)),
            S.TRACK_STATUS: ["1"] * len(rows),
        }
    )
    frame = validate_laps(fastf1_laps_to_frame(raw))
    ref = SessionRef(year, grand_prix, session)
    metadata = SessionMetadata(
        ref=ref,
        event_name=grand_prix,
        circuit="Synthetic Circuit",
        country="Not applicable",
        n_drivers=drivers,
        n_laps=len(frame),
        loaded_with_telemetry=False,
    )
    return build_lap_features(LoadedSession(metadata=metadata, laps=frame))


def _degrading(base: float, per_lap: float) -> LapTimeFn:
    return lambda driver, lap: base + 0.2 * driver + per_lap * lap


def test_naive_previous_lap_falls_back_to_prior_mean_and_skips_unpredictable_rows() -> None:
    dataset = _dataset("A", _degrading(90.0, 0.1), drivers=1, laps=5, deleted=frozenset({(0, 3)}))
    prediction = predict_naive_previous_lap(dataset.features)
    by_lap = dict(zip(dataset.identifiers["lap_number"], prediction, strict=True))

    assert pd.isna(by_lap[1])
    assert by_lap[2] == pytest.approx(90.1)
    assert by_lap[4] == pytest.approx((90.1 + 90.2) / 2)


def test_naive_prior_mean_matches_feature() -> None:
    dataset = _dataset("A", _degrading(90.0, 0.1))
    prediction = predict_naive_prior_mean(dataset.features)

    assert prediction.equals(dataset.features["prior_3lap_mean_time_s"].astype("Float64"))


def test_ridge_learns_constant_degradation_without_absolute_pace() -> None:
    model = RidgeLapTimeModel.fit(
        [_dataset("A", _degrading(80.0, 0.1)), _dataset("B", _degrading(100.0, 0.1))],
        alpha=0.0,
    )
    held_out = _dataset("C", _degrading(70.0, 0.1), drivers=1)
    prediction = model.predict(held_out.features)
    rows = held_out.features["prior_3lap_valid_count"] == 3

    assert prediction[rows].to_numpy(dtype="float64") == pytest.approx(
        held_out.labels[rows].to_numpy(), abs=1e-6
    )


def test_ridge_rows_without_history_are_not_predicted() -> None:
    model = RidgeLapTimeModel.fit([_dataset("A", _degrading(90.0, 0.1))])
    dataset = _dataset("B", _degrading(90.0, 0.1))
    prediction = model.predict(dataset.features)
    first_laps = dataset.identifiers["lap_number"] == 1

    assert prediction[first_laps].isna().all()
    assert prediction[~first_laps].notna().all()


def test_ridge_fit_requires_enough_rows_and_valid_alpha() -> None:
    tiny = _dataset("A", _degrading(90.0, 0.1), drivers=1, laps=3)
    with pytest.raises(InsufficientDataError):
        RidgeLapTimeModel.fit([tiny])
    with pytest.raises(ValueError, match="alpha"):
        RidgeLapTimeModel.fit([_dataset("A", _degrading(90.0, 0.1))], alpha=-1.0)


def test_ridge_is_deterministic() -> None:
    data = [_dataset("A", _degrading(90.0, 0.1)), _dataset("B", _degrading(85.0, 0.2))]

    assert RidgeLapTimeModel.fit(data) == RidgeLapTimeModel.fit(data)


def test_evaluation_needs_two_weekends() -> None:
    race = _dataset("A", _degrading(90.0, 0.1))
    practice = _dataset("A", _degrading(91.0, 0.1), session=SessionType.PRACTICE_1)
    with pytest.raises(InsufficientDataError, match="2 race weekends"):
        evaluate_leave_one_weekend_out([race, practice])


def test_evaluation_holds_out_whole_weekends_and_scores_models_on_same_rows() -> None:
    datasets = [
        _dataset("A", _degrading(80.0, 0.1)),
        _dataset("A", _degrading(81.0, 0.1), session=SessionType.PRACTICE_1),
        _dataset("B", _degrading(95.0, 0.1)),
        _dataset("C", _degrading(70.0, 0.1)),
    ]
    report = evaluate_leave_one_weekend_out(datasets, alpha=0.0)

    assert [result.weekend for result in report.weekends] == [(2024, "A"), (2024, "B"), (2024, "C")]
    weekend_a = report.weekends[0]
    assert weekend_a.target_rows == 72
    assert weekend_a.predictable_rows == 66
    assert {m.rows for m in weekend_a.metrics.values()} == {66}
    assert set(report.pooled) == set(MODEL_NAMES)
    assert report.pooled["ridge_deviation"].rows == 66 + 33 + 33


def test_learned_model_beats_naive_baselines_on_learnable_synthetic_pattern() -> None:
    # Synthetic, noise-free degradation: a sanity check of the mechanics, not a
    # claim about performance on real Formula 1 data.
    weekends = [("A", 80.0), ("B", 95.0), ("C", 70.0)]
    datasets = [_dataset(gp, _degrading(base, 0.15)) for gp, base in weekends]
    pooled = evaluate_leave_one_weekend_out(datasets, alpha=0.0).pooled

    assert pooled["ridge_deviation"].mae_s < pooled["naive_previous_lap"].mae_s
    assert pooled["naive_previous_lap"].mae_s < pooled["naive_prior_mean"].mae_s
    assert all(math.isfinite(m.rmse_s) for m in pooled.values())
