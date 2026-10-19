# ADR-0001 — Layered clean architecture with `src/` layout

- Status: **Proposed**
- Date: 2026-06-17
- Deciders: Chief Architect

## Context

The project must read like production software, not a notebook port. It spans
ingestion, feature engineering, analytics, ML, strategy, and a UI — six concerns
that will be touched by different specialists and that evolve at different rates.
Without enforced boundaries, these concerns bleed into each other and the codebase
becomes a single tangled module (the exact failure mode of the current
`scripts/load_telemetry.py`).

## Decision

Adopt a **layered (clean) architecture** with dependencies pointing inward to a
dependency-free `domain` core, packaged under a **`src/f1strategy/` layout** and
installed via `pyproject.toml`.

Layers: `domain`, `config` (leaves) → `telemetry` → `features` → `analytics` /
`models` → `strategy` → `visualization` → `app`. Each owns one responsibility and
may only import inward (see DEPENDENCY_GRAPH.md).

## Options considered

1. **Flat packages at repo root** (status quo). Simple, but imports are ambiguous
   (the test imports differ depending on CWD), and nothing prevents `visualization`
   from importing `fastf1`. Rejected: no enforced boundaries, weaker "ships
   software" signal.
2. **Single package, no layering** — one `f1` module with submodules but no
   import rules. Rejected: boundaries exist only in folder names, not enforced.
3. **`src/` layout + layered architecture** (chosen). Slightly more setup;
   requires `pip install -e .`. Buys unambiguous imports, enforceable boundaries,
   and an installable artifact.

## Consequences

- (+) Boundaries are mechanically enforceable (import-linter / a grep test).
- (+) The package is installable and importable identically everywhere.
- (+) New contributors orient via eight named layers.
- (−) One-time migration cost: move existing files under `src/f1strategy/` and
  add packaging. Tracked in CURRENT_STATE_REVIEW §E.
- (−) Contributors must `pip install -e .` once. Documented in README.
