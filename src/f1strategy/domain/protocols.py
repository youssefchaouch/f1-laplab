"""Structural interfaces (Protocols) — the seams for dependency injection.

WHY THIS FILE EXISTS
    Downstream layers and tests depend on *capabilities*, not concrete classes.
    ``SessionLoader`` describes "something that can load a session" without naming
    FastF1. The real ``FastF1SessionLoader`` lives in the telemetry layer; a test
    can supply a fake that returns a fixture ``LoadedSession`` with no network.
    This is what makes analytics/models/strategy testable offline (ADR-0002).

DESIGN
    ``typing.Protocol`` (structural typing): an implementer satisfies the
    interface by shape, with no import-time inheritance coupling back to the
    domain. ``@runtime_checkable`` so ``isinstance`` checks work in tests if needed.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from f1strategy.domain.models import LoadedSession, SessionRef


@runtime_checkable
class SessionLoader(Protocol):
    """Anything that can turn a ``SessionRef`` into a ``LoadedSession``."""

    def load(self, ref: SessionRef, *, with_telemetry: bool = False) -> LoadedSession:
        ...
