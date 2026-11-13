"""Evaluate baseline upcoming-lap-time models with leave-one-weekend-out splits.

Default: a small synthetic fixture with a built-in degradation pattern. Its
numbers only show that the evaluation runs; they say nothing about real F1 data.

With ``--session YEAR GRAND_PRIX SESSION`` (repeatable, at least two race
weekends) real sessions are loaded through FastF1, which reads and may write to
the FastF1 cache and may make network requests.
"""

from __future__ import annotations

import argparse
import random

import pandas as pd

from f1strategy.config.settings import Settings
from f1strategy.domain import schemas as S
from f1strategy.domain.enums import SessionType
from f1strategy.domain.models import LoadedSession, SessionMetadata, SessionRef
from f1strategy.features import LapFeatureDataset, build_lap_features
from f1strategy.modeling import MODEL_NAMES, EvaluationReport, evaluate_leave_one_weekend_out
from f1strategy.telemetry.conversion import fastf1_laps_to_frame
from f1strategy.telemetry.loader import FastF1SessionLoader
from f1strategy.telemetry.validation import validate_laps

SYNTHETIC_WEEKENDS = (("Synthetic A", 78.0), ("Synthetic B", 92.0), ("Synthetic C", 101.0))


def _synthetic_dataset(grand_prix: str, base_s: float, rng: random.Random) -> LapFeatureDataset:
    drivers, laps = 6, 30
    rows = [(d, n) for d in range(drivers) for n in range(1, laps + 1)]
    times = [base_s + 0.25 * d + 0.06 * n + rng.gauss(0.0, 0.35) for d, n in rows]
    raw = pd.DataFrame(
        {
            S.DRIVER: [f"S{d:02d}" for d, _ in rows],
            S.TEAM: ["Synthetic Team"] * len(rows),
            S.LAP_NUMBER: [n for _, n in rows],
            S.STINT: [1] * len(rows),
            S.COMPOUND: ["MEDIUM"] * len(rows),
            S.TYRE_LIFE: [n for _, n in rows],
            "LapTime": pd.to_timedelta(times, unit="s"),
            S.IS_ACCURATE: [True] * len(rows),
            S.DELETED: [False] * len(rows),
            "PitInTime": pd.to_timedelta([pd.NaT] * len(rows)),
            "PitOutTime": pd.to_timedelta([pd.NaT] * len(rows)),
            S.TRACK_STATUS: ["1"] * len(rows),
        }
    )
    frame = validate_laps(fastf1_laps_to_frame(raw))
    metadata = SessionMetadata(
        ref=SessionRef(2024, grand_prix, SessionType.RACE),
        event_name=grand_prix,
        circuit="Synthetic Circuit",
        country="Not applicable",
        n_drivers=drivers,
        n_laps=len(frame),
        loaded_with_telemetry=False,
    )
    return build_lap_features(LoadedSession(metadata=metadata, laps=frame))


def _print_report(report: EvaluationReport) -> None:
    header = f"{'held-out weekend':<32}{'rows':>7}  " + "  ".join(
        f"{name + ' MAE':>24}" for name in MODEL_NAMES
    )
    print(header)
    for result in report.weekends:
        year, grand_prix = result.weekend
        cells = "  ".join(f"{result.metrics[name].mae_s:>22.3f} s" for name in MODEL_NAMES)
        print(f"{f'{year} {grand_prix}':<32}{result.predictable_rows:>7}  {cells}")
    print()
    print(f"Pooled over all held-out rows (ridge alpha={report.alpha}):")
    for name in MODEL_NAMES:
        m = report.pooled[name]
        print(
            f"  {name:<20} rows={m.rows:<6} MAE={m.mae_s:8.3f}s  "
            f"median AE={m.median_ae_s:7.3f}s  RMSE={m.rmse_s:9.3f}s"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session",
        nargs=3,
        action="append",
        metavar=("YEAR", "GRAND_PRIX", "SESSION"),
        help="real session to include (repeat; needs at least two race weekends)",
    )
    parser.add_argument("--alpha", type=float, default=1.0, help="ridge penalty (default 1.0)")
    args = parser.parse_args()

    datasets: list[LapFeatureDataset] = []
    if args.session:
        loader = FastF1SessionLoader(Settings.load())
        for year, grand_prix, code in args.session:
            print(f"Loading {year} {grand_prix} {code} through FastF1 (uses cache).")
            session = loader.load(SessionRef(int(year), grand_prix, SessionType(code)))
            datasets.append(build_lap_features(session))
        print("Real FastF1 sessions; targets include pit, safety-car and red-flag laps.")
    else:
        print("Synthetic fixture with a built-in pattern: numbers demonstrate the")
        print("evaluation mechanics only and say nothing about real Formula 1 data.")
        rng = random.Random(2024)
        datasets = [_synthetic_dataset(gp, base, rng) for gp, base in SYNTHETIC_WEEKENDS]
    print()
    _print_report(evaluate_leave_one_weekend_out(datasets, alpha=args.alpha))


if __name__ == "__main__":
    main()
