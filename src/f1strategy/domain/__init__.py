"""Domain layer — the dependency-free core.

Owns the shared vocabulary (enums, errors, data models), the boundary schema
contracts, and the Protocols used for dependency injection. Every other layer may
import from here; this layer imports nothing from them.
"""

from f1strategy.domain.enums import SessionType, TireCompound
from f1strategy.domain.errors import (
    F1StrategyError,
    InsufficientDataError,
    SchemaValidationError,
    SessionLoadError,
)
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.domain.protocols import SessionLoader
from f1strategy.domain.schemas import LAPS_COLUMNS, LAPS_SCHEMA

__all__ = [
    # enums
    "SessionType",
    "TireCompound",
    # errors
    "F1StrategyError",
    "SessionLoadError",
    "SchemaValidationError",
    "InsufficientDataError",
    # models
    "SessionRef",
    "SessionMetadata",
    "LoadedSession",
    # protocols
    "SessionLoader",
    # schemas
    "LAPS_SCHEMA",
    "LAPS_COLUMNS",
]
