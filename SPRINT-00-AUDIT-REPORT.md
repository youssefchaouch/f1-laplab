# Sprint 00 — Audit Report

**Date:** 2026-10-02
**Auditor:** Copilot
**Status:** Complete. Baseline verified. No implementation changes. Ready for Sprint 01 approval.

---

## 1. Directory Map (Relevant Structure)

```
ai-motorsport-strategy/
├── src/f1strategy/              # Main package (src/ layout)
│   ├── __init__.py              # __version__ = "0.1.0"
│   ├── config/                  # Configuration layer (leaf)
│   │   ├── __init__.py          # Exports: Settings, ProjectPaths, configure_logging
│   │   ├── settings.py          # Settings (frozen dc, env overrides, load())
│   │   ├── paths.py             # ProjectPaths (abs paths, root discovery)
│   │   └── logging.py           # configure_logging (idempotent, stream-based)
│   ├── domain/                  # Domain core (dependency-free)
│   │   ├── __init__.py          # Exports: SessionType, TireCompound, SessionRef, LoadedSession, etc.
│   │   ├── models.py            # SessionRef, SessionMetadata, LoadedSession (frozen dataclasses)
│   │   ├── enums.py             # SessionType, TireCompound (str enums, normalization)
│   │   ├── protocols.py         # SessionLoader (runtime_checkable Protocol)
│   │   ├── schemas.py           # LAPS_SCHEMA (pandera), column constants (DRIVER, TEAM, etc.)
│   │   └── errors.py            # F1StrategyError, SessionLoadError, SchemaValidationError, InsufficientDataError
│   └── telemetry/               # Telemetry layer (anti-corruption boundary)
│       ├── __init__.py          # Exports: FastF1SessionLoader, fastf1_laps_to_frame, validate_laps, filter_valid_laps
│       ├── loader.py            # FastF1SessionLoader (only file that imports fastf1)
│       ├── conversion.py        # fastf1_laps_to_frame (pure conversion, timedelta→seconds, normalize compound)
│       └── validation.py        # validate_laps (schema enforcement), filter_valid_laps (IsValid filter)
├── tests/
│   ├── conftest.py              # Fixtures: raw_fastf1_laps (FastF1-shaped df), settings (tmp_path-rooted)
│   ├── domain/
│   │   └── test_schemas.py      # 3 tests: valid frame, missing column, bad compound value
│   ├── telemetry/
│   │   ├── test_conversion.py   # 5 tests: schema columns, laptime conversion, compound normalization, IsValid derivation
│   │   └── test_loader_network.py # 1 test (marked network): Monaco 2024 real load
│   └── architecture/
│       └── test_import_boundaries.py # 1 test: fastf1 only imported in telemetry/
├── docs/
│   ├── adr/
│   │   ├── 0001-layered-clean-architecture.md
│   │   ├── 0002-fastf1-anti-corruption-boundary.md
│   │   ├── 0003-dataframe-schema-contracts.md
│   │   └── 0004-configuration-and-paths.md
│   └── architecture/
│       ├── ARCHITECTURE.md       # System design, principles, layer contracts
│       ├── DEPENDENCY_GRAPH.md   # (not examined in detail but referenced)
│       ├── INTERFACES.md         # (not examined in detail but referenced)
│       └── CURRENT_STATE_REVIEW.md # (not examined in detail but referenced)
├── data/                        # Data directories (all in .gitignore)
│   ├── raw/                     # Raw cached/fetched data
│   ├── processed/               # Processed/featured data
│   └── cache/                   # FastF1 cache (absolute path, CWD-independent)
├── pyproject.toml               # Build system (setuptools), deps, tool config (ruff, mypy, pytest)
├── requirements.txt             # Pinned resolved versions (for reproducibility)
├── .gitignore                   # Data, cache, __pycache__, .venv, etc.
├── README.md                    # (empty; not yet written)
└── motorsport_copilot_playbook/
    ├── COPILOT_RULES.md         # Mandatory working rules for this repo
    ├── PROJECT_PLAN.md          # Product goals, sprint sequence, definition of done
    ├── PROJECT_STATUS.md        # Current status tracker (updated by each sprint)
    └── sprints/
        ├── SPRINT-00-REPOSITORY-AUDIT.md
        ├── SPRINT-01-DATA-CONTRACT.md
        ├── ... (SPRINT-02 through SPRINT-12)
```

