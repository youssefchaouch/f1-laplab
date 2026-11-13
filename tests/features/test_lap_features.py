"""Offline tests for leakage-safe pre-lap feature construction."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import pandas.testing as pdt
import pytest

from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.errors import InsufficientDataError, SchemaValidationError
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.features import (
    FEATURE_COLUMNS,
    IDENTIFIER_COLUMNS,
    TARGET_COLUMN,
    ExcludedLap,
    LapFeatureDataset,
    build_lap_features,
)
from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.validation import validate_laps, validate_laps_with_report


def _raw_rows(
    template: pd.DataFrame,
    laps: Iterable[dict[str, object]],
) -> pd.DataFrame:
    """Build FastF1-shaped fixture data from explicit lap observations."""
    base = template.iloc[0]
    rows: list[pd.Series] = []
    for lap in laps:
        row = base.copy()
        row["Driver"] = str(lap.get("driver", "VER"))
        row["Team"] = str(lap.get("team", "Red Bull Racing"))
        lap_number = lap["lap"]
        if not isinstance(lap_number, int):
            raise TypeError("lap number fixture values must be integers")
        row["LapNumber"] = lap_number
        seconds = lap.get("time_s")
        if seconds is not None and not isinstance(seconds, (int, float)):
            raise TypeError("lap time fixture values must be numeric or None")
        row["LapTime"] = pd.NaT if seconds is None else pd.Timedelta(seconds, unit="s")
        row["IsAccurate"] = bool(lap.get("accurate", True))
        row["Deleted"] = bool(lap.get("deleted", False))
        row["PitInTime"] = pd.NaT if not lap.get("pit_in", False) else pd.Timedelta(1, unit="s")
        row["PitOutTime"] = (
            pd.NaT if not lap.get("pit_out", False) else pd.Timedelta(1, unit="s")
        )
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


def _row_index(result: LapFeatureDataset, driver: str, lap_number: int) -> int:
    identifiers = result.identifiers
    matches = identifiers.index[
        identifiers["driver"].eq(driver)
        & identifiers["lap_number"].eq(lap_number)
    ]
    assert len(matches) == 1
    return int(matches[0])


def _features_for(result: LapFeatureDataset, driver: str, lap_number: int) -> pd.Series:
    return result.features.iloc[_row_index(result, driver, lap_number)]


def _label_for(result: LapFeatureDataset, driver: str, lap_number: int) -> float:
    return float(result.labels.iloc[_row_index(result, driver, lap_number)])


def test_target_population_excludes_invalid_but_keeps_valid_special_laps(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    excluded_rows = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 3, "time_s": 80.0, "deleted": True},
            {"lap": 4, "time_s": None},
        ],
    )
    result = build_lap_features(
        _loaded_session(pd.concat([raw_fastf1_laps, excluded_rows], ignore_index=True))
    )

    assert result.identifiers["driver"].tolist() == ["VER", "VER"]
    assert result.identifiers["lap_number"].tolist() == [1, 2]
    assert result.labels.name == TARGET_COLUMN
    assert result.excluded_laps[0].driver == "LEC"
    assert result.excluded_laps[0].reasons == ("inaccurate_lap", "missing_lap_time")
    assert ExcludedLap("VER", 3, ("deleted_lap",)) in result.excluded_laps
    assert ExcludedLap("VER", 4, ("missing_lap_time",)) in result.excluded_laps
    assert _label_for(result, "VER", 2) == pytest.approx(73.9)


def test_duplicate_eligible_target_identities_raise_instead_of_dropping_rows(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    duplicated = pd.concat([raw_fastf1_laps, raw_fastf1_laps.iloc[[0]]], ignore_index=True)

    with pytest.raises(SchemaValidationError, match="Duplicate eligible target identities"):
        build_lap_features(_loaded_session(duplicated))


def test_invalid_duplicate_does_not_remove_the_single_eligible_target(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    invalid_copy = raw_fastf1_laps.iloc[[0]].copy()
    invalid_copy["IsAccurate"] = False
    raw = pd.concat([raw_fastf1_laps, invalid_copy], ignore_index=True)
    session = _loaded_session(raw)

    report = validate_laps_with_report(session.laps)
    result = build_lap_features(session)

    assert len(report.cleaned_laps) < int(session.laps[S.IS_VALID].sum())
    assert result.identifiers.query("driver == 'VER' and lap_number == 1").shape[0] == 1
    assert len(result.labels) == int(session.laps[S.IS_VALID].sum())


def test_labels_and_identifiers_are_separate_from_model_features(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    result = build_lap_features(_loaded_session(raw_fastf1_laps))

    assert list(result.features.columns) == list(FEATURE_COLUMNS)
    assert TARGET_COLUMN not in result.features.columns
    assert list(result.identifiers.columns) == list(IDENTIFIER_COLUMNS)
    assert not set(IDENTIFIER_COLUMNS).intersection(result.features.columns)
    assert result.labels.name == TARGET_COLUMN


def test_target_time_perturbation_changes_label_but_not_its_features(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    changed = raw_fastf1_laps.copy()
    changed.loc[1, "LapTime"] = pd.Timedelta(99.0, unit="s")
    original_result = build_lap_features(_loaded_session(raw_fastf1_laps))
    changed_result = build_lap_features(_loaded_session(changed))

    pdt.assert_series_equal(
        _features_for(original_result, "VER", 2),
        _features_for(changed_result, "VER", 2),
    )
    assert _label_for(original_result, "VER", 2) != _label_for(changed_result, "VER", 2)


def test_future_time_and_event_perturbations_do_not_change_earlier_features(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 70.0},
            {"lap": 2, "time_s": 71.0},
            {"lap": 3, "time_s": 72.0},
            {"lap": 4, "time_s": 73.0},
            {"lap": 5, "time_s": 74.0},
        ],
    )
    changed = raw.copy()
    changed.loc[changed["LapNumber"] > 3, "LapTime"] = pd.to_timedelta(
        ["0:02:00", "0:02:01"]
    )
    changed["PitInTime"] = changed["PitInTime"].astype(object)
    changed["PitOutTime"] = changed["PitOutTime"].astype(object)
    changed.loc[changed["LapNumber"] > 3, "PitInTime"] = pd.Timedelta(1, unit="s")
    changed.loc[changed["LapNumber"] > 3, "PitOutTime"] = pd.Timedelta(1, unit="s")
    changed.loc[changed["LapNumber"] > 3, "TrackStatus"] = "4"
    original_result = build_lap_features(_loaded_session(raw))
    changed_result = build_lap_features(_loaded_session(changed))

    pdt.assert_series_equal(
        _features_for(original_result, "VER", 3),
        _features_for(changed_result, "VER", 3),
    )


def test_appending_later_eligible_lap_preserves_earlier_target_features(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    initial = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 70.0},
            {"lap": 2, "time_s": 71.0},
            {"lap": 3, "time_s": 72.0},
        ],
    )
    appended_lap = _raw_rows(initial, [{"lap": 4, "time_s": 73.0}])
    extended = pd.concat([initial, appended_lap], ignore_index=True)
    original_result = build_lap_features(_loaded_session(initial))
    extended_result = build_lap_features(_loaded_session(extended))

    def target_mask(result: LapFeatureDataset) -> pd.Series:
        identifiers = result.identifiers
        return (
            identifiers["session_year"].eq(2024)
            & identifiers["grand_prix"].eq("Monaco")
            & identifiers["session"].eq(SessionType.RACE.value)
            & identifiers["driver"].eq("VER")
            & identifiers["lap_number"].eq(3)
        )

    original_mask = target_mask(original_result)
    extended_mask = target_mask(extended_result)

    assert original_mask.sum() == extended_mask.sum() == 1
    original_features = original_result.features.loc[original_mask].iloc[0]
    extended_features = extended_result.features.loc[extended_mask].iloc[0]
    pdt.assert_series_equal(original_features, extended_features)
    assert original_features.isna().equals(extended_features.isna())
    assert len(extended_result.identifiers) == len(original_result.identifiers) + 1
    assert _row_index(extended_result, "VER", 4) >= 0


def test_exact_predecessor_does_not_fall_back_when_immediate_lap_is_invalid(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 70.0},
            {"lap": 2, "time_s": 71.0, "accurate": False},
            {"lap": 3, "time_s": 72.0},
        ],
    )
    result = build_lap_features(_loaded_session(raw))
    features = _features_for(result, "VER", 3)

    assert pd.isna(features["previous_lap_time_s"])
    assert features["prior_3lap_mean_time_s"] == pytest.approx(70.0)
    assert features["prior_3lap_valid_count"] == 1


def test_rolling_window_full_partial_empty_and_gap_behavior(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 10.0},
            {"lap": 2, "time_s": 20.0},
            {"lap": 3, "time_s": 30.0},
            {"lap": 4, "time_s": 40.0},
            {"lap": 5, "time_s": 50.0},
            {"lap": 6, "time_s": 60.0},
        ],
    )
    result = build_lap_features(_loaded_session(raw))

    assert _features_for(result, "VER", 1)["prior_3lap_valid_count"] == 0
    assert pd.isna(_features_for(result, "VER", 1)["prior_3lap_mean_time_s"])
    assert _features_for(result, "VER", 2)["prior_3lap_mean_time_s"] == pytest.approx(10.0)
    assert _features_for(result, "VER", 2)["prior_3lap_valid_count"] == 1
    assert _features_for(result, "VER", 4)["prior_3lap_mean_time_s"] == pytest.approx(20.0)
    assert _features_for(result, "VER", 4)["prior_3lap_valid_count"] == 3
    assert _features_for(result, "VER", 5)["prior_3lap_mean_time_s"] == pytest.approx(30.0)
    assert _features_for(result, "VER", 5)["previous_lap_time_s"] == pytest.approx(40.0)
    assert _features_for(result, "VER", 6)["prior_3lap_mean_time_s"] == pytest.approx(40.0)


def test_rolling_window_ignores_invalid_slots_and_values_older_than_boundary(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 10.0},
            {"lap": 2, "time_s": 20.0, "accurate": False},
            {"lap": 3, "time_s": 30.0},
            {"lap": 4, "time_s": 40.0},
            {"lap": 5, "time_s": 50.0},
            {"lap": 7, "time_s": 70.0},
        ],
    )
    result = build_lap_features(_loaded_session(raw))
    lap5 = _features_for(result, "VER", 5)
    lap7 = _features_for(result, "VER", 7)

    assert lap5["prior_3lap_mean_time_s"] == pytest.approx(35.0)
    assert lap5["prior_3lap_valid_count"] == 2
    assert pd.isna(lap7["previous_lap_time_s"])
    assert lap7["prior_3lap_mean_time_s"] == pytest.approx(45.0)
    assert lap7["prior_3lap_valid_count"] == 2


def test_first_lap_features_are_null_with_zero_history(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(raw_fastf1_laps, [{"lap": 1, "time_s": 70.0}])
    result = build_lap_features(_loaded_session(raw))
    first = result.features.iloc[0]

    assert pd.isna(first["previous_lap_time_s"])
    assert pd.isna(first["prior_3lap_mean_time_s"])
    assert first["prior_3lap_valid_count"] == 0


def test_valid_pit_and_non_clear_status_targets_remain_labels_not_features(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    result = build_lap_features(_loaded_session(raw_fastf1_laps))

    assert _label_for(result, "VER", 2) == pytest.approx(73.9)
    assert "IsPitInLap" not in result.features.columns
    assert "IsPitOutLap" not in result.features.columns
    assert "TrackStatus" not in result.features.columns


def test_valid_pit_out_lap_is_retained_as_target(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "time_s": 70.0},
            {"lap": 2, "time_s": 71.0, "pit_out": True},
        ],
    )
    result = build_lap_features(_loaded_session(raw))

    assert result.identifiers.loc[
        result.identifiers["lap_number"].eq(2), "driver"
    ].tolist() == ["VER"]
    assert _label_for(result, "VER", 2) == pytest.approx(71.0)


def test_output_is_deterministic_sorted_and_input_order_independent(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 3, "driver": "LEC", "time_s": 73.0},
            {"lap": 1, "driver": "VER", "time_s": 70.0},
            {"lap": 2, "driver": "VER", "time_s": 71.0},
            {"lap": 2, "driver": "LEC", "time_s": 72.0},
        ],
    )
    first = build_lap_features(_loaded_session(raw))
    repeated = build_lap_features(_loaded_session(raw))
    permuted = build_lap_features(_loaded_session(raw.sample(frac=1, random_state=7)))

    pdt.assert_frame_equal(first.identifiers, repeated.identifiers)
    pdt.assert_frame_equal(first.features, repeated.features)
    pdt.assert_series_equal(first.labels, repeated.labels)
    pdt.assert_frame_equal(first.identifiers, permuted.identifiers)
    pdt.assert_frame_equal(first.features, permuted.features)
    pdt.assert_series_equal(first.labels, permuted.labels)
    assert first.metadata == repeated.metadata == permuted.metadata


def test_identifiers_features_and_labels_align_with_unique_composite_keys(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    result = build_lap_features(_loaded_session(raw_fastf1_laps))
    keys = result.identifiers[list(IDENTIFIER_COLUMNS)]

    assert result.identifiers.index.equals(result.features.index)
    assert result.identifiers.index.equals(result.labels.index)
    assert len(keys.drop_duplicates()) == len(keys)
    assert len(keys) == len(result.features) == len(result.labels)
    assert list(result.features.columns) == list(FEATURE_COLUMNS)


def test_prior_history_is_isolated_by_driver(raw_fastf1_laps: pd.DataFrame) -> None:
    raw = _raw_rows(
        raw_fastf1_laps,
        [
            {"lap": 1, "driver": "VER", "time_s": 70.0},
            {"lap": 2, "driver": "VER", "time_s": 71.0},
            {"lap": 1, "driver": "LEC", "time_s": 80.0},
            {"lap": 2, "driver": "LEC", "time_s": 81.0},
        ],
    )
    result = build_lap_features(_loaded_session(raw))

    assert _features_for(result, "VER", 2)["previous_lap_time_s"] == pytest.approx(70.0)
    assert _features_for(result, "LEC", 2)["previous_lap_time_s"] == pytest.approx(80.0)


def test_output_types_nullable_values_and_metadata_are_explicit(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    result = build_lap_features(_loaded_session(raw_fastf1_laps))

    assert str(result.features["previous_lap_time_s"].dtype) == "Float64"
    assert str(result.features["prior_3lap_mean_time_s"].dtype) == "Float64"
    assert str(result.features["prior_3lap_valid_count"].dtype) == "int64"
    assert str(result.labels.dtype) == "float64"
    assert result.metadata.source.ref == SessionRef(2024, "Monaco", SessionType.RACE)
    assert result.metadata.prediction_cutoff == "immediately_before_target_lap_begins"
    assert result.metadata.target_name == TARGET_COLUMN
    assert result.metadata.target_unit == "seconds"
    assert result.metadata.history_window_lap_offsets == (-3, -1)


def test_empty_and_malformed_inputs_raise_clear_domain_errors(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    empty_session = _loaded_session(raw_fastf1_laps.iloc[:0].copy())
    with pytest.raises(InsufficientDataError, match="empty session"):
        build_lap_features(empty_session)

    malformed = _loaded_session(raw_fastf1_laps)
    malformed.laps.drop(columns=[S.COMPOUND], inplace=True)
    with pytest.raises(SchemaValidationError):
        build_lap_features(malformed)


def test_sessions_with_no_eligible_targets_raise_insufficient_data(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.copy()
    raw["IsAccurate"] = False

    with pytest.raises(InsufficientDataError, match="no canonically valid timed"):
        build_lap_features(_loaded_session(raw))
