# Sprint 04 — Leakage-Safe Feature Engineering

## Goal
Create a deterministic feature pipeline for the selected prediction target.

## Prerequisite decision
Before implementation, explicitly define the target. Recommended MVP target: predict the lap time for a lap using only information available before that lap begins. Confirm the exact prediction moment and target column before coding.

## Copilot prompt
Implement only Sprint 04. First state the prediction target, prediction time, target column, and what information is available at prediction time. Identify any candidate features that would leak future/current-lap information and exclude them. Propose a minimal feature list before coding. Use deterministic transformations and keep training/inference feature construction consistent. Add tests for schema, ordering, missing-value behavior, and leakage-sensitive cases. Do not train a model. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- Prediction target and prediction moment are documented.
- Feature names, types, units, and missing-value policy are documented.
- Feature generation is deterministic and tested.
- No target/future information leaks into input features.
