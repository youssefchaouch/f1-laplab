"""Tests for the FastF1 -> domain conversion and validation (no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.errors import SchemaValidationError
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.telemetry.conversion import fastf1_laps_to_frame, lap_records_from_session
from f1strategy.telemetry.validation import (
    filter_valid_laps,
    validate_laps,
    validate_laps_with_report,
)


def test_conversion_produces_exact_schema_columns(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    assert list(frame.columns) == list(S.LAPS_COLUMNS)


def test_laptime_converted_to_float_seconds(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    assert frame[S.LAP_TIME_S].dtype == "float64"
    # 0:01:14.5 -> 74.5 s
    assert frame.loc[0, S.LAP_TIME_S] == 74.5


def test_unknown_compound_is_normalized(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    assert frame.loc[1, S.COMPOUND] == "SOFT"      # lower-case "soft" normalized
    assert frame.loc[2, S.COMPOUND] == "UNKNOWN"   # null -> UNKNOWN


def test_is_valid_derivation(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    # Row 2 had IsAccurate=False and no LapTime -> invalid.
    assert frame.loc[0, S.IS_VALID]
    assert not frame.loc[2, S.IS_VALID]


def test_pit_event_times_are_preserved_as_nullable_lap_flags(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)

    assert frame.loc[0, S.IS_PIT_OUT_LAP]
    assert frame.loc[1, S.IS_PIT_IN_LAP]
    assert frame[S.IS_PIT_IN_LAP].dtype.name == "boolean"


def test_track_status_is_preserved_and_non_clear_laps_are_reported(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    report = validate_laps_with_report(frame)

    assert frame.loc[1, S.TRACK_STATUS] == "2"
    issue = next(item for item in report.issues if item.lap_number == 2)
    assert "non_clear_track_status" in issue.reasons
    assert not issue.excluded


def test_missing_pit_event_columns_remain_unknown(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.drop(
        columns=["PitInTime", "PitOutTime", S.TRACK_STATUS]
    )
    frame = validate_laps(fastf1_laps_to_frame(raw))

    assert frame[S.IS_PIT_IN_LAP].isna().all()
    assert frame[S.IS_PIT_OUT_LAP].isna().all()
    assert frame[S.TRACK_STATUS].isna().all()


def test_validate_then_filter_valid_laps(raw_fastf1_laps: pd.DataFrame) -> None:
    validated = validate_laps(fastf1_laps_to_frame(raw_fastf1_laps))
    valid = filter_valid_laps(validated)
    assert len(valid) == 2
    assert valid[S.IS_VALID].all()


def test_missing_optional_stint_and_tyre_life_are_preserved(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.drop(columns=["Stint", "TyreLife"])
    frame = validate_laps(fastf1_laps_to_frame(raw))
    assert frame[S.STINT].isna().all()
    assert frame[S.TYRE_LIFE].isna().all()


def test_incomplete_optional_values_are_preserved_as_missing(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.copy()
    raw["Stint"] = pd.Series([1, pd.NA, 2], dtype="Int64")
    raw["TyreLife"] = pd.Series([pd.NA, 2, 3], dtype="Int64")
    frame = validate_laps(fastf1_laps_to_frame(raw))
    assert bool(frame[S.STINT].isna().loc[1])
    assert bool(frame[S.TYRE_LIFE].isna().loc[0])


def test_missing_required_lap_flags_are_rejected(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.copy()
    raw[S.IS_ACCURATE] = pd.Series([True, pd.NA, False], dtype="boolean")
    with pytest.raises(SchemaValidationError, match="IsAccurate"):
        fastf1_laps_to_frame(raw)


def test_missing_deleted_values_are_rejected(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.copy()
    raw[S.DELETED] = pd.Series([False, pd.NA, False], dtype="boolean")
    with pytest.raises(SchemaValidationError, match="Deleted"):
        fastf1_laps_to_frame(raw)


def test_invalid_lap_number_is_not_replaced_with_a_default(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.assign(LapNumber=[0, 2, 1])
    with pytest.raises(SchemaValidationError):
        validate_laps(fastf1_laps_to_frame(raw))


@pytest.mark.parametrize("lap_time_s", [0.0, -1.0])
def test_non_positive_lap_times_are_rejected(
    raw_fastf1_laps: pd.DataFrame,
    lap_time_s: float,
) -> None:
    raw = raw_fastf1_laps.copy()
    raw.loc[0, "LapTime"] = pd.Timedelta(lap_time_s, unit="s")

    with pytest.raises(SchemaValidationError):
        validate_laps(fastf1_laps_to_frame(raw))


def test_inconsistent_is_valid_flag_is_rejected(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    frame.loc[0, S.IS_VALID] = False

    with pytest.raises(SchemaValidationError, match="IsValid must equal"):
        validate_laps(frame)


def test_validation_report_excludes_invalid_rows_with_reasons(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)

    report = validate_laps_with_report(frame)

    assert report.input_rows == 3
    assert report.retained_rows == 2
    assert report.excluded_rows == 1
    assert report.issues[-1].reasons == ("inaccurate_lap", "missing_lap_time")
    assert report.issues[-1].excluded
    assert list(validate_laps(report.cleaned_laps).columns) == list(S.LAPS_COLUMNS)
    assert report.cleaned_laps[S.IS_VALID].all()


def test_duplicate_driver_lap_identities_are_all_excluded_with_reasons(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    duplicate = frame.iloc[[0]].copy()
    frame = pd.concat([frame, duplicate], ignore_index=True)

    report = validate_laps_with_report(frame)

    duplicate_issues = [
        issue for issue in report.issues if "duplicate_identity" in issue.reasons
    ]
    assert len(duplicate_issues) == 2
    assert all(issue.excluded for issue in duplicate_issues)
    assert report.retained_rows == 1
    assert report.excluded_rows == 3
    assert dict(report.reason_counts)["duplicate_identity"] == 2


def test_pit_laps_are_reported_as_warnings_not_excluded(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)

    report = validate_laps_with_report(frame)

    pit_issues = [
        issue for issue in report.issues if "pit_out_lap" in issue.reasons
    ]
    assert len(pit_issues) == 1
    assert not pit_issues[0].excluded
    assert report.retained_rows == 2


def test_validation_report_is_reproducible(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)

    first = validate_laps_with_report(frame)
    second = validate_laps_with_report(frame)

    assert first.summary == second.summary
    assert first.reason_counts == second.reason_counts
    assert first.issues == second.issues


def test_records_preserve_session_identity_and_are_deterministic(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    ref = SessionRef(2024, "Monaco", SessionType.RACE)
    metadata = SessionMetadata(ref, "Monaco Grand Prix", "Monaco", "Monaco", 2, 3, False)
    loaded = LoadedSession(metadata, validate_laps(fastf1_laps_to_frame(raw_fastf1_laps)))

    records = lap_records_from_session(loaded)

    assert records == lap_records_from_session(loaded)
    assert records[0].session_ref == ref
    assert records[0].driver == "VER"
    assert records[0].lap_number == 1
    assert records[0].is_valid
    assert records[2].lap_time_s is None
    assert not records[2].is_valid


def test_record_conversion_rejects_inconsistent_validity(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    ref = SessionRef(2024, "Monaco", SessionType.RACE)
    metadata = SessionMetadata(ref, "Monaco Grand Prix", "Monaco", "Monaco", 2, 3, False)
    laps = validate_laps(fastf1_laps_to_frame(raw_fastf1_laps))
    laps.loc[0, S.IS_VALID] = False

    with pytest.raises(SchemaValidationError, match="IsValid"):
        lap_records_from_session(LoadedSession(metadata, laps))


def test_missing_compound_column_uses_declared_unknown_sentinel(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.drop(columns=["Compound"])
    frame = validate_laps(fastf1_laps_to_frame(raw))
    assert frame[S.COMPOUND].eq("UNKNOWN").all()


def test_missing_team_column_uses_declared_unknown_sentinel(
    raw_fastf1_laps: pd.DataFrame,
) -> None:
    raw = raw_fastf1_laps.drop(columns=["Team"])
    frame = validate_laps(fastf1_laps_to_frame(raw))
    assert frame[S.TEAM].eq("UNKNOWN").all()
