# Sprint 06 — Experiment Metadata and Reproducibility

## Goal
Record enough metadata to reproduce and compare a training run.

## Scope
Capture configuration, dataset/session references, feature version, model parameters, metrics, software version where practical, timestamp, and artifact location. Use a simple structured local format first unless there is a clear reason to introduce MLflow now.

## Copilot prompt
Implement only Sprint 06. Inspect the current training output and determine the minimum metadata needed for reproducibility. Propose a small schema and storage format before coding. Prefer a simple local structured record if it meets the need; do not add MLflow just for résumé keywords. If recommending MLflow, explain the concrete capability missing from the simpler approach and confirm dependency/environment compatibility first. Add tests that metadata is complete and linked to the correct artifact/run. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- Each run has a unique identifier and structured metadata.
- Metadata identifies data/session references, features, parameters, metrics, and artifact.
- Two runs can be compared without guessing which configuration produced them.
