# Sprint 10 — Retraining Workflow and Promotion Gate

## Goal
Create a repeatable workflow that trains a candidate and promotes it only if it passes the evaluation gate.

## Scope
- One explicit command/workflow to rerun validation, features, training, and evaluation.
- Save candidate artifacts and metadata.
- Apply Sprint 07 promotion logic.
- Keep the previous selected model if a candidate fails.
- Scheduling can be added later; begin with a reproducible local command.

## Copilot prompt
Implement only Sprint 10. Build a single reproducible local workflow that runs the existing stages in order and fails clearly if a stage fails. Candidate models must pass the existing evaluation gate before selection changes. Never overwrite the only good model artifact. Do not add an orchestrator or scheduler package just to automate a local script; justify any such dependency first. Add an integration test using a small fixture where practical. Document the command and update `PROJECT_STATUS.md`. Do not begin strategy simulation.

## Acceptance criteria
- One command executes the intended retraining sequence.
- Candidate metadata and artifact are preserved.
- Failed evaluation leaves the selected model unchanged.
- Failure and promotion decisions are observable.
