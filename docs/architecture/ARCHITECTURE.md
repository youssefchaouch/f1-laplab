# F1 LapLab Architecture

F1 LapLab is a data-ingestion, validation, and feature-engineering library with
a baseline modelling layer. The pipeline produces a structured
`LapFeatureDataset`, on which `modeling` fits and evaluates baseline lap-time
predictors. It has no inference service, race replay, or calibrated strategy
simulator. The separate `strategy` package provides an assumption-driven
one-stop baseline.

## Data flow

```text
SessionRef
  -> SessionLoader / FastF1SessionLoader
  -> provider laps
  -> fastf1_laps_to_frame
  -> validate_laps (LAPS_SCHEMA + canonical validity)
  -> LoadedSession
      -> lap_records_from_session -> tuple[LapRecord, ...]
      -> build_lap_features -> LapFeatureDataset
          -> modeling.evaluate_leave_one_weekend_out -> EvaluationReport
          -> visualization.*_figure -> matplotlib Figure
```

The synthetic demonstration exercises the in-memory portion of this flow
without calling FastF1 or accessing the cache.

## Package responsibilities

| Package | Responsibility |
|---|---|
| `domain` | `SessionRef`, `SessionMetadata`, `LoadedSession`, `LapRecord`, enums, protocols, errors, and `LAPS_SCHEMA`. |
| `config` | Injected settings, absolute project data/cache paths, and explicit logging setup. |
| `telemetry` | FastF1 session loading, provider-to-canonical conversion, and lap validation. This is the only package that imports FastF1. |
| `features` | Deterministic prior-only feature construction for one `LoadedSession` at a time. |
| `modeling` | Naive and ridge baseline predictors of the upcoming lap time, and leave-one-weekend-out evaluation. Consumes `LapFeatureDataset`; never imports FastF1. |
| `visualization` | Static matplotlib figures built from validated domain objects. Loads no data and writes no files; returns figures for the caller to save. |
| `strategy` | Deterministic one-stop strategy baseline: enumerates and ranks feasible one-stop plans from explicit lap-pace, linear-degradation, pit-loss, stint, and pit-window assumptions. Depends only on `domain`; does not consume pipeline output and is not a calibrated race simulator. |

Tests mirror the package boundaries. Conversion, validation, feature
construction, and the synthetic demonstration can be exercised offline.

## Feature contract

`build_lap_features(LoadedSession) -> LapFeatureDataset` creates one target row
for every canonically valid timed lap. Its features are
`previous_lap_time_s`, `prior_3lap_mean_time_s`, and
`prior_3lap_valid_count`; the separate label is `target_lap_time_s`.

The prediction cutoff is immediately before the target lap begins. The builder
uses only eligible laps in exact slots `n-3` through `n-1`, for the same driver
and session. Missing slots remain missing; history never crosses sessions.
Eligible duplicate `(driver, lap_number)` identities raise
`SchemaValidationError`.

Eligibility is the canonical validity rule, so prior-lap inclusion depends on
the post-hoc `Deleted` and `IsAccurate` flags. See "Scope of the leakage
guarantee" in the root README for what the guarantee does and does not cover.

## External data and side effects

`FastF1SessionLoader` is an explicit I/O boundary. Initializing it ensures the
configured directories exist and enables FastF1's cache; loading a session may
make external requests and update that cache. Importing the package, running the
synthetic demo, and running tests marked `not network` do not require those
operations.
