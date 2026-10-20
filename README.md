# AI Motorsport Strategy Framework

A Python framework for building reproducible Formula 1 telemetry and race-strategy
analysis. The project is being developed in small, testable sprints; its current
foundation focuses on domain contracts, FastF1 ingestion, and offline validation.

## Current status

**Sprints 00–03 are implemented as worked in this repository.** Sprint 03 was
reprioritized from the roadmap's data-validation milestone to a deterministic,
assumption-driven one-stop strategy baseline; roadmap data validation remains
outstanding. See the
[project status](motorsport_copilot_playbook/PROJECT_STATUS.md) and
[project plan](motorsport_copilot_playbook/PROJECT_PLAN.md).

## Implemented capabilities

- **Domain contracts:** session references and metadata, loaded-session and
  immutable per-lap models, session/tyre enums, a `SessionLoader` protocol, and
  the Pandera `LAPS_SCHEMA`.
- **Telemetry boundary:** `FastF1SessionLoader` loads sessions using the
  configured cache; conversion normalizes lap times and compounds; validation
  enforces the lap schema and provides valid-lap filtering. FastF1 imports are
  confined to the telemetry package.
- **Configuration:** immutable settings with environment overrides and
  project-rooted data/cache paths.
- **Strategy baseline:** explicit inputs drive a deterministic one-stop
  comparison with linear tire degradation, configurable pit windows and stint
  limits, ranked alternatives, and time deltas.
- **Logging:** explicit, idempotent logging setup; importing the library does
  not configure logging.

The test suite includes deterministic offline tests and a separately marked
network/cache-dependent FastF1 integration test.

## Architecture and decisions

The package uses a `src/` layout. Telemetry adapts FastF1 data into owned domain
contracts; schemas validate DataFrames at boundaries, and downstream code can
use the immutable `LapRecord` representation. See:

- [Architecture overview](docs/architecture/ARCHITECTURE.md)
- [Dependency graph](docs/architecture/DEPENDENCY_GRAPH.md)
- [Module contracts and interfaces](docs/architecture/INTERFACES.md)
- [Current-state review](docs/architecture/CURRENT_STATE_REVIEW.md)
- [Architecture Decision Records](docs/adr/README.md), including
  [ADR-0001: layered architecture](docs/adr/0001-layered-clean-architecture.md),
  [ADR-0002: FastF1 boundary](docs/adr/0002-fastf1-anti-corruption-boundary.md),
  [ADR-0003: schema contracts](docs/adr/0003-dataframe-schema-contracts.md),
  [ADR-0004: configuration and paths](docs/adr/0004-configuration-and-paths.md),
  and [ADR-0005: canonical lap record](docs/adr/0005-canonical-lap-record.md).

## Prerequisites and setup (Windows PowerShell)

Python **3.12 or newer** and `pip` are required. From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The editable install uses the package configuration in `pyproject.toml`; the
`dev` extra installs pytest, Ruff, MyPy, and pandas stubs. If PowerShell blocks
activation, either use the Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Quality checks

Run from the repository root:

```powershell
python -m pytest -m "not network"
python -m ruff check src/ tests/
python -m mypy src/ tests/
```

The offline test command excludes the test marked `network`, which may require
FastF1 cache data or network access. Run the full suite with
`python -m pytest` only when that integration test's requirements are available.
The latest verified offline result is **58 passed, 1 deselected**; Ruff and
strict MyPy also passed.

## Acquiring the historical sample

After installing the project in editable mode, run this from the repository
root to load the **2024 Monaco Grand Prix Race** through the existing FastF1
loader:

```powershell
python scripts/acquire_sample.py
```

FastF1 uses its cache under the configured project data directory by default.
To use a different cache location, set `F1STRATEGY_CACHE_DIR` before running:

```powershell
$env:F1STRATEGY_CACHE_DIR = "C:\f1strategy-cache"
python scripts/acquire_sample.py
```

The script reports the session and lap/driver counts. FastF1 manages cache
reuse; this project does not implement a second cache layer. Acquisition can
require network access when the requested data is not already cached.

## Baseline strategy calculation

The strategy engine accepts explicit assumptions and does not load telemetry or
call FastF1. For example:

```python
from f1strategy.domain.enums import TireCompound
from f1strategy.strategy import StrategyConfig, TireDegradation, recommend_strategy

assumptions = StrategyConfig(
    race_laps=57,
    baseline_lap_time_s=92.0,
    pit_stop_loss_s=22.0,
    tire_degradation=(
        TireDegradation(TireCompound.SOFT, 0.08),
        TireDegradation(TireCompound.MEDIUM, 0.05),
        TireDegradation(TireCompound.HARD, 0.03),
    ),
    min_stint_laps=5,
    max_stint_laps=40,
    pit_window_start_lap=15,
    pit_window_end_lap=35,
)
result = recommend_strategy(assumptions)
```

These values are illustrative, not calibrated to a circuit, car, driver, or
race. Every compound uses the same baseline lap time; compounds differ only in
the configured linear degradation rate. Consequently, the model may prefer the
compound with the lowest configured degradation for both stints. Lap time is
modeled as baseline plus degradation rate multiplied by tire age; tire age
starts at zero on each stint's first lap. Pit loss is added once. The engine
models exactly one stop, does not enforce sporting compound rules, and does not
account for initial compound pace offsets, fuel, traffic, weather, safety cars,
or pit-window dynamics. Its recommendation is fastest only under the supplied
assumptions, not a real-world optimum.

## Planned work and current limits

The roadmap's data validation/normalization, leakage-safe features, baseline
model evaluation, experiment tracking, inference, monitoring, retraining, and
prediction-backed strategy simulation remain planned. The current strategy
engine is an illustrative deterministic baseline; it is not an ML predictor, a
calibrated pit-stop optimizer, or a full race simulator. There is no dashboard
or database.

Although scikit-learn, Plotly, and an optional Streamlit extra are declared as
dependencies, their planned modeling and application capabilities are not yet
present. `pyproject.toml` also declares an `f1strategy` console script, but its
target CLI module has not been implemented; use the Python package interfaces
directly for now.

## Project documents

- [Project plan and roadmap](motorsport_copilot_playbook/PROJECT_PLAN.md)
- [Current project status](motorsport_copilot_playbook/PROJECT_STATUS.md)
- [Working rules](motorsport_copilot_playbook/COPILOT_RULES.md)