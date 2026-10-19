"""Shared test fixtures.

The key fixture is ``raw_fastf1_laps`` — a DataFrame shaped like FastF1's own
``session.laps`` (timedelta LapTime, raw compound strings, a no-time lap). It lets
us test the entire conversion/validation path with zero network access, which is
the whole point of the anti-corruption boundary.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from f1strategy.config.settings import Settings


@pytest.fixture
def raw_fastf1_laps() -> pd.DataFrame:
    """A small frame mimicking ``fastf1.core.Laps`` (pre-conversion)."""
    return pd.DataFrame(
        {
            "Driver": ["VER", "VER", "LEC"],
            "Team": ["Red Bull Racing", "Red Bull Racing", "Ferrari"],
            "LapNumber": [1, 2, 1],
            "Stint": [1, 1, 1],
            "Compound": ["SOFT", "soft", None],          # mixed case + null -> UNKNOWN
            "TyreLife": [1, 2, 1],
            "LapTime": pd.to_timedelta(["0:01:14.5", "0:01:13.9", pd.NaT]),
            "IsAccurate": [True, True, False],
            "Deleted": [False, False, False],
        }
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings rooted at a temp dir so tests never touch the real cache."""
    from f1strategy.config.paths import ProjectPaths

    return Settings(paths=ProjectPaths.from_root(tmp_path))
