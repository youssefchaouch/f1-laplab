"""Boundary DataFrame schemas (pandera).

WHY THIS FILE EXISTS
    A bare DataFrame is an untyped bag of columns. ``LAPS_SCHEMA`` is the
    executable contract for the laps frame that the telemetry layer produces and
    every downstream layer consumes. Validation runs at the producer's exit, so a
    shape problem fails *there*, with a clear message, instead of surfacing as a
    cryptic KeyError three layers later. See ADR-0003.

DESIGN
    Column-name constants are exported so producers/consumers reference one
    spelling (no stringly-typed ``df["LapTime_s"]`` scattered around). The schema
    is ``strict`` and ``coerce``: the telemetry converter emits exactly these
    columns, coerced to these dtypes, and any extra/missing column is a contract
    breach we want to hear about.

NOTE ON DEPENDENCIES
    This is the one place the domain layer imports pandera. Pandera is a data-
    contract library, not a business dependency, so the domain stays conceptually
    pure (it owns the contract; it does not do business logic).
"""

from __future__ import annotations

import pandera.pandas as pa

from f1strategy.domain.enums import TireCompound

# --- Canonical column names (single source of truth) ---------------------
DRIVER = "Driver"
TEAM = "Team"
LAP_NUMBER = "LapNumber"
STINT = "Stint"
COMPOUND = "Compound"
TYRE_LIFE = "TyreLife"
LAP_TIME_S = "LapTime_s"
IS_ACCURATE = "IsAccurate"
DELETED = "Deleted"
IS_VALID = "IsValid"
IS_PIT_IN_LAP = "IsPitInLap"
IS_PIT_OUT_LAP = "IsPitOutLap"
TRACK_STATUS = "TrackStatus"

LAPS_COLUMNS: tuple[str, ...] = (
    DRIVER,
    TEAM,
    LAP_NUMBER,
    STINT,
    COMPOUND,
    TYRE_LIFE,
    LAP_TIME_S,
    IS_ACCURATE,
    DELETED,
    IS_VALID,
    IS_PIT_IN_LAP,
    IS_PIT_OUT_LAP,
    TRACK_STATUS,
)

_COMPOUND_VALUES = [c.value for c in TireCompound]

# The contract for a validated laps frame. FastF1's LapTime timedelta has already
# been converted to LAP_TIME_S float seconds at the boundary — no timedeltas here.
LAPS_SCHEMA = pa.DataFrameSchema(
    {
        DRIVER: pa.Column(str, nullable=False),
        TEAM: pa.Column(str, nullable=False),
        LAP_NUMBER: pa.Column(int, pa.Check.ge(1), nullable=False),
        # FastF1 may omit these values; preserve missingness instead of using 0.
        STINT: pa.Column("Int64", pa.Check.ge(0), nullable=True),
        COMPOUND: pa.Column(str, pa.Check.isin(_COMPOUND_VALUES), nullable=False),
        TYRE_LIFE: pa.Column("Int64", pa.Check.ge(0), nullable=True),
        # Null LapTime is legitimate (no time set on the lap), so nullable.
        LAP_TIME_S: pa.Column(float, pa.Check.gt(0), nullable=True),
        IS_ACCURATE: pa.Column(bool, nullable=False),
        DELETED: pa.Column(bool, nullable=False),
        IS_VALID: pa.Column(bool, nullable=False),
        # FastF1 exposes pit markers as nullable times; None means unavailable.
        IS_PIT_IN_LAP: pa.Column("boolean", nullable=True),
        IS_PIT_OUT_LAP: pa.Column("boolean", nullable=True),
        # Preserve FastF1's per-lap track-status code without interpreting it.
        TRACK_STATUS: pa.Column("string", nullable=True),
    },
    strict=True,
    coerce=True,
    name="LAPS_SCHEMA",
)
