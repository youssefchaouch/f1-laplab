# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is (and is not)

F1 LapLab (`f1-laplab`, importable as `f1strategy`) turns historical Formula 1
timing data into validated, leakage-safe lap-level datasets. The pipeline ends
at a `LapFeatureDataset` — there is **no trained model, inference service, race
replay, or race-strategy simulator**. Keep README/docs claims aligned with that;
the repo has deliberately been scrubbed of overclaiming (see
`FINALIZATION-REPORT-F1-LAPLAB.md`).

## Commands

The venv is at `.venv`. If activation is restricted, call
`.\.venv\Scripts\python.exe` directly instead of `python`.

```powershell
py -3.12 -m venv .venv            # Python >= 3.12 required
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

python -m pytest -m "not network"               # offline suite (the default gate)
python -m pytest tests/features/test_lap_features.py -k duplicate   # one test
python -m pytest -m network                     # needs FastF1 cache/internet
python -m ruff check src\ tests\ examples\
python -m mypy src\ tests\ examples\            # strict mode
git diff --check

python examples\synthetic_pipeline.py           # offline end-to-end demo, no network
python scripts\acquire_sample.py                # OPTIONAL: hits network, writes FastF1 cache
```

`tests/telemetry/test_loader_network.py` is the only `network`-marked test; run
it only when cached data or external access is intended. Everything else must
stay deterministic and offline.

## Architecture

Strict one-direction layering inside `src/f1strategy/` (ADR-0001):

`config` → `domain` ← `telemetry` → `features`

| Package | Owns |
|---|---|
| `domain` | `SessionRef`, `SessionMetadata`, `LoadedSession`, `LapRecord`, `SessionType`/`TireCompound` enums, `SessionLoader` protocol, the error hierarchy, and `LAPS_SCHEMA`. |
| `config` | `Settings` (frozen, `Settings.load()` reads `F1STRATEGY_*` env vars), `ProjectPaths` (absolute, anchored at the `pyproject.toml` marker), `configure_logging`. |
| `telemetry` | FastF1 loading, provider→canonical conversion, lap validation. **The only package allowed to import `fastf1`.** |
| `features` | `build_lap_features(LoadedSession) -> LapFeatureDataset`. |
| `strategy` | Retained illustrative one-stop ranking from explicit uncalibrated assumptions. Outside the LapLab pipeline — do not grow it or present it as a simulator. |

Data flow:

```
SessionRef -> FastF1SessionLoader -> fastf1_laps_to_frame
  -> validate_laps (LAPS_SCHEMA + canonical validity) -> LoadedSession
       -> lap_records_from_session -> tuple[LapRecord, ...]
       -> build_lap_features      -> LapFeatureDataset
```

### Invariants that tests enforce

- **FastF1 containment (ADR-0002).** `tests/architecture/test_import_boundaries.py`
  greps `src/` and fails the build on any `import fastf1` outside `telemetry/`.
  Nothing downstream ever sees a raw `fastf1.Session`; raw FastF1 exceptions are
  wrapped in `SessionLoadError`.
- **Schema contract (ADR-0003).** `LAPS_SCHEMA` is `strict=True, coerce=True`.
  Reference columns through the constants in `domain/schemas.py` (`S.LAP_TIME_S`,
  …), never string literals. Timedeltas are converted to float seconds at the
  boundary; nullability is deliberate (`Stint`/`TyreLife` as `Int64`, pit markers
  as `boolean`, `TrackStatus` as `string`) — never fill missing values with `0`.
- **No import-time side effects (ADR-0004).** The FastF1 cache is enabled in
  `FastF1SessionLoader.__init__` from injected `Settings`, and `paths.ensure()`
  is the only mkdir. Importing the package, the demo, and offline tests touch
  nothing on disk outside the configured dirs.
- **Canonical validity.** One rule, `domain.models.lap_is_valid` =
  `is_accurate and not deleted and lap_time_s is not None`. Pit-in/out and
  non-green track status are *warnings*, not exclusions. `lap_records_from_session`
  raises `SchemaValidationError` if a frame's `IsValid` disagrees with the rule.
- **Leakage safety.** Features for target lap `n` use only eligible observations
  in exact slots `n-3`…`n-1`, same driver, same session. History never crosses
  session boundaries; missing slots stay missing (no backfill, no nearest-valid
  substitution). Identifiers and `target_lap_time_s` are kept in separate frames
  from the feature matrix. Duplicate eligible `(driver, lap_number)` raises
  `SchemaValidationError` rather than being silently deduped. Tests include
  perturbation/append checks that future laps cannot change earlier feature rows
  — preserve those properties in any change here.

Frozen `slots=True` dataclasses are the norm for domain types; `SessionRef` is
frozen specifically so it can be a cache key.

## Working conventions

From `motorsport_copilot_playbook/COPILOT_RULES.md` (the surrounding playbook
and `PROJECT_STATUS.md` are a **historical archive** of an abandoned sprint
roadmap — don't treat them as current scope):

- Smallest coherent change for the stated task; no speculative placeholder
  modules, abstractions, or features "common in similar projects".
- Read the existing files and tests before proposing code; don't trust earlier
  summaries (including the many `SPRINT-*.md` / `*-REPORT.md` files at the repo
  root) over the actual source.
- Handle missing, malformed, duplicate, and incomplete data explicitly. Never
  swallow exceptions or substitute fabricated data.
- Keep network access at the telemetry boundary; unit tests stay offline.
- Report the exact commands run and their real results.
- Justify any new dependency and name the simpler alternative considered; don't
  change the Python version or dependency manager.

## Testing notes

`tests/` mirrors the package layout. The central fixture is `raw_fastf1_laps`
in `tests/conftest.py` — a frame shaped like `fastf1.core.Laps` (timedelta
`LapTime`, mixed-case/null compounds, a no-time lap) that exercises the whole
conversion→validation→features path with zero network. The `settings` fixture
roots `ProjectPaths` at `tmp_path` so tests never write the real cache.

## Documentation map

- `docs/architecture/ARCHITECTURE.md` — current implemented boundaries.
- `docs/adr/` — ADR-0001 layering, 0002 FastF1 boundary, 0003 schema contracts,
  0004 config/paths, 0005 canonical lap record. ADRs are immutable: supersede
  with a new one rather than editing.
- `data/cache/` holds a local, git-ignored FastF1 cache (a 2024 Monaco race may
  be present); no dataset is distributed with the repo and none is required.
  `F1STRATEGY_CACHE_DIR` relocates it.
