"""FastF1 session loader — the only module that imports ``fastf1``.

WHY THIS FILE EXISTS
    Replaces the original ``load_session()``, fixing its three problems:
      1. It returned a raw ``fastf1.Session`` (leaky abstraction) — now it returns
         a validated ``LoadedSession`` (ADR-0002).
      2. It enabled the cache at *import time* with a relative path — now the
         cache is enabled in ``__init__`` from injected ``Settings`` with an
         absolute path (ADR-0004).
      3. It let raw FastF1 errors escape — now failures are wrapped in
         ``SessionLoadError`` carrying the ``SessionRef``.

DESIGN
    ``FastF1SessionLoader`` implements the ``SessionLoader`` Protocol, so every
    downstream consumer depends on the interface and tests can inject a fake. The
    constructor takes ``Settings`` (dependency injection); nothing global is read.
"""

from __future__ import annotations

import logging

import fastf1
import pandas as pd
from fastf1.exceptions import DataNotLoadedError

from f1strategy.config.settings import Settings
from f1strategy.domain.errors import InsufficientDataError, SessionLoadError
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.validation import validate_laps

logger = logging.getLogger(__name__)


class FastF1SessionLoader:
    """Loads F1 sessions via FastF1 and returns validated domain objects."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Enable the cache here (not at import time) with an absolute path.
        settings.paths.ensure()
        fastf1.Cache.enable_cache(str(settings.paths.cache))
        logger.debug("FastF1 cache enabled at %s", settings.paths.cache)

    def load(self, ref: SessionRef, *, with_telemetry: bool = False) -> LoadedSession:
        """Load a session and return a validated ``LoadedSession``.

        Raises:
            SessionLoadError: if FastF1 cannot fetch/parse the session.
            SchemaValidationError: if the laps frame violates ``LAPS_SCHEMA``.
            InsufficientDataError: if the session has no laps or no valid laps.
        """
        logger.info("Loading session %s (telemetry=%s)", ref, with_telemetry)
        try:
            session = fastf1.get_session(ref.year, ref.grand_prix, ref.session.value)
            session.load(telemetry=with_telemetry, weather=False, messages=True)
        except Exception as exc:  # FastF1 raises a variety of error types
            raise SessionLoadError(f"Failed to load {ref}: {exc}") from exc

        try:
            raw_laps = session.laps
        except DataNotLoadedError as exc:
            raise SessionLoadError(f"FastF1 did not load lap data for {ref}: {exc}") from exc

        laps = validate_laps(fastf1_laps_to_frame(raw_laps))
        if laps.empty:
            raise InsufficientDataError(f"Session {ref} contains no laps")
        if not laps["IsValid"].any():
            raise InsufficientDataError(f"Session {ref} contains no valid laps")

        metadata = self._build_metadata(ref, session, laps, with_telemetry)
        logger.info("Loaded %s: %d laps, %d drivers", ref, metadata.n_laps, metadata.n_drivers)
        return LoadedSession(metadata=metadata, laps=laps)

    @staticmethod
    def _build_metadata(
        ref: SessionRef,
        session: fastf1.core.Session,
        laps: pd.DataFrame,
        with_telemetry: bool,
    ) -> SessionMetadata:
        event = session.event
        return SessionMetadata(
            ref=ref,
            event_name=_event_field(event, "EventName", default=ref.grand_prix),
            circuit=_event_field(event, "Location", default="UNKNOWN"),
            country=_event_field(event, "Country", default="UNKNOWN"),
            n_drivers=int(laps["Driver"].nunique()),
            n_laps=int(len(laps)),
            loaded_with_telemetry=with_telemetry,
        )


def _event_field(event: object, key: str, *, default: str) -> str:
    """Read a field from a FastF1 event object defensively."""
    try:
        value = event[key]  # type: ignore[index]
    except (KeyError, TypeError, IndexError):
        return default
    return default if value is None else str(value)
