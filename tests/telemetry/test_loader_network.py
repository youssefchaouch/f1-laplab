"""End-to-end loader test against real FastF1 data.

Marked ``network`` so it can be skipped offline: ``pytest -m "not network"``.
It loads Monaco 2024 (already in the local cache) through the new path and
asserts the output honours the LoadedSession contract.
"""

from __future__ import annotations

import pytest

from f1strategy.config.settings import Settings
from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.models import LoadedSession, SessionRef
from f1strategy.telemetry.loader import FastF1SessionLoader


@pytest.mark.network
def test_load_monaco_2024_race() -> None:
    # Use the real project cache (where Monaco 2024 is already stored).
    loader = FastF1SessionLoader(Settings.load())
    ref = SessionRef(2024, "Monaco", SessionType.RACE)

    session = loader.load(ref)

    assert isinstance(session, LoadedSession)
    assert session.metadata.n_drivers > 10
    assert session.metadata.n_laps > 0
    # Output already conforms to the schema (loader validates internally).
    assert list(session.laps.columns) == list(S.LAPS_COLUMNS)
    assert session.laps[S.IS_VALID].sum() > 0
