# Sprint 04 — Leakage-Safe Pre-Lap Feature Engineering

## Status and scope

Sprint 04 prepares a deterministic dataset for predicting the observed lap time
of an upcoming lap. The prediction cutoff is immediately before that target lap
begins. This sprint does not train or evaluate a model, replay races, simulate
strategy, or predict finishing positions or top-10 probabilities.

The reusable input is a validated `LoadedSession`; feature construction must not
acquire data, use network access, or depend on a specific circuit, season, or
sample session.

## Target population and label

The target population is every row in `LoadedSession.laps` whose canonical
`IsValid` value is true. The canonical contract requires `IsAccurate=True`,
`Deleted=False`, and a present, positive `LapTime_s`, with all rows conforming
to `LAPS_SCHEMA`. Pit-in/out markers and non-clear track status are warnings,
not validity exclusions; such otherwise valid timed laps remain targets.

The sole label is `target_lap_time_s`, sourced only from that target row's
`LapTime_s` in seconds. Invalid and untimed rows are not labels. If no eligible
target remains, feature construction raises `InsufficientDataError`.

The row identity is `(session_year, grand_prix, session, driver, lap_number)`.
Two or more canonically eligible rows with the same `(session, driver,
lap_number)` identity are an error: raise `SchemaValidationError` and do not
arbitrarily choose or discard an eligible duplicate. The general validation
report's duplicate-filtered `cleaned_laps` must not be used as the target source,
because it removes every row in a duplicate identity group.

## Approved v1 feature contract

The model matrix contains exactly these features, in this order:

| Feature | Type and unit | Source / derivation | Available at cutoff | Missing-value behavior | Leakage risk and mitigation |
|---|---|---|---|---|---|
| `previous_lap_time_s` | Nullable floating-point, seconds | Same driver's eligible canonical `LapTime_s` at exact lap number `n-1` in this session | After lap `n-1` completes and before lap `n` begins | Null if exact slot `n-1` is absent or ineligible; never substitute an older lap | Current target time could leak if read from target row; lookup is restricted to the exact prior lap-number key |
| `prior_3lap_mean_time_s` | Nullable floating-point, seconds | Arithmetic mean of eligible lap times in exact slots `n-3`, `n-2`, and `n-1` | Only after each contributing lap completes and before target lap `n` begins | Mean available eligible observations in those slots; partial window allowed; null if none | Target/future or out-of-window laps could leak; fixed prior-only lap-number slots prevent this |
| `prior_3lap_valid_count` | Integer, count 0–3 | Number of eligible observations used by the preceding mean | Same as the mean | Zero when no eligible history exists; mean is then null | Count could reveal target validity if computed from target rows; it counts only prior eligible slots |

An absent, invalid, untimed, or otherwise ineligible slot contributes no value.
The mean does not fill gaps or extend the window. In particular, an ineligible
`n-1` makes `previous_lap_time_s` null even if an older lap is available, while
that older lap may contribute to the three-slot mean if it is within `n-3` to
`n-1`.

Identifiers and source metadata are carried separately from features and
labels. Session, driver, and lap identity are trace keys, not model predictors
in v1. The target lap's time, compound, tyre age/stint, pit markers, track
status, accuracy/deletion flags, final results, future laps, and
future-derived statistics are not feature inputs. Target-row tyre state is not
established as reliably known before that lap begins and is therefore excluded.

## Output and deterministic behavior

The result separates:

- source/session metadata, prediction cutoff, target name/unit, and the
  `n-3` through `n-1` history definition;
- identifiers `(session_year, grand_prix, session, driver, lap_number)`;
- `X`, containing only the three ordered features above;
- `y`, containing only `target_lap_time_s`;
- an exclusion trace for canonically invalid source rows.

Identifier, feature, and label rows share the same reset index and are aligned
one-to-one by the unique composite key. Sort deterministically by session
identity, driver, and lap number. A single `LoadedSession` supplies one session
identity; no cross-session feature history is allowed.

Feature generation first validates the canonical frame, selects eligible
targets without using the duplicate-dropping report output, rejects duplicate
eligible identities, builds exact prior-slot lookups, then creates sorted
identifiers, features, labels, and invalid-row trace. Empty input and input with
no eligible target rows raise `InsufficientDataError`; malformed canonical
input raises `SchemaValidationError`. No imputation or forward/backfilling is
performed.

## Leakage threat model and acceptance tests

Tests must establish that:

1. only canonical valid timed rows become labels; invalid, deleted, and untimed
   rows are excluded, while valid pit/status-warning rows remain;
2. duplicate eligible composite identities fail clearly, and the builder does
   not silently inherit the general report's duplicate-row removal;
3. labels and identifiers are absent from `X`, and the target time is label-only;
4. changing a target time changes its label but not its own features;
5. changing/appending future laps, including future times and event fields, does
   not change features for earlier cutoffs;
6. exact predecessor, fixed three-slot mean/count, partial/empty windows,
   invalid/missing slots, gaps, and the `n-3` lower boundary are respected;
7. repeated construction and input-row permutation produce identical ordered
   keys, features, labels, and metadata;
8. output columns, order, types, nullability, units, alignment, and unique keys
   match this contract;
9. empty and malformed inputs fail with explicit domain errors.

For future-row perturbation, build a dataset from a canonicalized fixture, then
change or append only source rows with lap numbers greater than a selected
target. Rebuild and compare the selected earlier target's features by composite
key. Repeat after perturbing target time alone and verify only its label changes.
All tests remain offline and use the repository's conversion and validation
path.

## Future prediction milestones and limitations

This dataset predicts observed lap time, not race outcomes. Labels are observed
times for all canonically valid laps; this population can include laps affected
by pits, yellow flags, safety cars, traffic, weather, damage, or other events.
The v1 feature set does not explain or model those conditions, so the labels are
not equivalent to clean-air pace or causal performance.

Before-weekend, pre-race, and pre-lap are distinct prediction cutoffs. Sprint
04 uses only pre-lap information. Future race-outcome prediction will require
separately defined outcome labels, cutoff-specific source data, provenance and
availability rules, and evaluation held out by race weekend or chronology—not
a random split of individual laps. Historical race replay is a separate
follow-up milestone. No training, race simulation, finishing-position
prediction, or top-10 probability prediction is delivered here.