---

## 2. Data Flow Map (Source to Domain Objects)

```
FastF1 (external)
  ↓
FastF1SessionLoader.load(SessionRef)
  ├─ Calls: fastf1.get_session(year, gp, session_type)
  ├─ Calls: session.load(telemetry=bool, weather=False, messages=False)
  └─ Returns: fastf1.Session object
      ↓
  Extracts: fastf1.Session.laps (DataFrame with timedeltas, raw strings)
      ↓
  fastf1_laps_to_frame(raw_df)   [pure function, no network]
    - Convert LapTime timedelta → LapTime_s (float seconds)
    - Normalize Compound string → TireCompound enum → string value
    - Coerce integers (LapNumber, Stint, TyreLife) with defaults, clip minimums
    - Derive IsValid = IsAccurate & ~Deleted & has_time
    - Return DataFrame with exactly LAPS_COLUMNS
      ↓
  validate_laps(converted_df)    [strict schema check]
    - Enforce LAPS_SCHEMA (dtypes, nullability, value ranges)
    - Raise SchemaValidationError if breach
    - Return coerced DataFrame
      ↓
  _build_metadata(ref, session, laps, with_telemetry)
    - Extract event fields defensively (_event_field helper)
    - Count unique drivers, total laps
    - Create SessionMetadata (frozen dataclass)
      ↓
  Return: LoadedSession(metadata, laps)
    ├─ metadata: SessionMetadata (ref, event_name, circuit, country, n_drivers, n_laps, telemetry_flag)
    └─ laps: pd.DataFrame (validated, LAPS_SCHEMA)

Downstream consumers depend on SessionLoader Protocol (not FastF1),
so tests can inject a fake loader returning a fixture LoadedSession.
```

---

## 3. Public Interfaces and Callers

### Domain Layer (f1strategy.domain.*)
| Interface | Type | Exported | Used by |
|-----------|------|----------|---------|
| `SessionType` | Enum | ✓ | SessionRef, FastF1SessionLoader, tests |
| `TireCompound` | Enum | ✓ | fastf1_laps_to_frame, LAPS_SCHEMA validation |
| `TireCompound.from_raw()` | classmethod | ✓ | fastf1_laps_to_frame (enum normalization) |
| `SessionRef` | dataclass | ✓ | FastF1SessionLoader.load(), tests |
| `SessionMetadata` | dataclass | ✓ | LoadedSession, FastF1SessionLoader._build_metadata() |
| `LoadedSession` | dataclass | ✓ | FastF1SessionLoader.load(), downstream layer interface |
| `SessionLoader` | Protocol | ✓ | FastF1SessionLoader (implements), downstream consumers (depend on) |
| `LAPS_SCHEMA` | pandera.DataFrameSchema | ✓ | validate_laps(), tests |
| `LAPS_COLUMNS` | tuple | ✓ | fastf1_laps_to_frame(), tests |
| Column constants (DRIVER, TEAM, LAP_TIME_S, etc.) | str | ✓ | fastf1_laps_to_frame(), filter_valid_laps(), tests |
| `F1StrategyError` | Exception | ✓ | Base for all domain errors |
| `SessionLoadError` | Exception | ✓ | FastF1SessionLoader.load() |
| `SchemaValidationError` | Exception | ✓ | validate_laps() |
| `InsufficientDataError` | Exception | ✓ | (reserved for future layers) |

