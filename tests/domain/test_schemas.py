"""Tests for the LAPS_SCHEMA boundary contract."""

from __future__ import annotations

import pandas as pd
import pytest

from f1strategy.domain import schemas as S
from f1strategy.domain.errors import SchemaValidationError
from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.validation import validate_laps


def test_valid_frame_passes(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    out = validate_laps(frame)
    assert list(out.columns) == list(S.LAPS_COLUMNS)


def test_missing_column_raises(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps).drop(columns=[S.COMPOUND])
    with pytest.raises(SchemaValidationError):
        validate_laps(frame)


def test_bad_compound_value_raises(raw_fastf1_laps: pd.DataFrame) -> None:
    frame = fastf1_laps_to_frame(raw_fastf1_laps)
    frame.loc[0, S.COMPOUND] = "ROCKET_FUEL"  # not a TireCompound
    with pytest.raises(SchemaValidationError):
        validate_laps(frame)
