"""FastF1 -> domain conversion.

WHY THIS FILE EXISTS
    This is the heart of the anti-corruption boundary (ADR-0002). FastF1 hands us
    a laps DataFrame with its own column names and dtypes (notably ``LapTime`` as
    a ``timedelta``). Here we translate that, exactly once, into a frame matching
    ``LAPS_SCHEMA`` — owned column names, plain float seconds, a normalized
    compound enum, and a derived ``IsValid`` flag. Downstream layers never see a
    FastF1 dtype again.

DESIGN
    Pure function, no FastF1 import needed — it operates on the raw DataFrame the
    loader extracts. That keeps it unit-testable with a hand-built fixture frame
    and no network. The loader owns the ``import fastf1``.
"""

from __future__ import annotations

from numbers import Integral

import pandas as pd

from f1strategy.domain import schemas as S
from f1strategy.domain.enums import TireCompound
from f1strategy.domain.errors import SchemaValidationError
from f1strategy.domain.models import LapRecord, LoadedSession, lap_is_valid
from f1strategy.telemetry.validation import validate_laps


def fastf1_laps_to_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert a raw FastF1 laps frame into a ``LAPS_SCHEMA``-shaped frame.

    Produces exactly ``LAPS_COLUMNS`` — no more, no less — so the schema's
    ``strict`` check passes and no FastF1-specific columns leak downstream.
    """
    lap_time_s = _timedelta_to_seconds(raw.get("LapTime"), index=raw.index)
    is_accurate = _to_bool(raw.get(S.IS_ACCURATE), field_name=S.IS_ACCURATE)
    deleted = _to_bool(raw.get(S.DELETED), field_name=S.DELETED)

    frame = pd.DataFrame(
        {
            S.DRIVER: _driver_codes(raw.get(S.DRIVER)),
            S.TEAM: _team_names(raw.get(S.TEAM), index=raw.index),
            S.LAP_NUMBER: _to_int(
                raw.get(S.LAP_NUMBER),
                index=raw.index,
                field_name=S.LAP_NUMBER,
                nullable=False,
            ),
            S.STINT: _to_int(
                raw.get(S.STINT),
                index=raw.index,
                field_name=S.STINT,
                nullable=True,
            ),
            S.COMPOUND: _to_compound(raw.get(S.COMPOUND), index=raw.index),
            S.TYRE_LIFE: _to_int(
                raw.get(S.TYRE_LIFE),
                index=raw.index,
                field_name=S.TYRE_LIFE,
                nullable=True,
            ),
            S.LAP_TIME_S: lap_time_s,
            S.IS_ACCURATE: is_accurate,
            S.DELETED: deleted,
        }
    )
    frame[S.IS_VALID] = pd.Series(
        [
            lap_is_valid(
                accurate,
                was_deleted,
                None if pd.isna(lap_time) else float(lap_time),
            )
            for accurate, was_deleted, lap_time in zip(
                is_accurate, deleted, lap_time_s, strict=True
            )
        ],
        index=raw.index,
        dtype="bool",
    )
    return frame[list(S.LAPS_COLUMNS)]


def lap_records_from_session(session: LoadedSession) -> tuple[LapRecord, ...]:
    """Convert validated session laps into immutable, traceable lap records."""
    laps = validate_laps(session.laps)
    records: list[LapRecord] = []
    for _, row in laps.iterrows():
        lap_time = row[S.LAP_TIME_S]
        record = LapRecord(
            session_ref=session.metadata.ref,
            driver=str(row[S.DRIVER]),
            team=str(row[S.TEAM]),
            lap_number=int(row[S.LAP_NUMBER]),
            stint=_optional_int(row[S.STINT]),
            compound=TireCompound(str(row[S.COMPOUND])),
            tyre_life=_optional_int(row[S.TYRE_LIFE]),
            lap_time_s=None if pd.isna(lap_time) else float(lap_time),
            is_accurate=bool(row[S.IS_ACCURATE]),
            deleted=bool(row[S.DELETED]),
        )
        if bool(row[S.IS_VALID]) != record.is_valid:
            raise SchemaValidationError("IsValid does not match the canonical lap-validity rule")
        records.append(record)
    return tuple(records)


def _timedelta_to_seconds(series: pd.Series | None, *, index: pd.Index) -> pd.Series:
    if series is None:
        return pd.Series(float("nan"), index=index, dtype="float64")
    return pd.to_timedelta(series).dt.total_seconds().astype("float64")


def _to_int(
    series: pd.Series | None,
    *,
    index: pd.Index,
    field_name: str,
    nullable: bool,
) -> pd.Series:
    if series is None:
        if nullable:
            return pd.Series(pd.NA, index=index, dtype="Int64")
        raise SchemaValidationError(f"Required telemetry column {field_name!r} is missing")

    try:
        numeric = pd.to_numeric(series, errors="raise")
        fractional = numeric.notna() & numeric.mod(1).ne(0)
        if fractional.any():
            raise ValueError(f"{field_name} values must be integers")
        if not nullable and numeric.isna().any():
            raise ValueError(f"{field_name} values cannot be missing")
        return numeric.astype("Int64" if nullable else "int64")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SchemaValidationError(f"Invalid telemetry values for {field_name!r}: {exc}") from exc


def _to_bool(series: pd.Series | None, *, field_name: str) -> pd.Series:
    if series is None:
        raise SchemaValidationError(f"Required telemetry column {field_name!r} is missing")
    if not pd.api.types.is_bool_dtype(series.dtype) or series.isna().any():
        raise SchemaValidationError(f"{field_name!r} must contain non-missing boolean values")
    return series.astype(bool)


def _driver_codes(series: pd.Series | None) -> pd.Series:
    if series is None or series.isna().any():
        raise SchemaValidationError("Driver must contain a non-missing driver code")
    codes = series.astype("string")
    if codes.str.strip().eq("").any():
        raise SchemaValidationError("Driver must contain a non-empty driver code")
    return codes.astype(str)


def _team_names(series: pd.Series | None, *, index: pd.Index) -> pd.Series:
    if series is None:
        return pd.Series("UNKNOWN", index=index, dtype="string").astype(str)
    return series.astype("string").fillna("UNKNOWN").astype(str)


def _to_compound(series: pd.Series | None, *, index: pd.Index) -> pd.Series:
    """Convert a compound column to normalized tire compound enum values.

    The UNKNOWN enum is the declared sentinel for absent or unrecognized compounds.
    """
    if series is None:
        return pd.Series(TireCompound.UNKNOWN.value, index=index, dtype="string")
    return series.map(TireCompound.from_raw).map(lambda c: c.value)


def _optional_int(value: object) -> int | None:
    if value is pd.NA or value is None:
        return None
    if isinstance(value, Integral):
        return int(value)
    raise SchemaValidationError(f"Expected an integer or missing value, got {value!r}")