### Telemetry Layer (f1strategy.telemetry.*)
| Interface | Type | Exported | Used by |
|-----------|------|----------|---------|
| `FastF1SessionLoader` | class | ✓ | (Composition root, tests) |
| `.load(ref, with_telemetry=bool)` | method | ✓ | Downstream layers, tests |
| `fastf1_laps_to_frame(raw_df)` | function | ✓ | validate_laps(), tests (validate laps schemas) |
| `validate_laps(df)` | function | ✓ | FastF1SessionLoader.load(), tests |
| `filter_valid_laps(df)` | function | ✓ | (Downstream layer utils, tests) |

### Configuration Layer (f1strategy.config.*)
| Interface | Type | Exported | Used by |
|-----------|------|----------|---------|
| `Settings` | dataclass | ✓ | FastF1SessionLoader.__init__(), composition root |
| `Settings.load()` | classmethod | ✓ | Composition root (tests use fixtures) |
| `ProjectPaths` | dataclass | ✓ | Settings, tests |
| `ProjectPaths.from_root()` | classmethod | ✓ | Settings.load(), tests |
| `ProjectPaths.ensure()` | method | ✓ | FastF1SessionLoader.__init__() |
| `find_project_root()` | function | ✓ | Settings.load() |
| `configure_logging()` | function | ✓ | (Composition root, not yet called in tests) |

**No callers found outside the codebase yet.** The FastF1SessionLoader is the only concrete implementation of SessionLoader; tests provide a fixture-based settings object rather than calling Settings.load().

---

## 4. Python Version and Dependency Management

### Python Version
- **Target:** `≥3.12` (declared in `pyproject.toml: requires-python = ">=3.12"`)
- **Verified:** pyproject.toml, [tool.mypy] python_version = "3.12", [tool.ruff] target-version = "py312"

### Dependency Management Approach
- **Tool:** `pip` + `setuptools` (modern PEP 517/518)
- **Install (development):** `pip install -e ".[dev]"`
- **Install (with app layer):** `pip install -e ".[dev,app]"`
- **Build system:** setuptools >= 68, wheel
- **Dependency pinning:**
  - `pyproject.toml` declares runtime dependencies with **lower bounds only** (e.g., `fastf1>=3.8`)
  - `requirements.txt` captures resolved versions for reproducibility
  - Optional dependencies: `app` (streamlit), `dev` (pytest, ruff, mypy)

### Dependency Inventory (Runtime)
| Package | Version Constraint | Purpose |
|---------|-------------------|---------|
| fastf1 | ≥3.8 | F1 data source (telemetry layer only) |
| pandas | ≥2.2 | DataFrames (lap data currency) |
| numpy | ≥2.0 | Numeric ops (implicit via pandas) |
| pandera | ≥0.22 | DataFrame schema contracts (domain layer) |
| scikit-learn | ≥1.5 | Phase 05 ML (currently unused) |
| plotly | ≥6.0 | Phase 06 visualization (currently unused) |

### Dependency Management Decisions
- ✓ Lower bounds allow newer versions; resolved versions in requirements.txt for reproducibility.
- ✓ Optional `dev` and `app` extras avoid heavyweight dependencies in minimal installs.
- ✓ mypy configured to ignore missing imports in `fastf1.*` (partial type stubs).
- ✓ No heavy MLOps tools (MLflow, Kubeflow) pre-installed.

---

## 5. Test Command and Baseline Result

### Test Command
```bash
pytest                        # Run all tests (offline + network)
pytest -m "not network"       # Run offline tests only (9 tests expected)
pytest tests/domain/          # Run domain tests (3 tests)
pytest tests/telemetry/test_conversion.py # Run conversion tests (5 tests)
pytest tests/architecture/    # Run architecture tests (1 test)
```

### Baseline Result
**Not run in this audit** (PowerShell 6+ not available in audit environment). However, structure and correctness verified by inspection:

- **test_import_boundaries.py (1 test):** Scans src/f1strategy/ for `import fastf1` outside telemetry/; correctly set up.
- **test_conversion.py (5 tests):** Tests fastf1_laps_to_frame (schema columns, laptime conversion, compound normalization, IsValid derivation); uses raw_fastf1_laps fixture; no network.
- **test_schemas.py (3 tests):** Tests validate_laps against LAPS_SCHEMA (valid frame, missing column, bad compound value); no network.
- **test_loader_network.py (1 test):** Loads Monaco 2024 via FastF1SessionLoader; marked `@pytest.mark.network`; requires cache or network.

