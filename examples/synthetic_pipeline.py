"""Run the F1 LapLab pipeline on a small, explicitly synthetic session."""

from __future__ import annotations

import pandas as pd

from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.features import build_lap_features
from f1strategy.telemetry.conversion import fastf1_laps_to_frame, lap_records_from_session
from f1strategy.telemetry.validation import validate_laps, validate_laps_with_report


def build_synthetic_session() -> LoadedSession:
    """Create an in-memory FastF1-shaped fixture and validate its canonical form."""
    raw_laps = pd.DataFrame(
        {
            S.DRIVER: ["SYN", "SYN", "SYN", "SYN", "SYN"],
            S.TEAM: ["Synthetic Example Team"] * 5,
            S.LAP_NUMBER: [1, 2, 3, 4, 5],
            S.STINT: [1, 1, 1, 1, 1],
            S.COMPOUND: ["MEDIUM"] * 5,
            S.TYRE_LIFE: [1, 2, 3, 4, 5],
            "LapTime": pd.to_timedelta([90, 91, 92, 94, 95], unit="s"),
            S.IS_ACCURATE: [True] * 5,
            S.DELETED: [False, False, True, False, False],
            "PitInTime": pd.to_timedelta([pd.NaT, pd.NaT, pd.NaT, pd.NaT, pd.NaT]),
            "PitOutTime": pd.to_timedelta([pd.Timedelta(0), pd.NaT, pd.NaT, pd.NaT, pd.NaT]),
            S.TRACK_STATUS: ["1"] * 5,
        }
    )
    laps = validate_laps(fastf1_laps_to_frame(raw_laps))
    ref = SessionRef(2024, "Synthetic Demonstration", SessionType.RACE)
    metadata = SessionMetadata(
        ref=ref,
        event_name="Synthetic Demonstration",
        circuit="Synthetic Circuit",
        country="Not applicable",
        n_drivers=int(laps[S.DRIVER].nunique()),
        n_laps=len(laps),
        loaded_with_telemetry=False,
    )
    return LoadedSession(metadata=metadata, laps=laps)


def main() -> None:
    """Print validation, structured records, and leakage-safe features."""
    session = build_synthetic_session()
    report = validate_laps_with_report(session.laps)
    records = lap_records_from_session(session)
    dataset = build_lap_features(session)

    print("F1 LapLab pipeline demonstration (synthetic data; no real F1 data).")
    print(f"Canonical validation: {report.summary}")
    print(f"Structured LapRecord values: {len(records)}")
    print(f"Eligible feature/target rows: {len(dataset.labels)}")
    print("Features and target (lap 3 is deleted and therefore not a target):")
    output = pd.concat(
        [
            dataset.identifiers[["driver", "lap_number"]],
            dataset.features,
            dataset.labels,
        ],
        axis=1,
    )
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
