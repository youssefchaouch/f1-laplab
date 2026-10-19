# ADR-0003 — DataFrame schema contracts at layer boundaries

- Status: **Proposed**
- Date: 2026-06-17
- Deciders: Chief Architect, Data Scientist, ML Engineer

## Context

Pandas DataFrames are the natural currency for tabular F1 data, but a bare
DataFrame is an untyped bag of columns. When `telemetry` hands a frame to
`features`, nothing documents or enforces which columns exist, their dtypes, or
nullability. Bugs then surface deep in analytics as cryptic `KeyError`s, far from
the real cause (the producer changed shape). The current code already assumes
columns like `IsAccurate` and `LapTime` exist with no guarantee.

## Decision

Every DataFrame that **crosses a layer boundary** is validated against a declared
schema (`LAPS_SCHEMA`, `FEATURES_SCHEMA`, …). Validation runs at the *producer's*
exit. A violation raises `SchemaValidationError` with the offending columns —
failing at the boundary, not three layers downstream.

Preferred tool: **`pandera`** — declarative schemas, dtype + nullability +
value-range checks in ~20 lines, with a typed-DataFrame story that pairs well with
mypy. If we choose to stay strictly within the originally listed stack, the
fallback is a small hand-rolled `validate(df, schema)` helper; the *contract* is
identical either way, only the implementation differs.

## Options considered

1. **No validation** (status quo). Cheapest; failures are late and cryptic. Rejected.
2. **Hand-rolled validators.** No new dependency; more boilerplate, easy to let
   schemas drift from reality. Acceptable fallback.
3. **`pandera`** (chosen). One dependency; declarative, self-documenting,
   industry-standard. The schema doubles as boundary documentation.

## Consequences

- (+) Shape bugs fail fast, at the boundary, with a clear message.
- (+) Schemas are executable documentation of every contract in INTERFACES §4.
- (+) Tests assert on schemas, not on hand-picked column names.
- (−) One dependency (`pandera`) if we take the recommended path.
- (−) Validation has a small runtime cost; acceptable, and skippable in hot loops
  via a settings flag if ever needed.
