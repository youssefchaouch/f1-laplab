"""Tests for the immutable canonical lap value."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from f1strategy.domain.enums import SessionType, TireCompound
from f1strategy.domain.models import LapRecord, SessionRef


def make_record(
    *,
    lap_number: int = 1,
    stint: int | None = 1,
    compound: TireCompound = TireCompound.SOFT,
    tyre_life: int | None = 1,
    lap_time_s: float | None = 74.5,
    is_accurate: bool = True,
    deleted: bool = False,
) -> LapRecord:
    return LapRecord(
        session_ref=SessionRef(2024, "Monaco", SessionType.RACE),
        driver="VER",
        team="Red Bull Racing",
        lap_number=lap_number,
        stint=stint,
        compound=compound,
        tyre_life=tyre_life,
        lap_time_s=lap_time_s,
        is_accurate=is_accurate,
        deleted=deleted,
    )


def test_lap_record_is_immutable_and_exposes_canonical_validity() -> None:
    record = make_record()

    assert record.is_valid
    with pytest.raises(FrozenInstanceError):
        record.__setattr__("lap_number", 2)


def test_missing_optional_values_are_preserved_and_make_lap_invalid() -> None:
    record = make_record(stint=None, tyre_life=None, lap_time_s=None)

    assert record.stint is None
    assert record.tyre_life is None
    assert record.lap_time_s is None
    assert not record.is_valid


@pytest.mark.parametrize("lap_number", [0, -1])
def test_lap_number_must_be_one_based(lap_number: int) -> None:
    with pytest.raises(ValueError, match="lap_number"):
        make_record(lap_number=lap_number)


@pytest.mark.parametrize("field", ["stint", "tyre_life"])
def test_optional_integer_fields_cannot_be_negative(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        if field == "stint":
            make_record(stint=-1)
        else:
            make_record(tyre_life=-1)


def test_lap_time_must_be_positive_when_present() -> None:
    with pytest.raises(ValueError, match="lap_time_s"):
        make_record(lap_time_s=0.0)


@pytest.mark.parametrize(
    ("is_accurate", "deleted", "lap_time_s", "expected"),
    [
        (True, False, 74.5, True),
        (False, False, 74.5, False),
        (True, True, 74.5, False),
        (True, False, None, False),
    ],
)
def test_validity_matches_the_project_rule(
    is_accurate: bool,
    deleted: bool,
    lap_time_s: float | None,
    expected: bool,
) -> None:
    record = make_record(
        is_accurate=is_accurate,
        deleted=deleted,
        lap_time_s=lap_time_s,
    )
    assert record.is_valid is expected
