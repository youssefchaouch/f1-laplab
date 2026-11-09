# Historical Repository Review — Weaknesses, Improvements, Decisions

> This is an original planning review and contains superseded observations.
> The current project is F1 LapLab; see [the implemented architecture](ARCHITECTURE.md)
> and the repository-root README for current scope.

Honest review of the code as it exists today, the way a senior reviewer would
write it on a PR. The point is not to criticize — it is to show that the rebuild
is *deliberate*.

## A. What exists today

| File | State | Verdict |
|------|-------|---------|
| `telemetry/loader.py` | `load_session()` + import-time cache enable, relative path `../data/cache` | Keep the idea, rebuild the implementation |
| `scripts/load_telemetry.py` | Notebook-style script: load + filter + groupby + `print` | Delete; split logic into `telemetry` + `analytics` |
| `telemetry/lap_analysis.py` | Empty | Placeholder |
| `strategy/pit_strategy.py` | Empty | Placeholder |
| `visualization/plots.py` | Empty | Placeholder |
| `main.py`, `requirements.txt`, `README.md` | Empty | To be authored |

## B. Weaknesses (ranked by impact)

1. **Leaky abstraction — `load_session` returns a raw `fastf1.Session`.**
   Every consumer is now coupled to FastF1's object model. If FastF1 changes,
   the whole codebase changes. → Introduce `LoadedSession` (validated frame +
   metadata) as the boundary type. *(ADR-0002)*

2. **Import-time side effect.** `fastf1.Cache.enable_cache(...)` runs the moment
   anything imports `loader.py`. That makes the module untestable in isolation,
   couples import to the filesystem, and fires even when you only wanted a type.
   → Cache configuration moves into the loader's `__init__`, driven by `Settings`.

3. **Fragile relative path `../data/cache`.** Resolves against the *current working
   directory*, not the project. Run from the repo root and it silently creates
   `../data/cache` *outside* the project. → `Settings` resolves absolute paths from
   a discovered project root. *(ADR-0004)*

4. **Duplication risk.** The prompt's `loader.py` uses `"data/cache"`; the on-disk
   one uses `"../data/cache"`. Two truths already. → One loader, one config source.

5. **No validation / no schema.** `laps["IsAccurate"] == True` assumes columns and
   dtypes that FastF1 is free to change. Nothing guarantees `LapTime` exists. →
   `LAPS_SCHEMA` validated at the boundary; `SchemaValidationError` on drift. *(ADR-0003)*

6. **No error handling.** A bad GP name or an offline network throws a raw FastF1
   exception with no context. → Wrap in `SessionLoadError` with the `SessionRef`.

7. **Analysis logic trapped in a script.** `valid_laps` filtering and per-driver
   pace aggregation are real domain logic living in a `print`-driven script. →
   `telemetry.filter_valid_laps()` and `analytics.driver_pace()`, both testable.

8. **No types beyond a single signature, no logging, no tests, no packaging.**
   → Type hints everywhere, structured logging at the root, `pytest` suite,
   `pyproject.toml` with `src/` layout.

9. **Mixed structure expectations.** Agents 2 reference `analytics/` and
   `features/` packages that don't exist yet; the tree has flat packages. →
   Unified under `src/f1strategy/` per ARCHITECTURE §4.

## C. Improvements (what the rebuild buys)

- **Testable without a network** — the #1 thing reviewers check. Protocols +
  fixture frames mean `analytics`, `models`, and `strategy` test offline.
- **A blast radius of one** when FastF1 changes.
- **A readable repo** — eight named responsibilities instead of four half-empty folders.
- **A real CI story** — `ruff` (lint), `mypy` (types), `pytest` (tests), and an
  import-boundary test that mechanically proves the architecture holds.
- **A portfolio narrative** — the `docs/` folder *is* the differentiator. Most
  junior portfolios have code; almost none have ADRs and a dependency graph.

## D. Decisions requiring your approval

Implementation is blocked on these. Recommended option in **bold**.

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Project layout | **`src/` layout + `pyproject.toml` (installable `f1strategy`)** vs. flat top-level packages | `src/` layout — it's the professional default and the single biggest "this person ships software" signal |
| D2 | Data crossing boundaries | **Hybrid: typed objects + schema-validated DataFrames** vs. raw DataFrames vs. fully typed (no DataFrames) | Hybrid — DataFrames where pandas earns its keep, typed objects for results |
| D3 | Schema validation tool | **Add `pandera`** vs. hand-rolled validators (strict to listed stack) | `pandera` — declarative, ~20 lines, industry-standard. Falls back cleanly if you'd rather not add a dep |
| D4 | Package name | **`f1strategy`** vs. `motorsport` vs. `ams` | `f1strategy` — short, importable, unambiguous |
| D5 | Notebooks | **Keep `notebooks/` as consumers only** vs. drop entirely | Keep — they demo the library; they never get imported by it |

## E. Migration plan (Phase 1, after approval)

1. Add `pyproject.toml`; create `src/f1strategy/` package skeleton.
2. Author `config/` (settings, paths, logging) and `domain/` (types, enums,
   protocols, errors) — the two leaves first, since everything depends on them.
3. Rebuild `telemetry/` against the new contracts; delete `scripts/load_telemetry.py`.
4. Port the existing valid-lap filter and pace aggregation into
   `telemetry.filter_valid_laps` and `analytics.driver_pace` (Phase 3).
5. Wire a smoke test that loads Monaco 2024 (the session already cached) through
   the new path end-to-end.

Each step is one module, with the written rationale the execution rules require.
