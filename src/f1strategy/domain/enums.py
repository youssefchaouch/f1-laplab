"""Domain enumerations.

WHY THIS FILE EXISTS
    FastF1 represents session types and tyre compounds as bare strings. Strings
    are easy to typo and carry no guarantees. These enums are the canonical
    vocabulary every layer shares, so a compound is always one of a known set and
    the telemetry boundary normalizes FastF1's strings into them exactly once.

DESIGN
    ``str`` mixins so the members compare/serialize as their string value
    (``TireCompound.SOFT == "SOFT"``), which keeps them friendly to pandas
    categoricals and JSON without losing enum safety.
"""

from __future__ import annotations

from enum import StrEnum


class SessionType(StrEnum):
    """FastF1 session identifier."""

    PRACTICE_1 = "FP1"
    PRACTICE_2 = "FP2"
    PRACTICE_3 = "FP3"
    QUALIFYING = "Q"
    SPRINT = "S"
    SPRINT_QUALIFYING = "SQ"
    RACE = "R"


class TireCompound(StrEnum):
    """Normalized tyre compound. ``UNKNOWN`` absorbs nulls/unmapped values so
    downstream code never has to handle a missing compound."""

    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_raw(cls, value: object) -> TireCompound:
        """Map a raw FastF1 compound string (or null) to a known member."""
        if value is None:
            return cls.UNKNOWN
        try:
            return cls(str(value).strip().upper())
        except ValueError:
            return cls.UNKNOWN
