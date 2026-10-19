# Module Contracts & Interfaces

> Status: **PROPOSED — awaiting approval**
> Owner: Chief Architect (Agent 0)

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

class FeatureBuilder(Protocol):
    def build(self, session: LoadedSession) -> "FeatureFrame": ...

class Predictor(Protocol):
    """Common shape for ML models so strategy depends on the interface, not sklearn."""
    def fit(self, X, y) -> "Predictor": ...
    def predict(self, X) -> "numpy.ndarray": ...
    def metrics(self) -> dict[str, float]: ...
```

---

## 3. Layer-by-layer public API

### `telemetry/` (Agent 1)
```python
class FastF1SessionLoader:                      # implements SessionLoader
    def __init__(self, settings: Settings) -> None: ...
    def load(self, ref: SessionRef, *, with_telemetry: bool = False) -> LoadedSession: ...

def validate_laps(df: pandas.DataFrame) -> pandas.DataFrame:   # raises SchemaValidationError
    ...
def filter_valid_laps(df: pandas.DataFrame) -> pandas.DataFrame:  # IsAccurate & not Deleted & LapTime present
    ...
```
> Owns the **only** `import fastf1` in the codebase. Converts fastf1 → `LoadedSession`.

### `features/` (Agent 2)
```python
@dataclass(frozen=True)
class FeatureFrame:
    data: pandas.DataFrame        # conforms to FEATURES_SCHEMA
    feature_names: tuple[str, ...]
    target_name: str | None

def build_lap_features(session: LoadedSession) -> FeatureFrame: ...
```

### `analytics/` (Agent 2)
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

### `models/` (Agent 3)
```python
class LapTimePredictor:                          # implements Predictor
    def __init__(self, settings: Settings) -> None: ...
    def fit(self, features: FeatureFrame) -> "LapTimePredictor": ...
    def predict(self, features: FeatureFrame) -> numpy.ndarray: ...
    def metrics(self) -> dict[str, float]: ...   # MAE, RMSE, R²
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "LapTimePredictor": ...
```

### `strategy/` (Agent 4)
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

### `visualization/` (Agent 5)
```python
def driver_pace_figure(pace: list[DriverPace]) -> plotly.graph_objects.Figure: ...
def tire_deg_figure(stints: list[StintSummary]) -> plotly.graph_objects.Figure: ...
# Pure: typed analytics objects in, Figure out. No data loading inside viz.
```

---

## 4. DataFrame schema contracts

DataFrames that cross a boundary are validated. Each schema declares column names,
dtypes, and nullability. (ADR-0003 covers `pandera` vs. hand-rolled.)

**`LAPS_SCHEMA`** — produced by `telemetry`, consumed by `features`/`analytics`:

| column | dtype | null? | notes |
|--------|-------|-------|-------|
| `Driver` | str | no | 3-letter code |
| `Team` | str | no | |
| `LapNumber` | int | no | |
| `Stint` | int | no | |
| `Compound` | category(`TireCompound`) | no | normalized to the enum |
| `TyreLife` | int | no | laps on current set |
| `LapTime_s` | float | yes | seconds; null = no time set |
| `IsAccurate` | bool | no | |
| `Deleted` | bool | no | |
| `IsValid` | bool | no | derived: accurate & not deleted & laptime present |

> Note we convert FastF1's `LapTime` (timedelta) into `LapTime_s` (float seconds)
> at the boundary, so no downstream layer deals with timedeltas or fastf1 dtypes.

**`FEATURES_SCHEMA`** — produced by `features`, consumed by `analytics`/`models`:
adds engineered columns (`tyre_life_sq`, `fuel_corrected_laptime_s`,
`compound_ohe_*`, `is_outlap`, `is_inlap`, …). Specified fully in Phase 2.
