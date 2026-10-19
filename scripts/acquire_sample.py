"""Acquire the documented Monaco 2024 race sample using FastF1."""

from __future__ import annotations

import sys

from f1strategy.config.settings import Settings
from f1strategy.domain.enums import SessionType
from f1strategy.domain.errors import F1StrategyError
from f1strategy.domain.models import SessionRef
from f1strategy.domain.protocols import SessionLoader
from f1strategy.telemetry.loader import FastF1SessionLoader


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

    n_valid_laps = int(loaded.laps["IsValid"].sum())
    print(
        f"FastF1: {ref} — {loaded.metadata.n_laps} laps, "
        f"{n_valid_laps} valid laps, {loaded.metadata.n_drivers} drivers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
