"""Leakage-safe, prior-only features for upcoming-lap-time datasets."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum

import pandas as pd

from f1strategy.domain import schemas as S
from f1strategy.domain.errors import InsufficientDataError, SchemaValidationError
from f1strategy.domain.models import LoadedSession, SessionMetadata
from f1strategy.telemetry.validation import validate_laps

IDENTIFIER_COLUMNS = (
    "session_year",
    "grand_prix",
    "session",
    "driver",
    "lap_number",
)
FEATURE_COLUMNS = (
    "previous_lap_time_s",
    "prior_3lap_mean_time_s",
    "prior_3lap_valid_count",
)
TARGET_COLUMN = "target_lap_time_s"


@dataclass(frozen=True, slots=True)
class LapFeatureMetadata:
    """Source metadata and prediction/target contract for one session dataset."""

    source: SessionMetadata
    prediction_cutoff: str = "immediately_before_target_lap_begins"
    target_name: str = TARGET_COLUMN
    target_unit: str = "seconds"
    history_window_lap_offsets: tuple[int, int] = (-3, -1)


@dataclass(frozen=True, slots=True)
class ExcludedLap:
    """A source lap excluded from labels under the canonical validity rule."""

    driver: str
    lap_number: int
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LapFeatureDataset:
    """Aligned trace keys, model features, labels, and source exclusion trace.

    ``identifiers``, ``features``, and ``labels`` use the same deterministic
    RangeIndex and row order. The identifier columns form the unique row key.
    Identifiers and labels are deliberately separate from the model matrix.
    """

    metadata: LapFeatureMetadata
    identifiers: pd.DataFrame
    features: pd.DataFrame
    labels: pd.Series
    excluded_laps: tuple[ExcludedLap, ...]


def build_lap_features(session: LoadedSession) -> LapFeatureDataset:
    """Build one deterministic dataset of valid timed target laps.

    Features for target lap ``n`` use only eligible observations in lap-number
    slots ``n-3`` through ``n-1`` for the same driver and session. Missing or
    invalid slots remain missing; no nearest-valid-lap substitution or imputation
    is performed. Eligible duplicate target identities are rejected.

    Empty input and input with no eligible target laps raise
    ``InsufficientDataError``. Schema and validity-contract violations raise
    ``SchemaValidationError``.
    """
    laps = validate_laps(session.laps)
    if laps.empty:
        raise InsufficientDataError("Cannot build lap features from an empty session")

    eligible = laps[S.IS_VALID]
    target_rows = laps.loc[eligible]
    if target_rows.empty:
        raise InsufficientDataError(
            "Cannot build lap features: session contains no canonically valid timed target laps"
        )

    duplicate_targets = target_rows.duplicated(
        [S.DRIVER, S.LAP_NUMBER],
        keep=False,
    )
    if duplicate_targets.any():
        duplicate_keys = sorted(
            {
                (str(row[S.DRIVER]), int(row[S.LAP_NUMBER]))
                for _, row in target_rows.loc[duplicate_targets].iterrows()
            }
        )
        raise SchemaValidationError(
            "Duplicate eligible target identities (session, driver, lap_number): "
            f"{duplicate_keys}"
        )

    eligible_times = {
        (str(row[S.DRIVER]), int(row[S.LAP_NUMBER])): float(row[S.LAP_TIME_S])
        for _, row in target_rows.iterrows()
    }

    ordered_targets = target_rows.sort_values(
        [S.DRIVER, S.LAP_NUMBER],
        kind="mergesort",
    ).reset_index(drop=True)
    identifiers = pd.DataFrame(
        {
            "session_year": pd.Series(
                [session.metadata.ref.year] * len(ordered_targets),
                dtype="int64",
            ),
            "grand_prix": pd.Series(
                [session.metadata.ref.grand_prix] * len(ordered_targets),
                dtype="string",
            ),
            "session": pd.Series(
                [session.metadata.ref.session.value] * len(ordered_targets),
                dtype="string",
            ),
            "driver": ordered_targets[S.DRIVER].astype("string").reset_index(drop=True),
            "lap_number": ordered_targets[S.LAP_NUMBER].astype("int64").reset_index(drop=True),
        }
    )[list(IDENTIFIER_COLUMNS)]

    previous_times: list[float | None] = []
    prior_means: list[float | None] = []
    prior_counts: list[int] = []
    for _, row in ordered_targets.iterrows():
        driver = str(row[S.DRIVER])
        lap_number = int(row[S.LAP_NUMBER])
        previous = eligible_times.get((driver, lap_number - 1))
        history = [
            eligible_times[(driver, prior_lap)]
            for prior_lap in range(lap_number - 3, lap_number)
            if (driver, prior_lap) in eligible_times
        ]
        previous_times.append(previous)
        prior_means.append(None if not history else fsum(history) / len(history))
        prior_counts.append(len(history))

    features = pd.DataFrame(
        {
            "previous_lap_time_s": pd.array(previous_times, dtype="Float64"),
            "prior_3lap_mean_time_s": pd.array(prior_means, dtype="Float64"),
            "prior_3lap_valid_count": pd.Series(prior_counts, dtype="int64"),
        }
    )[list(FEATURE_COLUMNS)]
    labels = ordered_targets[S.LAP_TIME_S].astype("float64").reset_index(drop=True)
    labels.name = TARGET_COLUMN

    excluded_laps = tuple(
        sorted(
            (
                ExcludedLap(
                    driver=str(row[S.DRIVER]),
                    lap_number=int(row[S.LAP_NUMBER]),
                    reasons=_invalid_lap_reasons(row),
                )
                for _, row in laps.loc[~eligible].iterrows()
            ),
            key=lambda issue: (issue.driver, issue.lap_number, issue.reasons),
        )
    )

    return LapFeatureDataset(
        metadata=LapFeatureMetadata(source=session.metadata),
        identifiers=identifiers,
        features=features,
        labels=labels,
        excluded_laps=excluded_laps,
    )


def _invalid_lap_reasons(row: pd.Series) -> tuple[str, ...]:
    reasons: list[str] = []
    if not bool(row[S.IS_ACCURATE]):
        reasons.append("inaccurate_lap")
    if bool(row[S.DELETED]):
        reasons.append("deleted_lap")
    if pd.isna(row[S.LAP_TIME_S]):
        reasons.append("missing_lap_time")
    return tuple(reasons)
