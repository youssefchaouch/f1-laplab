"""Acquire the documented Monaco 2024 race sample using FastF1."""

from __future__ import annotations

import sys

from f1strategy.config.settings import Settings
from f1strategy.domain.enums import SessionType
from f1strategy.domain.errors import F1StrategyError
from f1strategy.domain.models import SessionRef
from f1strategy.domain.protocols import SessionLoader
from f1strategy.telemetry.loader import FastF1SessionLoader
from f1strategy.telemetry.validation import validate_laps_with_report


class AcquisitionSetupError(Exception):
    """Raised when local project or cache setup prevents acquisition."""


def _build_loader() -> SessionLoader:
    """Load settings and initialize the configured FastF1 cache."""
    try:
        settings = Settings.load()
    except (OSError, ValueError) as exc:
        raise AcquisitionSetupError(f"Unable to load project settings: {exc}") from exc

    try:
        return FastF1SessionLoader(settings)
    except (OSError, ValueError) as exc:
        raise AcquisitionSetupError(
            f"Unable to initialize the configured cache at {settings.paths.cache}: {exc}"
        ) from exc


def main() -> int:
    """Load the fixed historical sample and print a concise summary."""
    ref = SessionRef(2024, "Monaco", SessionType.RACE)
    try:
        loader = _build_loader()
        loaded = loader.load(ref)
    except (AcquisitionSetupError, F1StrategyError) as exc:
        print(f"Failed to acquire {ref} from FastF1: {exc}", file=sys.stderr)
        return 1

    report = validate_laps_with_report(loaded.laps)
    print(
        f"FastF1: {ref} | {loaded.metadata.n_drivers} drivers; "
        f"{report.summary}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
