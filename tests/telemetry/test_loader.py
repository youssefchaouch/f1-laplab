"""Offline tests for the FastF1 session loader."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from f1strategy.config.settings import Settings
from f1strategy.domain.enums import SessionType
from f1strategy.domain.errors import (
    InsufficientDataError,
    SchemaValidationError,
    SessionLoadError,
)
from f1strategy.domain.models import LoadedSession, SessionRef
from f1strategy.telemetry.loader import FastF1SessionLoader


@pytest.fixture
def session_ref() -> SessionRef:
    return SessionRef(2024, "Monaco", SessionType.RACE)


def _mock_session(laps: pd.DataFrame, *, load: Mock | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        laps=laps,
        event={
            "EventName": "Monaco Grand Prix",
            "Location": "Monaco",
            "Country": "Monaco",
        },
        load=load or Mock(),
    )


def _disable_fastf1_cache(monkeypatch: pytest.MonkeyPatch) -> Mock:
    enable_cache = Mock()
    monkeypatch.setattr(
        "f1strategy.telemetry.loader.fastf1.Cache.enable_cache",
        enable_cache,
    )
    return enable_cache


def test_load_returns_validated_session_and_uses_configured_cache(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    raw_fastf1_laps: pd.DataFrame,
    session_ref: SessionRef,
) -> None:
    enable_cache = _disable_fastf1_cache(monkeypatch)
    session = _mock_session(raw_fastf1_laps)
    get_session = Mock(return_value=session)
    monkeypatch.setattr("f1strategy.telemetry.loader.fastf1.get_session", get_session)

    loaded = FastF1SessionLoader(settings).load(session_ref, with_telemetry=True)

    assert isinstance(loaded, LoadedSession)
    assert loaded.metadata.ref == session_ref
    assert loaded.metadata.event_name == "Monaco Grand Prix"
    assert loaded.metadata.circuit == "Monaco"
    assert loaded.metadata.country == "Monaco"
    assert loaded.metadata.n_drivers == 2
    assert loaded.metadata.n_laps == 3
    assert loaded.metadata.loaded_with_telemetry
    assert enable_cache.call_args.args == (str(settings.paths.cache),)
    get_session.assert_called_once_with(2024, "Monaco", "R")
    session.load.assert_called_once_with(telemetry=True, weather=False, messages=False)


def test_provider_lookup_failure_raises_session_load_error(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    session_ref: SessionRef,
) -> None:
    _disable_fastf1_cache(monkeypatch)
    get_session = Mock(side_effect=RuntimeError("provider unavailable"))
    monkeypatch.setattr("f1strategy.telemetry.loader.fastf1.get_session", get_session)

    with pytest.raises(SessionLoadError, match="provider unavailable") as error:
        FastF1SessionLoader(settings).load(session_ref)

    assert isinstance(error.value.__cause__, RuntimeError)


def test_provider_load_failure_raises_session_load_error(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    raw_fastf1_laps: pd.DataFrame,
    session_ref: SessionRef,
) -> None:
    _disable_fastf1_cache(monkeypatch)
    provider_error = RuntimeError("session data unavailable")
    session = _mock_session(raw_fastf1_laps, load=Mock(side_effect=provider_error))
    monkeypatch.setattr(
        "f1strategy.telemetry.loader.fastf1.get_session",
        Mock(return_value=session),
    )

    with pytest.raises(SessionLoadError, match="session data unavailable") as error:
        FastF1SessionLoader(settings).load(session_ref)

    assert error.value.__cause__ is provider_error


def test_empty_lap_results_raise_insufficient_data_error(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    raw_fastf1_laps: pd.DataFrame,
    session_ref: SessionRef,
) -> None:
    _disable_fastf1_cache(monkeypatch)
    session = _mock_session(raw_fastf1_laps.iloc[:0].copy())
    monkeypatch.setattr(
        "f1strategy.telemetry.loader.fastf1.get_session",
        Mock(return_value=session),
    )

    with pytest.raises(InsufficientDataError, match="contains no laps"):
        FastF1SessionLoader(settings).load(session_ref)


def test_schema_invalid_laps_raise_schema_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    raw_fastf1_laps: pd.DataFrame,
    session_ref: SessionRef,
) -> None:
    _disable_fastf1_cache(monkeypatch)
    invalid_laps = raw_fastf1_laps.assign(LapNumber=[0, 2, 1])
    session = _mock_session(invalid_laps)
    monkeypatch.setattr(
        "f1strategy.telemetry.loader.fastf1.get_session",
        Mock(return_value=session),
    )

    with pytest.raises(SchemaValidationError):
        FastF1SessionLoader(settings).load(session_ref)


def test_nonempty_laps_without_valid_laps_raise_insufficient_data_error(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    raw_fastf1_laps: pd.DataFrame,
    session_ref: SessionRef,
) -> None:
    _disable_fastf1_cache(monkeypatch)
    invalid_laps = raw_fastf1_laps.assign(IsAccurate=[False, False, False])
    session = _mock_session(invalid_laps)
    monkeypatch.setattr(
        "f1strategy.telemetry.loader.fastf1.get_session",
        Mock(return_value=session),
    )

    with pytest.raises(InsufficientDataError, match="contains no valid laps"):
        FastF1SessionLoader(settings).load(session_ref)
