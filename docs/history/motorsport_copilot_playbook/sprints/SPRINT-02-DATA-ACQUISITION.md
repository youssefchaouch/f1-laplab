# Sprint 02 — Historical Data Acquisition and Cache

## Goal
Acquire a small, fixed sample of historical F1 session/lap data and cache it locally.

## Scope
- Use the project's existing telemetry/loading abstractions.
- Use FastF1 only if it fits the existing design and dependencies.
- Start with one known historical session, then support a small configurable list.
- Separate source-specific extraction from canonicalization.
- Do not engineer model features or train a model yet.

## Copilot prompt
Implement only Sprint 02. Inspect the current telemetry module and use its existing abstractions. Before coding, identify the smallest change set and any dependency addition. Build an acquisition path for a small configurable set of historical sessions, with explicit caching and clear errors for unavailable sessions. Keep downloaded data outside source-controlled code where the current configuration permits. Unit tests must use fixtures/mocks and must not access the network. Add an explicitly marked integration/manual command for a real download if appropriate. Do not create a database or API. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- One documented command can retrieve/cache the selected sample.
- Re-running does not needlessly fetch the same data again when cache behavior allows it.
- Source-specific fields are mapped explicitly.
- Network-independent tests cover transformation/error handling.
- Data source and session identifiers are recorded.
