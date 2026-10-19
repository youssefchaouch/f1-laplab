"""Lap-frame validation and valid-lap filtering.

WHY THIS FILE EXISTS
    ``validate_laps`` enforces ``LAPS_SCHEMA`` at the telemetry layer's exit, so
    any shape drift fails here with a clear message rather than deep in analytics
    (ADR-0003). ``filter_valid_laps`` lifts the valid-lap rule out of the old
    notebook script into one reusable, tested place.
"""

from __future__ import annotations

import pandas as pd
import pandera.errors as pa_errors

from f1strategy.domain import schemas as S
from f1strategy.domain.errors import SchemaValidationError


def validate_laps(df: pd.DataFrame) -> pd.DataFrame:
    """Validate (and dtype-coerce) a laps frame against ``LAPS_SCHEMA``.

    Returns the coerced frame on success; raises ``SchemaValidationError`` with
    the underlying pandera report on failure.
    """
    try:
        return S.LAPS_SCHEMA.validate(df, lazy=True)
    except pa_errors.SchemaErrors as exc:
        raise SchemaValidationError(f"Laps frame failed LAPS_SCHEMA:\n{exc}") from exc


def filter_valid_laps(df: pd.DataFrame) -> pd.DataFrame:
    """Return only laps flagged ``IsValid`` (accurate, not deleted, timed).

    Replaces the script's inline ``(IsAccurate == True) & (Deleted == False) &
    LapTime.notna()`` filter with a single named operation.
    """
    return df[df[S.IS_VALID]].reset_index(drop=True)
