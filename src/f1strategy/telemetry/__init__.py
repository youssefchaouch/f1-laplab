"""Telemetry layer — FastF1 ingestion and the anti-corruption boundary.

This is the ONLY package permitted to ``import fastf1`` (enforced by
tests/architecture/test_import_boundaries.py). It converts FastF1 objects into
validated domain types and hands a ``LoadedSession`` downstream.
"""

from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.loader import FastF1SessionLoader
from f1strategy.telemetry.validation import (
    LapValidationIssue,
    LapValidationReport,
    filter_valid_laps,
    validate_laps,
    validate_laps_with_report,
)

__all__ = [
    "FastF1SessionLoader",
    "fastf1_laps_to_frame",
    "validate_laps",
    "filter_valid_laps",
    "LapValidationIssue",
    "LapValidationReport",
    "validate_laps_with_report",
]
