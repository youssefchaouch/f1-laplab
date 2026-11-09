"""Core domain data structures.

WHY THIS FILE EXISTS
    These are the owned types that cross layer boundaries. ``LoadedSession`` in
    particular is the *only* thing the telemetry layer hands downstream: a
    validated laps frame plus metadata. Nothing outside telemetry ever touches a
    raw ``fastf1.Session`` object, which is what keeps FastF1 coupling contained
    (ADR-0002).

DESIGN
    Frozen, slotted dataclasses: immutable (an analysis can't accidentally mutate
    the session it was handed) and hashable where useful. ``SessionRef`` is
    frozen specifically so it can serve as a cache key.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from f1strategy.domain.enums import SessionType, TireCompound


def lap_is_valid(is_accurate: bool, deleted: bool, lap_time_s: float | None) -> bool:
    """Apply the project's canonical valid-lap rule."""
    return is_accurate and not deleted and lap_time_s is not None


@dataclass(frozen=True, slots=True)
class SessionRef:
    """Immutable identity of a session — hashable, usable as a cache key."""

    year: int
    grand_prix: str
    session: SessionType

    def __str__(self) -> str:
        return f"{self.year} {self.grand_prix} {self.session.value}"


@dataclass(frozen=True, slots=True)
class SessionMetadata:
    """Descriptive facts about a loaded session (no timing data)."""

    ref: SessionRef
    event_name: str
    circuit: str
    country: str
    n_drivers: int
    n_laps: int
    loaded_with_telemetry: bool


@dataclass(frozen=True, slots=True)
class LoadedSession:
    """The telemetry layer's single output contract.

    ``laps`` conforms to ``LAPS_SCHEMA``. Downstream layers consume the frame +
    metadata and never reach back into FastF1.
    """

    metadata: SessionMetadata
    laps: pd.DataFrame


@dataclass(frozen=True, slots=True)
class LapRecord:
    """Immutable, typed representation of one validated session lap."""

    session_ref: SessionRef
    driver: str
    team: str
    lap_number: int
    stint: int | None
    compound: TireCompound
    tyre_life: int | None
    lap_time_s: float | None
    is_accurate: bool
    deleted: bool
    is_pit_in_lap: bool | None = None
    is_pit_out_lap: bool | None = None
    track_status: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.session_ref, SessionRef):
            raise ValueError("session_ref must be a SessionRef")
        if not isinstance(self.driver, str) or not self.driver.strip():
            raise ValueError("driver must be a non-empty driver code")
        if not isinstance(self.team, str) or not self.team.strip():
            raise ValueError("team must be non-empty; use 'UNKNOWN' when unavailable")
        if not isinstance(self.lap_number, int) or isinstance(self.lap_number, bool):
            raise ValueError("lap_number must be an integer greater than or equal to 1")
        if self.lap_number < 1:
            raise ValueError("lap_number must be an integer greater than or equal to 1")
        if self.stint is not None and (
            not isinstance(self.stint, int)
            or isinstance(self.stint, bool)
            or self.stint < 0
        ):
            raise ValueError("stint must be a non-negative integer or None")
        if self.tyre_life is not None and (
            not isinstance(self.tyre_life, int)
            or isinstance(self.tyre_life, bool)
            or self.tyre_life < 0
        ):
            raise ValueError("tyre_life must be a non-negative integer or None")
        if not isinstance(self.compound, TireCompound):
            raise ValueError("compound must be a TireCompound")
        if self.lap_time_s is not None:
            if (
                not isinstance(self.lap_time_s, (int, float))
                or isinstance(self.lap_time_s, bool)
                or pd.isna(self.lap_time_s)
                or self.lap_time_s <= 0
            ):
                raise ValueError("lap_time_s must be positive or None")
        if not isinstance(self.is_accurate, bool) or not isinstance(self.deleted, bool):
            raise ValueError("is_accurate and deleted must be bool values")
        for name, value in (
            ("is_pit_in_lap", self.is_pit_in_lap),
            ("is_pit_out_lap", self.is_pit_out_lap),
        ):
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{name} must be bool or None")
        if self.track_status is not None and (
            not isinstance(self.track_status, str) or not self.track_status
        ):
            raise ValueError("track_status must be a non-empty string or None")

    @property
    def is_valid(self) -> bool:
        """Whether this lap is accurate, not deleted, and has a lap time."""
        return lap_is_valid(self.is_accurate, self.deleted, self.lap_time_s)
