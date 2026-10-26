"""Lap-frame validation and valid-lap filtering.

WHY THIS FILE EXISTS
    ``validate_laps`` enforces ``LAPS_SCHEMA`` at the telemetry layer's exit, so
    any shape drift fails here with a clear message rather than deep in analytics
    (ADR-0003). ``filter_valid_laps`` lifts the valid-lap rule out of the old
    notebook script into one reusable, tested place.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd
import pandera.errors as pa_errors

from f1strategy.domain import schemas as S
from f1strategy.domain.errors import SchemaValidationError


@dataclass(frozen=True, slots=True)
class LapValidationIssue:
    """Row-level warning or exclusion reason in source row order."""

    row_position: int
    driver: str
    lap_number: int
    reasons: tuple[str, ...]
    excluded: bool


@dataclass(frozen=True, slots=True)
class LapValidationReport:
    """Deterministic summary, explainable row issues, and analysis-ready laps.

    Reason counts are non-exclusive: one excluded row can have multiple reasons,
    while pit-in/out markers are warnings and do not exclude a valid lap.
    """

    input_rows: int
    retained_rows: int
    excluded_rows: int
    reason_counts: tuple[tuple[str, int], ...]
    issues: tuple[LapValidationIssue, ...]
    cleaned_laps: pd.DataFrame

    @property
    def summary(self) -> str:
        """Return a stable text summary suitable for logs or command output."""
        reasons = ", ".join(f"{name}={count}" for name, count in self.reason_counts)
        return (
            f"{self.input_rows} rows: {self.retained_rows} retained, "
            f"{self.excluded_rows} excluded; reasons: {reasons or 'none'}"
        )


def validate_laps(df: pd.DataFrame) -> pd.DataFrame:
    """Validate (and dtype-coerce) a laps frame against ``LAPS_SCHEMA``.

    Returns the coerced frame on success. Besides column-level schema checks, it
    enforces the canonical IsValid formula; either failure raises
    ``SchemaValidationError``.
    """
    try:
        validated = S.LAPS_SCHEMA.validate(df, lazy=True)
    except pa_errors.SchemaErrors as exc:
        raise SchemaValidationError(f"Laps frame failed LAPS_SCHEMA:\n{exc}") from exc

    expected_valid = (
        validated[S.IS_ACCURATE]
        & ~validated[S.DELETED]
        & validated[S.LAP_TIME_S].notna()
    )
    inconsistent = expected_valid.ne(validated[S.IS_VALID])
    if inconsistent.any():
        positions = inconsistent.to_numpy().nonzero()[0].tolist()
        raise SchemaValidationError(
            "IsValid must equal IsAccurate and not Deleted and LapTime_s present; "
            f"inconsistent row positions: {positions}"
        )
    return validated


def validate_laps_with_report(df: pd.DataFrame) -> LapValidationReport:
    """Classify invalid and duplicate rows without silently losing their reasons.

    Schema violations reject the input through ``validate_laps``. Canonically
    invalid laps and every row in a duplicate (Driver, LapNumber) identity group
    are excluded from ``cleaned_laps``. Pit-in/out markers remain eligible laps
    but are reported as warnings until a consumer defines a different policy.
    """
    laps = validate_laps(df)
    duplicate_identity = laps.duplicated([S.DRIVER, S.LAP_NUMBER], keep=False)
    issues: list[LapValidationIssue] = []
    reason_counts: Counter[str] = Counter()
    excluded_mask: list[bool] = []

    for position, (_, row) in enumerate(laps.iterrows()):
        reasons: list[str] = []
        if not bool(row[S.IS_ACCURATE]):
            reasons.append("inaccurate_lap")
        if bool(row[S.DELETED]):
            reasons.append("deleted_lap")
        if pd.isna(row[S.LAP_TIME_S]):
            reasons.append("missing_lap_time")
        if bool(duplicate_identity.iloc[position]):
            reasons.append("duplicate_identity")
        if pd.notna(row[S.IS_PIT_IN_LAP]) and bool(row[S.IS_PIT_IN_LAP]):
            reasons.append("pit_in_lap")
        if pd.notna(row[S.IS_PIT_OUT_LAP]) and bool(row[S.IS_PIT_OUT_LAP]):
            reasons.append("pit_out_lap")
        track_status = row[S.TRACK_STATUS]
        if pd.notna(track_status) and str(track_status) != "1":
            reasons.append("non_clear_track_status")

        excluded = not bool(row[S.IS_VALID]) or bool(duplicate_identity.iloc[position])
        excluded_mask.append(excluded)
        if reasons:
            reason_counts.update(reasons)
            issues.append(
                LapValidationIssue(
                    row_position=position,
                    driver=str(row[S.DRIVER]),
                    lap_number=int(row[S.LAP_NUMBER]),
                    reasons=tuple(reasons),
                    excluded=excluded,
                )
            )

    excluded_series = pd.Series(excluded_mask, index=laps.index, dtype=bool)
    cleaned = laps.loc[~excluded_series].reset_index(drop=True)
    excluded_rows = int(excluded_series.sum())
    return LapValidationReport(
        input_rows=len(laps),
        retained_rows=len(cleaned),
        excluded_rows=excluded_rows,
        reason_counts=tuple(sorted(reason_counts.items())),
        issues=tuple(issues),
        cleaned_laps=cleaned,
    )


def filter_valid_laps(df: pd.DataFrame) -> pd.DataFrame:
    """Return analysis-ready laps after validity and duplicate-identity checks.

    Excluded-row details are available from ``validate_laps_with_report``.
    """
    return validate_laps_with_report(df).cleaned_laps
