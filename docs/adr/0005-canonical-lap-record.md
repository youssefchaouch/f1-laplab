# ADR-0005 — Immutable canonical lap record

- Status: **Accepted**
- Date: 2026-10-19
- Deciders: Project owner

## Context

`LAPS_SCHEMA` defines the validated batch representation and `LoadedSession`
associates that batch with session metadata. A batch row is still an untyped,
mutable pandas object, and its columns do not carry the session identity needed
to identify a lap outside its parent frame.

## Decision

Keep `LAPS_SCHEMA` as the sole batch contract and add a frozen, slotted
`LapRecord` for consumers that need an immutable, typed value for one lap.
`LapRecord` carries the enclosing `SessionRef` and the schema's driver code,
making its session and driver traceable. Its lap number follows the schema's
one-based `LapNumber >= 1` rule.

Fields correspond to the existing schema: team, stint, tire compound, tire
life, lap time in seconds, accuracy, and deletion state. Stint and tire life
remain optional and are represented as `None` when absent. A missing lap time is
also represented as `None`. The schema's `UNKNOWN` sentinels remain in use for
unavailable team and compound values.

`is_valid` is a computed property using the shared rule: accurate, not deleted,
and lap time present. `IsValid` remains in the batch schema for filtering; the
record converter checks it agrees with the property. The accuracy and deletion
fields remain required because `LAPS_SCHEMA` declares them non-nullable.

Conversion from `LoadedSession` validates the batch contract, then returns an
immutable tuple of records. No second DataFrame schema is introduced. FastF1
continues to be isolated in the telemetry package.

## Trade-offs

- (+) Per-lap consumers receive an immutable, typed value with explicit session
  and driver identity rather than relying on a DataFrame row and external context.
- (+) Batch processing keeps the existing Pandera contract and does not duplicate
  a second DataFrame representation.
- (+) Missing optional integer and time values stay distinguishable from real
  zeroes or times.
- (−) The same domain information exists in both batch columns and a scalar
  model, so conversion and invariant tests must keep them aligned.
- (−) Record conversion validates the batch frame before materializing values;
  this adds validation work when callers convert an already-validated session.
