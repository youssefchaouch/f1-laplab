# Sprint 03 — Data Validation and Normalization

## Goal
Turn acquired records into a clean canonical dataset and make data issues visible.

## Scope
- Required columns and types
- Invalid/non-positive lap times
- Duplicate lap records
- Missing critical identifiers
- Explicit handling of pit-in/out laps and special laps when the source exposes those fields
- Validation summary/report

## Copilot prompt
Implement only Sprint 03. Reuse the canonical contract from Sprint 01 and acquisition output from Sprint 02. Do not silently drop rows. Define whether each issue causes rejection, exclusion with a reason, or a warning. Produce a validation summary with counts and reasons. Add deterministic tests using fixtures, including malformed and duplicate records. Do not add new validation frameworks unless justified. Do not implement feature engineering. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- Validation rules are documented and tested.
- Invalid/excluded records have an explainable reason.
- The cleaned output follows the canonical contract.
- The validation summary is reproducible.
