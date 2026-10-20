# Project Status

## Current stage
**Sprint 03 baseline strategy engine implemented and verified.** This was a user-directed reprioritization of the roadmap's Sprint 03 data-validation milestone, which remains outstanding.

## Verified existing components
✅ **Domain layer** — Complete and well-structured
  - Models: SessionRef, SessionMetadata, LoadedSession, LapRecord (frozen dataclasses)
  - Enums: SessionType, TireCompound (str enums with normalization)
  - Protocols: SessionLoader (runtime_checkable)
  - Schemas: LAPS_SCHEMA (pandera), column constants; optional Stint/TyreLife values remain nullable
  - Errors: F1StrategyError, SessionLoadError, SchemaValidationError, InsufficientDataError

✅ **Telemetry layer** — Anti-corruption boundary implemented
  - FastF1SessionLoader (only place fastf1 is imported)
  - fastf1_laps_to_frame (pure conversion function)
  - validate_laps, filter_valid_laps (validation functions)
  - Converts FastF1 timedeltas to float seconds, normalizes compounds, derives IsValid flag

✅ **Configuration layer** — Dependency injection ready
  - Settings (frozen dataclass with env overrides)
  - ProjectPaths (absolute, deterministic paths)
  - configure_logging (idempotent, stream-based)

✅ **Strategy layer** — Deterministic baseline engine
  - Models one-stop strategies from explicit race, tire-degradation, pit-loss, and stint/pit-window assumptions.
  - Uses one shared baseline lap time across compounds with linear tire degradation; age is zero on the first lap of each stint. Inputs are illustrative, not calibrated, and the model has no initial compound pace offsets or sporting compound rules.
  - Ranks complete race strategies, explains the winner, and reports time deltas for alternatives. No telemetry or network access is required.

✅ **Tests** — Comprehensive and offline
  - test_conversion.py — conversion, optional-value, identity, and deterministic record tests (no network)
  - test_lap_record.py — LapRecord invariants and validity-rule tests
  - test_schemas.py — 3 tests validating boundary contracts
  - test_import_boundaries.py — 1 test enforcing fastf1 isolation
  - test_loader_network.py — 1 marked network test (Monaco 2024)
  - test_engine.py — deterministic strategy model, feasibility, ranking, and input validation (offline)
  - conftest.py — 2 fixtures (raw_fastf1_laps, settings)

✅ **Architecture enforcement** — ADRs documented and mechanically tested
  - ADR-0001: Layered clean architecture, src/ layout, pip install -e .
  - ADR-0002: FastF1 confined to telemetry (test_import_boundaries.py)
  - ADR-0003: DataFrame schema contracts at boundaries (pandera)
  - ADR-0004: Configuration and paths (absolute, injected)

## Verified baseline
- **Python version:** ≥3.12 (configured in pyproject.toml: requires-python = ">=3.12")
- **Dependency/install command:** `pip install -e ".[dev]"` (core + ruff, mypy, pytest, pandas-stubs)
- **Test command:** `python -m pytest -m "not network"` → ✅ 58 passed, 1 deselected
- **Lint command:** `python -m ruff check src/ tests/` → ✅ All checks passed (4 UP042/UP037 fixed)
- **Type-check command:** `python -m mypy src/ tests/` → ✅ Success: no issues found in 25 source files
- **Quality gates configured:**
  - Ruff: line-length=100, select=[F, E, W, I, B, C4, UP]
  - MyPy: strict=true, Python 3.12, fastf1.* imports ignored
  - Pytest: -q (quiet), network marker for test isolation
- **Current entry points:**
  - Planned CLI: `f1strategy` (from pyproject.toml [project.scripts], but cli:main not yet implemented)
  - Current usage: programmatic imports of loaders, validators, models
- **Existing data/cache location:**
  - Root: `data/` (in .gitignore)
  - Structure: `data/raw/`, `data/processed/`, `data/cache/` (created by ProjectPaths.ensure())
  - Cache used by FastF1SessionLoader (absolute paths, CWD-independent)
- **Current architecture observations:**
  - Src/ layout correctly implemented with src/f1strategy/ (setuptools.packages.find)
  - Package installable via `pip install -e .` (verified structure, not yet tested in audit environment)
  - Dependencies pinned with lower bounds (>=), resolved versions in requirements.txt
  - No circular dependencies; strict import boundaries enforced by test_import_boundaries.py
  - All tests import from f1strategy.* (unambiguous imports)
  - Type annotations: complete; deferred via `from __future__ import annotations`; no `Any` shortcuts

## Completed sprints
- ✅ **Sprint 00** — Repository audit and baseline verification (complete)
  - Verified: domain, telemetry, config layers; 9 offline tests; architecture enforcement
  - Risks identified: CLI missing, prediction target undefined, validation flag unused

