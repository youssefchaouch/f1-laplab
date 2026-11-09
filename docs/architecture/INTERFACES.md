# Historical Module Contracts & Interfaces

> This document combines implemented interfaces with deferred proposals from
> the original platform plan. **Every section heading below states its status**:
> the `analytics/`, `models/`, `strategy/`, and `visualization/` headings in
> section 3 are marked *proposed/deferred* or *superseded* and describe code
> that does not exist. Sections 1, 2, and 4 and the `telemetry/` and
> `features/` subsections describe current APIs. See
> [the implemented architecture](ARCHITECTURE.md).

These are the contracts each layer exposes. **No specialist agent may change a
contract on this page without architect sign-off** — that is the whole point of
defining them up front. Signatures below are the *intended* public API; bodies
are written later, one module at a time.

The code blocks are illustrative Python 3.12 (with type hints). They live in
`src/f1strategy/domain/` once approved.

---

## 1. Domain types (`domain/`)

Pure, dependency-free. Shared vocabulary for the whole system.

```python
# domain/enums.py
from enum import Enum

class SessionType(str, Enum):
    PRACTICE_1 = "FP1"
    PRACTICE_2 = "FP2"
    PRACTICE_3 = "FP3"
    QUALIFYING = "Q"
    SPRINT = "S"
    RACE = "R"

class TireCompound(str, Enum):
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTERMEDIATE = "INTERMEDIATE"
    WET = "WET"
    UNKNOWN = "UNKNOWN"
```

```python
# domain/models.py
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class SessionRef:
    """Immutable identity of a session. Hashable -> usable as a cache key."""
    year: int
    grand_prix: str          # e.g. "Monaco"
    session: SessionType

@dataclass(frozen=True, slots=True)
class SessionMetadata:
    ref: SessionRef
    event_name: str
    circuit: str
    country: str
    n_drivers: int
    n_laps: int
    loaded_with_telemetry: bool

@dataclass(frozen=True, slots=True)
class LoadedSession:
    """The single object the telemetry layer hands downstream.

    `laps` conforms to LAPS_SCHEMA (see §4). Downstream layers consume the
    frame + metadata and NEVER touch the underlying fastf1 objects.
    """
    metadata: SessionMetadata
    laps: "pandas.DataFrame"      # validated against LAPS_SCHEMA
```

```python
# domain/errors.py
class F1StrategyError(Exception): ...
class SessionLoadError(F1StrategyError): ...      # network / fastf1 failure
class SchemaValidationError(F1StrategyError): ... # data shape contract broken
class InsufficientDataError(F1StrategyError): ... # not enough laps to analyse
```

---

## 2. Protocols (the seams for dependency injection)

Defined in `domain/protocols.py`. Concrete classes live in their layers and are
wired at the composition root. Protocols let tests substitute fakes — no network.

```python
# domain/protocols.py
from typing import Protocol

class SessionLoader(Protocol):
    """Implemented by telemetry.FastF1SessionLoader. Tests use a fake."""
    def load(self, ref: SessionRef, *, with_telemetry: bool = False) -> LoadedSession: ...

# Future feature-builder adapter (not implemented): Sprint 04 currently exposes
# f1strategy.features.build_lap_features(session) -> LapFeatureDataset.
# The implemented return contract is documented in §3 below.
```

Predictor integration is **proposed/deferred**; no predictor API is implemented.
Any future model must take model inputs only from `LapFeatureDataset.features`
and use `LapFeatureDataset.labels` separately for training/evaluation. Its
identifiers and metadata provide traceability, not predictors. See the
implemented Sprint 04 contract below; do not treat the former `FeatureFrame`
proposal as an active interface.

---

## 3. Layer-by-layer public API

### `telemetry/` (Agent 1)
```python
class FastF1SessionLoader:                      # implements SessionLoader
    def __init__(self, settings: Settings) -> None: ...
    def load(self, ref: SessionRef, *, with_telemetry: bool = False) -> LoadedSession: ...

def validate_laps(df: pandas.DataFrame) -> pandas.DataFrame:   # raises SchemaValidationError
    ...
def validate_laps_with_report(df: pandas.DataFrame) -> LapValidationReport:
    ...  # row reasons, deterministic counts, and cleaned canonical laps
def filter_valid_laps(df: pandas.DataFrame) -> pandas.DataFrame:
    ...  # canonical-valid laps with duplicate (Driver, LapNumber) groups excluded
    ...
```
> Owns the **only** `import fastf1` in the codebase. Converts fastf1 → `LoadedSession`.

### `features/` (implemented Sprint 04 contract)
```python
@dataclass(frozen=True)
class LapFeatureDataset:
    metadata: LapFeatureMetadata
    identifiers: pandas.DataFrame
    features: pandas.DataFrame     # exactly the approved prior-only feature columns
    labels: pandas.Series          # target_lap_time_s, kept outside features
    excluded_laps: tuple[ExcludedLap, ...]

def build_lap_features(session: LoadedSession) -> LapFeatureDataset: ...
```
The actual public contract is implemented in
`f1strategy.features.lap_features`. `identifiers`, `features`, and `labels`
have aligned deterministic row order; identifiers are trace keys, not model
inputs. The label is the target lap's observed time, and the only v1 features
are `previous_lap_time_s`, `prior_3lap_mean_time_s`, and
`prior_3lap_valid_count`, each computed from exact prior lap-number slots.
Eligible target duplicates raise `SchemaValidationError`; the builder does not
consume `validate_laps_with_report().cleaned_laps`, which excludes duplicate
identity groups. This replaces the illustrative `FeatureFrame`/`FEATURES_SCHEMA`
proposal below; no `FEATURES_SCHEMA` is currently implemented.

