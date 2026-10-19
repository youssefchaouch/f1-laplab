# Sprint 01 — Canonical Lap Data Contract

## Goal
Define a small, explicit canonical representation of a lap record, using existing domain models where possible.

## Scope
- Inspect and reuse existing domain schemas.
- Identify the minimum fields needed for a lap-time prediction MVP.
- Define units, types, missing-value rules, and identifiers.
- Add focused validation/tests for valid and invalid examples.
- Do not ingest new data or train models in this sprint.

## Copilot prompt
Implement only Sprint 01. First report which existing models/schemas you will reuse and which files need changes. Propose the canonical lap record fields and explain each field's type, units, optionality, and provenance. Keep the schema minimal and compatible with the current architecture. Do not add speculative fields. Ask me to approve the proposed contract before implementation if it changes existing public interfaces.

Add tests for valid records, missing required fields, invalid lap times, and type/unit assumptions where relevant. Run tests and report exact results. Update `PROJECT_STATUS.md`; stop after completion.

## Acceptance criteria
- One documented canonical lap-record contract exists.
- Existing domain abstractions are reused where reasonable.
- Validation behavior is covered by deterministic tests.
- No network access, ML training, API, or UI added.