- ✅ **Ruff linting fixes** — Modernize enums and type annotations (complete)
  - Fixed: SessionType/TireCompound (str, Enum → StrEnum); loader.py annotations
  - Files changed: enums.py (2), loader.py (2)
  - Status: 0 Ruff violations

- ✅ **MyPy type-checking fixes** — Resolve 9 errors (complete)
  - Added: pandas-stubs>=2.2 (dev dependency)
  - Fixed: tmp_path fixture annotation (conftest.py:38), laps parameter type (loader.py:67)
  - Files changed: pyproject.toml (1), conftest.py (2), loader.py (1)
  - Status: 0 mypy errors (verified with `python -m mypy src/ tests/`)

- ✅ **Sprint 01 — Data contracts and canonical lap representation**
  - Added immutable `LapRecord` with `SessionRef` and driver identity; validity is computed by the shared canonical rule.
  - Preserved missing stint and tyre-life values as nullable; retained the schema's `UNKNOWN` sentinels for team/compound and required non-null accuracy/deleted flags.
  - Added `lap_records_from_session` and documented the design/trade-offs in ADR-0005.
  - Verification: 28 offline tests passed, Ruff passed, strict MyPy passed.

- ✅ **Sprint 02 — Historical data acquisition and validation**
  - Added explicit `InsufficientDataError` handling for empty sessions and sessions with no valid laps, using the existing canonical `IsValid` rule. Provider failures remain `SessionLoadError`; schema failures remain `SchemaValidationError`.
  - Added offline loader tests for successful loads and metadata, configured cache path, provider lookup/load errors, empty data, schema-invalid data, and no-valid-lap data.
  - Added `scripts/acquire_sample.py` for the 2024 Monaco Grand Prix Race sample, using the existing `SessionLoader` abstraction and settings/cache configuration.
  - Documented the sample command and `F1STRATEGY_CACHE_DIR` override in the README. FastF1 remains responsible for cache reuse; no separate cache layer was introduced.
  - Verification: targeted telemetry tests — 19 passed; offline suite — 34 passed, 1 network test deselected; Ruff passed; strict MyPy passed. The network acquisition test was not run.

- ✅ **Sprint 03 — Baseline F1 race strategy engine (user-directed scope)**
  - Added a pure strategy layer for explicit, configurable linear tire-degradation assumptions, stint-time estimates, feasible one-stop generation, pit-loss accounting, deterministic ranking, and alternatives with time deltas.
  - Constraints and inputs are validated; recommendation includes its assumptions and an explanation. Tire age is zero on the first lap of each stint.
  - Values remain caller-supplied and illustrative, not calibrated. All compounds share one baseline pace and differ only by degradation rate; initial compound pace offsets, sporting compound rules, multi-stop strategies, traffic, weather, fuel, and safety cars are not modeled.
  - Verification: offline suite — 58 passed, 1 network test deselected; Ruff passed; strict MyPy passed; `git diff --check` passed.
  - Reprioritization note: the existing roadmap's Sprint 03 data-validation/normalization milestone remains outstanding; this implementation does not claim to complete it.

## Current sprint
**Sprint 03 baseline engine complete.** Existing roadmap data validation/normalization remains pending.

## Known decisions (Verified)
- Develop locally in PyCharm. ✓
- Use historical Formula 1 data initially. ✓ (FastF1 configured as data source)
- Prioritize MLOps lifecycle and reproducibility. ✓ (Settings, logging, schema contracts in place)
- Do not build Foundry into this local project unless explicitly decided later. ✓ (Out of scope)
- Layered architecture enforced by import tests. ✓
- Dependency injection (not globals or singletons). ✓
- No network access required for unit tests. ✓

## Immediate risks / architectural concerns
1. **CLI entrypoint not implemented** — pyproject.toml declares `f1strategy = "f1strategy.cli:main"` but `cli.py` does not exist. This will fail when invoking the installed entry point unless a composition root is added. **Mitigation:** Address this only in a sprint that requires a runnable CLI.

2. **Schema validation opt-out flag unused** — Settings.validate_schemas defaults to True, but neither fastf1_laps_to_frame nor validate_laps checks this flag. If validation becomes a bottleneck, the flag needs wiring before hot-path optimization. **Mitigation:** Document this for future; currently low priority.

3. **Prediction target undefined** — PROJECT_PLAN.md mentions "defensible lap-time predictions" but does not specify: next-lap time? average-lap pace under conditions? comparative lap delta? This affects feature engineering, model choice, and data splits. **Mitigation:** Clarify before Sprint 04 (feature engineering).

## Recommended next sprint
**Review roadmap sequencing** before selecting the next sprint. The planned data validation/normalization milestone remains outstanding; do not treat the user-directed Sprint 03 strategy baseline as completing that separate roadmap work.
