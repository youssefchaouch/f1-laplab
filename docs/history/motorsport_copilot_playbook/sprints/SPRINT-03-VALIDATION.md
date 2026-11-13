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

## Implemented validation policy
- Schema-invalid frames are rejected with `SchemaValidationError`. Missing
  Driver, LapNumber, IsAccurate, or Deleted values are not fabricated; the
  existing `UNKNOWN` sentinels remain in force for Team and Compound. Present
  lap times must be positive; a missing lap time remains nullable and makes
  that lap canonically invalid.
- `IsValid` must match the shared rule: accurate, not deleted, and timed. The
  converter derives this flag; inconsistent canonical frames are rejected.
- Inaccurate, deleted, and untimed laps are retained in `LoadedSession.laps`
  for traceability, then excluded from analysis-ready output with row-level
  reasons. Every row in a duplicate `(Driver, LapNumber)` group is excluded;
  the validator does not select a winner arbitrarily.
- Missing optional stint, tyre-life, pit-marker, and track-status values remain
  missing. Pit-in/out flags and non-clear FastF1 track-status codes are reported
  as warnings and do not, by themselves, change lap validity.
- `validate_laps_with_report` returns the canonical cleaned frame, retained and
  excluded counts, stable reason counts, and row-level issues in source order.
  Reason counts are non-exclusive because one row can have multiple reasons.