### `analytics/` (proposed/deferred; not implemented)
```python
@dataclass(frozen=True)
class DriverPace:
    driver: str
    mean_laptime_s: float
    median_laptime_s: float
    best_laptime_s: float
    valid_laps: int

@dataclass(frozen=True)
class StintSummary:
    driver: str
    stint: int
    compound: TireCompound
    n_laps: int
    deg_per_lap_s: float          # slope of laptime vs tyre life

def driver_pace(session: LoadedSession) -> list[DriverPace]: ...
def tire_degradation(session: LoadedSession) -> list[StintSummary]: ...
def teammate_comparison(session: LoadedSession, team: str) -> "TeammateDelta": ...
```
No `f1strategy.analytics` package exists. The types and functions above are
illustrative future work from the original platform plan, not a current API.

### `models/` (proposed/deferred; not implemented)
```python
class LapTimePredictor:                          # implements Predictor
    def __init__(self, settings: Settings) -> None: ...
    def fit(self, dataset: LapFeatureDataset) -> "LapTimePredictor": ...
    def predict(self, dataset: LapFeatureDataset) -> numpy.ndarray: ...
    def metrics(self) -> dict[str, float]: ...   # MAE, RMSE, R²
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "LapTimePredictor": ...
```
This is illustrative future work, not a current public API. A future
implementation must use `dataset.features` as `X` and keep `dataset.labels`
separate; prediction must not consume labels. No model training or evaluation
is part of Sprint 04.

### `strategy/` (superseded proposal; this API is not implemented)
```python
@dataclass(frozen=True)
class StrategyRecommendation:
    driver: str
    recommended_pit_lap: int
    compound_in: TireCompound
    gain_estimate_s: float
    rationale: str                 # human-readable strategist explanation

def recommend_pit_window(session: LoadedSession, driver: str) -> StrategyRecommendation: ...
def undercut_analysis(session: LoadedSession, attacker: str, target: str) -> "UndercutResult": ...
```
Neither function above exists. `f1strategy.strategy` is implemented, but with a
different, narrower API: it exposes the retained illustrative one-stop ranking
engine (`StrategyConfig`, `TireDegradation`, `Stint`, `RaceStrategy`) in
`f1strategy.strategy.engine`, built from explicit uncalibrated assumptions. It
consumes no `LoadedSession` and is not a race-strategy simulator.

### `visualization/` (proposed/deferred; not implemented)
```python
def driver_pace_figure(pace: list[DriverPace]) -> plotly.graph_objects.Figure: ...
def tire_deg_figure(stints: list[StintSummary]) -> plotly.graph_objects.Figure: ...
# Pure: typed analytics objects in, Figure out. No data loading inside viz.
```
No `f1strategy.visualization` package exists and plotly is **not** a project
dependency. This section is retained only as a record of the original proposal.

---

## 4. DataFrame schema contracts

The canonical telemetry boundary frame is validated with `LAPS_SCHEMA`. Sprint
04 feature outputs have their own fixed, documented columns and typed result
contract, but are not currently represented by a Pandera `FEATURES_SCHEMA`.
(ADR-0003 covers `pandera` vs. hand-rolled contracts.)

**`LAPS_SCHEMA`** — produced by `telemetry`, consumed by `features`:

| column | dtype | null? | notes |
|--------|-------|-------|-------|
| `Driver` | str | no | 3-letter code |
| `Team` | str | no | |
| `LapNumber` | int | no | |
| `Stint` | nullable int | yes | |
| `Compound` | str | no | normalized to `TireCompound`; `UNKNOWN` sentinel |
| `TyreLife` | nullable int | yes | laps on current set |
| `LapTime_s` | float | yes | seconds; null = no time set |
| `IsAccurate` | bool | no | |
| `Deleted` | bool | no | |
| `IsValid` | bool | no | derived: accurate & not deleted & laptime present |
| `IsPitInLap` | nullable bool | yes | derived from FastF1 `PitInTime`; missing stays unknown |
| `IsPitOutLap` | nullable bool | yes | derived from FastF1 `PitOutTime`; missing stays unknown |
| `TrackStatus` | nullable str | yes | preserved FastF1 status code; non-clear values warn, not validity inputs |

`validate_laps` rejects schema violations and inconsistent `IsValid` values.
`validate_laps_with_report` preserves invalid rows in its input, explains
exclusions and warnings, and excludes every row sharing a duplicate driver/lap
identity from its cleaned result.

> Note we convert FastF1's `LapTime` (timedelta) into `LapTime_s` (float seconds)
> at the boundary, so no downstream layer deals with timedeltas or fastf1 dtypes.

There is no implemented `FEATURES_SCHEMA`. Sprint 04's feature output is the
typed, documented `LapFeatureDataset` above. Target-row compound, tyre state,
pit markers, track status, validity flags, target time, final results, and
future-derived aggregates are not predictors because their availability before
the target lap begins is not established or they are inherently post-cutoff.
