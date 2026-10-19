# AI Motorsport Strategy Framework

A Python framework for building reproducible Formula 1 telemetry and race-strategy
analysis. The project is being developed in small, testable sprints; its current
foundation focuses on domain contracts, FastF1 ingestion, and offline validation.

## Current status

**Sprint 00 (repository audit) and Sprint 01 (canonical lap contract) are complete.**
Sprint 02, historical data acquisition, is planned and awaits approval. See the
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
The latest recorded offline result is **28 passed, 1 deselected**; Ruff and
strict MyPy also passed.

## Planned work and current limits

The roadmap proceeds from historical data acquisition and cache behavior
(Sprint 02) to validation/normalization, leakage-safe features, baseline model
evaluation, experiment tracking, inference, monitoring, retraining, and a
minimal strategy simulation. These are **planned**, not currently implemented.
There is no implemented ML predictor, pit-stop optimizer, race/strategy
simulator, dashboard, or database.

Although scikit-learn, Plotly, and an optional Streamlit extra are declared as
dependencies, their planned modeling and application capabilities are not yet
present. `pyproject.toml` also declares an `f1strategy` console script, but its
target CLI module has not been implemented; use the Python package interfaces
directly for now.

## Project documents

- [Project plan and roadmap](motorsport_copilot_playbook/PROJECT_PLAN.md)
- [Current project status](motorsport_copilot_playbook/PROJECT_STATUS.md)
- [Working rules](motorsport_copilot_playbook/COPILOT_RULES.md)