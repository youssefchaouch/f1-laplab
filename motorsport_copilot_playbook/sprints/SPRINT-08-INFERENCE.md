# Sprint 08 — Inference Interface

## Goal
Expose a small, stable Python interface for generating predictions with the selected model.

## Scope
- Validate inference features against the training contract.
- Load the selected artifact.
- Return prediction plus model/run identifier.
- Record prediction data needed for later evaluation.
- No FastAPI unless a concrete consumer requires HTTP.

## Copilot prompt
Implement only Sprint 08. First identify whether a Python function/module is sufficient for current consumers. Do not add FastAPI, Docker, or a service layer without a demonstrated requirement. Reuse the same feature contract used in training. Validate missing, extra, malformed, and out-of-range inputs where meaningful. Include the model/run identifier in results. Add tests for valid predictions, invalid inputs, and missing artifacts. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- One documented interface produces predictions from the selected artifact.
- Training and inference feature contracts are aligned.
- Predictions identify the model version/run.
- Error cases are explicit and tested.
