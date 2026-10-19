# AI Motorsport Strategy Assistant — System Architecture

> Status: **PROPOSED — awaiting approval**
> Owner: Chief Architect (Agent 0)
> Last updated: 2026-06-17

This document defines the architecture for the platform. No specialist agent
writes implementation code until the module boundaries and contracts described
here are approved.

---

## 1. What we are building (and what we are not)

We are building a **layered analytics platform** that ingests Formula 1 timing
and telemetry data, engineers features from it, runs analytics and machine
learning over those features, and produces **strategy recommendations** that are
surfaced through a dashboard.

The single most important architectural property for this project is that it must
read like a **system**, not a collection of scripts. A hiring manager skims the
repository and asks three questions:

1. Can I tell what each part does without reading every line? (module boundaries)
2. If FastF1 changes, breaks, or goes offline, how much of the codebase burns? (coupling)
3. Can this be tested without a network connection? (testability)

Every decision below optimizes for those three questions.

---

## 2. Architectural principles

These are non-negotiable and apply to every agent.

1. **Dependencies point inward.** Outer layers depend on inner layers, never the
   reverse. The domain core depends on nothing in this codebase.
2. **One external dependency, one boundary.** FastF1 is an external system. It is
   imported in **exactly one package** (`telemetry`). Everything else consumes a
   stable internal data contract. This is an *anti-corruption layer* (see ADR-0002).
3. **Data contracts are explicit.** Data crossing a layer boundary is either a
   typed object (dataclass / enum) or a DataFrame validated against a declared
   schema. No layer guesses at the columns another layer produced (see ADR-0003).
4. **No import-time side effects.** Importing a module must not touch the network,
   the filesystem, or global state. Configuration is injected, not executed on import.
5. **Type hints everywhere.** Public functions are fully annotated. `mypy` runs in CI.
6. **No notebook-centric design.** Notebooks may *consume* the library; the library
   never depends on a notebook. Analysis logic lives in importable, testable modules.
7. **Composition over import-time wiring.** Concrete implementations are wired
   together at a single *composition root* (the CLI / Streamlit entrypoint), not
   scattered as module-level globals.

---

## 3. Layered model

Eight layers. Each owns one responsibility. The arrow means "may import from".

```
            ┌─────────────────────────────────────────────┐
            │                  app / cli                   │  composition root
            │            (Streamlit, entrypoints)          │
            └───────────────┬─────────────────┬────────────┘
                            │                 │
                    ┌───────▼──────┐   ┌───────▼────────┐
                    │ visualization│   │    strategy    │
                    └───────┬──────┘   └───┬────────┬───┘
                            │              │        │
                       ┌────▼──────────────▼──┐ ┌───▼────┐
                       │      analytics       │ │ models │
                       └──────────┬───────────┘ └───┬────┘
                                  │                 │
                             ┌────▼─────────────────▼────┐
                             │         features          │
                             └─────────────┬─────────────┘
                                           │
                                   ┌───────▼────────┐
                                   │   telemetry    │  ← only FastF1 lives here
                                   └───────┬────────┘
                                           │
   ┌───────────────────────────────────────▼───────────────────────────────────┐
   │                          domain  (pure types + protocols)                  │
   └────────────────────────────────────────────────────────────────────────────┘
        config  (settings, paths, logging) — a cross-cutting leaf, depends on nothing
```

| Layer           | Owner agent | Responsibility | May import | Must NOT import |
|-----------------|-------------|----------------|-----------|-----------------|
| `domain`        | Architect   | Pure types, enums, protocols (interfaces). Zero third-party deps. | (stdlib only) | everything else |
| `config`        | Architect   | Settings, resolved paths, logging setup. | stdlib | every business layer |
| `telemetry`     | Agent 1     | FastF1 ingestion, validation, caching, session metadata. | domain, config | features, analytics, models, strategy, viz |
| `features`      | Agent 2     | Feature engineering over validated lap/telemetry frames. | domain, config | telemetry internals, fastf1, models, strategy, viz |
| `analytics`     | Agent 2     | Pace, tire degradation, stints, teammate comparison. | domain, config, features | fastf1, models, strategy, viz |
| `models`        | Agent 3     | Training, evaluation, experiment tracking, prediction. | domain, config, features | fastf1, strategy, viz |
| `strategy`      | Agent 4     | Pit/undercut/overcut, race simulation, recommendations. | domain, config, analytics, models | fastf1, viz |
| `visualization` | Agent 5     | Plotly figures from typed analytics/strategy outputs. | domain, analytics, strategy outputs | fastf1, telemetry |
| `app` / `cli`   | Agent 5     | Streamlit UI + composition root that wires concretes. | everything | — |
| `tests`         | Agent 6     | Unit / integration / regression tests. | everything | — |

**The hard rule:** `import fastf1` may appear **only** under `telemetry/`. A CI
check (Agent 6) enforces this with a grep-based test so the boundary cannot rot.

---

## 4. Target repository structure

