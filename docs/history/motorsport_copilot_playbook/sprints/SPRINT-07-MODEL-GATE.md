# Sprint 07 — Candidate Evaluation and Model Selection

## Goal
Create a transparent rule for deciding whether a candidate model may replace the current selected model.

## Scope
- Compare candidate against the baseline/current model on a comparable evaluation set.
- Define thresholds based on measured baseline results, not arbitrary claims.
- Record accepted/rejected decisions.
- Preserve previous artifacts.
- No automatic deployment yet.

## Copilot prompt
Implement only Sprint 07. Propose a minimal model-candidate metadata format and explicit promotion criteria. Do not invent a threshold before inspecting actual evaluation results; make the threshold configurable and explain how it will be chosen. Compare models on comparable data and record the decision and evidence. Preserve existing artifacts and selection state. Add tests for candidate accepted, candidate rejected, missing metrics, and incompatible feature schema. Do not build a model server. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- Promotion decision is deterministic and auditable.
- Candidate and current model are compared fairly.
- Rejected candidates do not replace the selected model.
- Previous model artifacts remain available.
