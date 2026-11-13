# Sprint 05 — Baseline Model and Evaluation

## Goal
Train and evaluate one simple model using the validated feature pipeline.

## Scope
- Implement a naive baseline and one simple ML model.
- Use a split that reflects the intended generalization (prefer time/session-aware evaluation where appropriate).
- Report MAE and RMSE, plus errors by useful slices where sample size permits.
- Save model artifacts locally using the existing project conventions.
- Do not deploy or add a dashboard.

## Copilot prompt
Implement only Sprint 05. First confirm the target and split strategy. Create a simple baseline (for example, a training-set median or a defensible historical pace baseline) and one simple model. Avoid adding multiple model families. Prevent leakage by fitting preprocessing only on training data and by using an appropriate time/session-aware split. Report MAE and RMSE and compare against the baseline. Make random seeds/configuration explicit where relevant. Add tests for training/evaluation interfaces and run a small reproducible experiment. Do not claim generalization beyond the evaluated data. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- Baseline and one ML model can be trained reproducibly.
- Evaluation split and limitations are documented.
- MAE/RMSE are reported against the baseline.
- Artifact and minimal metadata are saved.
- Tests do not need network access.