We adopt a **`src/` layout with an installable package** (`f1strategy`). This is
the professional default: it forces you to install the package to use it (so
imports are unambiguous), keeps the import namespace clean, and makes the project
look like shippable software rather than a folder of scripts. See ADR-0001.

```
ai-motorsport-strategy/
├── pyproject.toml                # packaging, deps, tool config (ruff, mypy, pytest)
├── README.md
├── docs/
│   ├── architecture/             # this folder
│   └── adr/                      # architecture decision records
├── data/
│   ├── raw/                      # immutable source extracts (gitignored)
│   ├── processed/                # derived feature frames (gitignored)
│   └── cache/                    # FastF1 cache (gitignored)
├── src/f1strategy/
│   ├── domain/                   # types, enums, protocols      (Agent 0)
│   ├── config/                   # settings, paths, logging     (Agent 0)
│   ├── telemetry/                # FastF1 adapter               (Agent 1)
│   ├── features/                 # feature engineering          (Agent 2)
│   ├── analytics/                # pace / tire / stint / mate   (Agent 2)
│   ├── models/                   # ML pipelines                 (Agent 3)
│   ├── strategy/                 # strategy engine              (Agent 4)
│   ├── visualization/            # plotly figures               (Agent 5)
│   ├── app/                      # streamlit + composition root (Agent 5)
│   └── cli.py                    # `f1strategy` CLI entrypoint
├── tests/                        # mirrors src/ package layout  (Agent 6)
└── notebooks/                    # consume the library, never imported by it
```

> **Migration note.** The current repo has flat top-level packages
> (`telemetry/`, `strategy/`, `visualization/`). Moving them under
> `src/f1strategy/` is part of Phase 1. The old `scripts/load_telemetry.py`
> notebook-style script is deleted and its logic is split across `telemetry`
> (loading/validation) and `analytics` (pace aggregation). This is tracked in
> `CURRENT_STATE_REVIEW.md`.

---

## 5. Data flow (the happy path)

```
 user picks (year, GP, session)
        │
        ▼
 telemetry.SessionLoader.load(SessionRef)         → fastf1 network/cache I/O
        │   returns
        ▼
 LoadedSession (laps frame validated to LAPS_SCHEMA + SessionMetadata)
        │
        ▼
 features.build_lap_features(LoadedSession)        → FeatureFrame (FEATURES_SCHEMA)
        │
        ├──────────────► analytics.*  (DriverPace, TireDegradation, StintSummary…)
        │                       │
        │                       ▼
        └──────────────► models.*  (LapTimePredictor, TireDegPredictor)
                                │
                                ▼
                         strategy.*  (PitWindow, UndercutAnalysis, RaceSim)
                                │
                                ▼
                     visualization.* → app (Streamlit renders typed results)
```

Each arrow carries a **named, validated contract**, not a loosely-shaped
DataFrame. The contracts are specified in `INTERFACES.md`.

---

## 6. Cross-cutting concerns

- **Configuration** (`config/settings.py`): a frozen `Settings` dataclass built
  from environment variables with sane defaults. It resolves the cache/raw/
  processed paths to **absolute** paths anchored at the project root, fixing the
  current `../data/cache` fragility (ADR-0004).
- **Logging** (`config/logging.py`): structured logging configured once at the
  composition root. Libraries log; they never `print`. The current script's
  `print(...)` debugging is replaced by returned values + logging.
- **Errors** (`domain/errors.py`): a small exception hierarchy
  (`F1StrategyError` → `SessionLoadError`, `SchemaValidationError`, …) so callers
  can distinguish "network failed" from "data shape is wrong".

---

## 7. Phasing (maps to the project's 7 phases)

| Phase | Deliverable | Primary agent | Depends on approved |
|-------|-------------|---------------|---------------------|
| 1 | Ingestion platform (`config`, `domain`, `telemetry`) | Architect + Agent 1 | this doc |
| 2 | Feature engineering (`features`) | Agent 2 | Phase 1 contracts |
| 3 | Analytics (`analytics`) | Agent 2 | Phase 2 |
| 4 | ML platform (`models`) | Agent 3 | Phase 2 |
| 5 | Strategy engine (`strategy`) | Agent 4 | Phases 3 & 4 |
| 6 | Dashboard (`visualization`, `app`) | Agent 5 | Phase 5 |
| 7 | Testing & hardening (`tests`, CI) | Agent 6 | continuous, finalized last |

Within each phase we generate **one module at a time**, with a written rationale
(why it exists, design decisions, tradeoffs, scalability) per the execution rules.

---

## 8. Open decisions requiring your approval

These are listed in `CURRENT_STATE_REVIEW.md §Decisions`. The most consequential:

1. **Adopt `src/` layout + `pyproject.toml`** (recommended) vs. keep flat packages.
2. **Domain core as typed objects + validated DataFrames** (recommended hybrid)
   vs. pass raw DataFrames everywhere.
3. **Add `pandera` for schema validation** (recommended) vs. hand-rolled validators
   to stay strictly within the listed stack.

Nothing downstream is implemented until these three are settled.
