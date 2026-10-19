# ADR-0002 — FastF1 confined to an anti-corruption boundary

- Status: **Proposed**
- Date: 2026-06-17
- Deciders: Chief Architect, Telemetry Engineer

## Context

FastF1 is a third-party library wrapping an external data source. It controls its
own object model, dtypes (timedeltas, categoricals), column names, and failure
modes — none of which we govern. The current `load_session()` returns a raw
`fastf1.Session`, so every downstream consumer is coupled to FastF1. Any upstream
change ripples through the entire codebase, and nothing can be tested without the
network.

## Decision

Confine `import fastf1` to the **`telemetry/` package only**. `telemetry` acts as
an *anti-corruption layer*: it converts FastF1 objects into our own domain types
(`LoadedSession` = validated `laps` frame conforming to `LAPS_SCHEMA` +
`SessionMetadata`). At the boundary we also normalize representations — e.g.
FastF1's `LapTime` timedelta becomes `LapTime_s: float` seconds — so no other
layer ever handles a FastF1 dtype.

Downstream layers depend on the `SessionLoader` **Protocol** (in `domain`), not on
the concrete loader, so tests inject a fake.

## Options considered

1. **Return raw `fastf1.Session` everywhere** (status quo). Zero conversion code,
   but maximal coupling and zero testability. Rejected.
2. **Thin pass-through wrapper** that returns FastF1's `laps` frame unchanged.
   Rejected: still leaks FastF1 dtypes/column names downstream.
3. **Full anti-corruption boundary** (chosen): convert to owned types + validated
   schema at the single seam.

## Consequences

- (+) A FastF1 change has a blast radius of one package.
- (+) `features`/`analytics`/`models`/`strategy` test offline against fixtures.
- (+) Downstream code reads our vocabulary, not FastF1's.
- (−) Conversion + validation code to write and maintain in `telemetry`.
- (−) A genuinely new FastF1 field must be threaded through `LAPS_SCHEMA` and
  `LoadedSession` deliberately — friction we accept as the price of the boundary.
- Enforced by `tests/architecture/test_import_boundaries.py` (Agent 6).