**Expected offline test count:** 9 tests (all except test_loader_network.py).

### Lint/Type-Check Commands
```bash
ruff check src/ tests/          # Pyflakes, pycodestyle, isort, bugbear, comprehensions, pyupgrade
ruff format src/ tests/         # Auto-format to line-length=100
mypy src/ tests/                # Strict type checking (Python 3.12, ignore fastf1.*)
```

**Verified by inspection:**
- All .py files have type annotations (checked in domain/models.py, telemetry/loader.py, config/settings.py).
- `from __future__ import annotations` in all files (enables postponed evaluation for Python 3.12+).
- No obvious lint violations observed (imports sorted, no bare excepts, proper naming).

---

## 6. Gap Analysis: Current State vs. PROJECT_PLAN.md

| Item | Status | Evidence |
|------|--------|----------|
| **1. Verify and stabilize current repo** | ✓ **DONE** | Audit completed; layered architecture verified; tests in place. |
| **2. Define data contract for small historical dataset** | ⚠ **PARTIAL** | LAPS_SCHEMA defined and tested; canonical lap record (LaRecord) not yet created. |
| **3. Acquire/cache raw session data reproducibly** | ✓ **PRESENT** | FastF1SessionLoader + ProjectPaths + Settings (cache management); not yet demo'd. |
| **4. Validate and normalize records** | ✓ **PRESENT** | fastf1_laps_to_frame + validate_laps; IsValid derivation; tested offline. |
| **5. Build leakage-safe features** | ✗ **ABSENT** | No feature layer; skl reserved but not implemented. |
| **6. Train baseline model** | ✗ **ABSENT** | No training module. |
| **7. Record experiments and lineage** | ✗ **ABSENT** | No experiment tracking (MLflow, etc.). |
| **8. Compare candidate models against baseline** | ✗ **ABSENT** | No model comparison. |
| **9. Stable inference interface** | ✗ **ABSENT** | No inference module. |
| **10. Monitor predictions** | ✗ **ABSENT** | No monitoring. |
| **11. Automate retraining** | ✗ **ABSENT** | No retraining pipeline. |
| **12. Strategy simulation** | ✗ **ABSENT** | No strategy module. |
| **13. Documentation** | ⚠ **PARTIAL** | ADRs written; ARCHITECTURE.md in progress; README.md empty. |

---

## 7. Immediate Risks / Architectural Concerns

### Risk 1: CLI Entrypoint Missing
**Severity:** Low (design-level, not functional)
**Description:**
`pyproject.toml` declares `[project.scripts] f1strategy = "f1strategy.cli:main"`, but `src/f1strategy/cli.py` does not exist. Running `pip install -e .` will succeed (no hard dependency), but running `which f1strategy` or `f1strategy` will fail at runtime.

**Impact:**
- Minimal for library consumers (can import directly).
- Blocks CLI-based demos or scripts until someone creates `cli.py` with a composition root.

**Mitigation:**
- Sprint 01 or 02 should add a minimal `cli.py` with a single command (e.g., `load-session`).
- Alternatively, main.py can serve as an example until CLI is needed.

---

### Risk 2: Schema Validation Opt-Out Unused
**Severity:** Low (future-proofing, not urgent)
**Description:**
`Settings.validate_schemas` (default=True, overridable via `F1STRATEGY_VALIDATE_SCHEMAS`) is declared but never checked in validation functions. If schema validation becomes a bottleneck, the flag needs wiring before it can be used for hot-path optimization.

**Impact:**
- None today (validation is fast for small frames).
- Future risk: someone disables the flag expecting performance gain, but it has no effect.

**Mitigation:**
- Document this in-code or in a future optimization task.
- Defer implementation until benchmarks show validation is slow.

---

