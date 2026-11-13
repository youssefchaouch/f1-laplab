# Sprint 09 — Prediction Monitoring

## Goal
Compare recorded predictions with actual lap times once ground truth is available, and report performance over time.

## Scope
- Store prediction records with timestamp, target identifiers, model version, prediction, and feature metadata needed for analysis.
- Join actual lap times when available.
- Calculate MAE/RMSE by suitable time/session windows.
- Monitor input distribution separately from prediction error.
- Do not claim drift implies degraded performance.

## Copilot prompt
Implement only Sprint 09. Inspect the inference output and canonical data keys. Design the smallest prediction log format that supports later joining to actual outcomes. Add evaluation when actual values become available; do not fabricate labels or use the target before it is available. Keep data-drift metrics separate from model-error metrics. Start with a local dataset/file approach consistent with the project; no dashboard, database server, or Evidently dependency unless justified. Add deterministic tests and update `PROJECT_STATUS.md`. Stop after the report.

## Acceptance criteria
- Predictions can be joined to actual outcomes using stable identifiers.
- Performance metrics are calculated only where ground truth exists.
- Monitoring reports sample counts and missing-ground-truth cases.
- Drift and model performance are represented separately.
