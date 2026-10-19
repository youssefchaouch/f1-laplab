"""Domain exception hierarchy.

WHY THIS FILE EXISTS
    The original loader let raw FastF1 exceptions escape, so a caller could not
    tell "the network failed" from "the data shape is wrong" from "there aren't
    enough laps to analyse". A small, owned hierarchy lets every layer raise
    something meaningful and lets callers (and the UI) react differently per case.

    All errors derive from ``F1StrategyError`` so a caller can catch the whole
    family with one ``except`` while still being able to narrow when it matters.
"""

from __future__ import annotations


class F1StrategyError(Exception):
    """Base class for every error raised by this platform."""


class SessionLoadError(F1StrategyError):
    """Raised when a session cannot be loaded (network/FastF1 failure, bad ref)."""


class SchemaValidationError(F1StrategyError):
    """Raised when a DataFrame violates its declared boundary schema."""


class InsufficientDataError(F1StrategyError):
    """Raised when there is not enough valid data to perform an analysis."""