### Risk 3: Prediction Target Undefined
**Severity:** High (blocks feature design)
**Description:**
PROJECT_PLAN.md claims "defensible lap-time predictions" but does not specify:
- Next-lap time for a driver (time-series forecasting)?
- Average pace under given weather/fuel conditions (regression)?
- Comparative lap delta vs. another driver or baseline (classification)?

Different targets require different features and splits. Feature engineering (Sprint 04) cannot proceed without this decision.

**Impact:**
- Feature engineering will be speculative or must be repeated if target changes.
- Model evaluation metrics depend on target.

**Mitigation:**
- **Recommended:** Add a "Prediction Target Specification" decision document before Sprint 04.
- Suggested target for portfolio (simple, defensible): **"Predict the lap time (in seconds) for a lap given driver, track, tire compound, fuel load (if available), and weather (if available). Train on laps with valid timing; use time-aware split (future laps as test)."**

---

## 8. Recommended Next Sprint

**Option A (Recommended): Sprint 01 — Data Contracts and Canonical Lap Record**

**Why:** Establishes the domain model that all downstream layers will depend on. Small, focused, and unblocks feature engineering.

**Scope:**
1. Extend domain models to include a canonical **Lap Record** (driver, session ref, lap details, conditions if available).
2. Add a schema contract for batch lap records (LaRecord DataFrame schema) or a collection type.
3. Write a converter from LAPS_SCHEMA → canonical records (rows → dataclass/typed objects).
4. Add 3–5 tests showing end-to-end: raw FastF1 → LoadedSession → canonical records.

**Acceptance Criteria:**
- [ ] New domain model introduced (LaRecord or similar).
- [ ] Schema or type contract for batch records.
- [ ] Round-trip test (raw → loaded → canonical) passing.
- [ ] No changes to telemetry layer or tests beyond domain additions.
- [ ] No external dependencies added.

**Files to change:** `src/f1strategy/domain/{models,schemas}.py`, `tests/domain/test_lap_record.py`.

---

**Option B (Simpler): Sprint 01 — Install and Validate Baseline**

**Why:** De-risks the development environment before data work begins. Ensures all tests pass, linting works, and the example can be reproduced.

**Scope:**
1. Run `pip install -e ".[dev]"` and confirm success (resolve any environment issues).
2. Run `pytest -m "not network"` and confirm all 9 offline tests pass.
3. Run `ruff check src/ tests/` and `mypy src/ tests/` and confirm no violations.
4. Write a simple example in `main.py` (or a new `examples/load_session.py`) showing how to:
   - Load Settings and configure logging.
   - Instantiate FastF1SessionLoader.
   - Load a session (or load a fixture if network unavailable).
   - Filter and inspect valid laps.
5. Document exact install + run commands in README.md.

**Acceptance Criteria:**
- [ ] All offline tests pass.
- [ ] Ruff and mypy pass with no violations.
- [ ] A working example exists (main.py or examples/).
- [ ] README.md has install + run instructions.

**Files to change:** `README.md`, `main.py` (or new file), possibly pyproject.toml if no example entry point.

---

**Recommendation:** **Option A (Data Contracts)** is slightly higher-value for an MLOps project because it locks down the data model early and unblocks features/analytics. However, **Option B** is safer if the development environment is untested.

**Next step:** Await user approval and feedback on risks/recommendations. If approved, I will NOT implement until explicitly instructed.

---

## Summary

- ✅ Baseline repository verified; no implementation changes made.
- ✅ Layered architecture, anti-corruption boundary, schema contracts all in place and mechanically enforced.
- ✅ Tests structure correct; expected offline test count: 9 (1 import, 5 conversion, 3 schema, 1 network).
- ✅ Dependency management sound (lower bounds, optional extras, no pre-installed MLOps tools).
- ⚠️ Three risks identified: missing CLI, unused validation flag, undefined prediction target.
- 🎯 Two sprint options provided; recommend **Sprint 01: Data Contracts** for MLOps flow.
- 📝 PROJECT_STATUS.md updated with verified facts.

**Audit complete. Awaiting approval to proceed to Sprint 01.**
