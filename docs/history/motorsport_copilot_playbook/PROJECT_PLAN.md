# Project Plan — Motorsport Strategy + MLOps

> **Historical plan:** this sprint roadmap predates the F1 LapLab project
> direction and is retained for development history. It is not a current
> commitment; see the repository-root README for active scope.

## Product goal

Build a portfolio-grade Python project that uses historical Formula 1 data to produce defensible lap-time predictions and later support strategy analysis. Demonstrate engineering discipline through data validation, reproducible training, model evaluation, inference, monitoring, and controlled retraining.

This is initially a historical/offline analysis system, not a live pit-wall system. Any real-time claims require a separate design and suitable live data access.

## Product boundaries

### In scope, in sequence
1. Verify and stabilize the current repository.
2. Define and test the data contract for a small historical dataset.
3. Acquire/cache raw session data reproducibly.
4. Validate and normalize records.
5. Build leakage-safe features.
6. Train a simple baseline model.
7. Record experiments and dataset/model lineage.
8. Compare candidate models against a baseline and promotion threshold.
9. Provide a stable inference interface.
10. Monitor predictions when actual lap times become available.
11. Automate retraining and candidate evaluation.
12. Add a small strategy simulation using validated predictions.
13. Document architecture, limitations, and reproducible setup.

### Explicitly out of scope until approved
- Live race control or real-time pit-stop recommendations
- Microservices, gRPC, Kubernetes, or cloud deployment
- A web UI/dashboard
- A database server
- A feature store
- Complex reinforcement learning or deep learning
- Multiple models before a baseline is evaluated
- Automatic model promotion without evaluation gates
- Broad rewrites of the existing architecture

## Current reported state (verify it; do not assume)
- Domain layer: core data models, schemas, enums, protocols
- Telemetry module: loading, conversion, validation from telemetry sources
- Configuration: settings, logging, path management
- Tests: telemetry, domain schemas, architecture boundaries
- Project structure: separation of concerns

Copilot must inspect the actual repository and tests before changing anything.

## Target high-level flow

Historical source (e.g. FastF1)
→ cached raw session data
→ validated canonical lap records
→ leakage-safe features
→ training/evaluation
→ versioned model artifact + metadata
→ inference
→ prediction/actual comparison
→ monitoring
→ candidate retraining and gated promotion
→ strategy simulation (later)

Keep data acquisition separate from transformations and ML code. Unit tests should run without downloading data.

## Suggested sprint sequence

- Sprint 00: Repository audit and baseline verification
- Sprint 01: Data contracts and canonical lap record
- Sprint 02: Historical data acquisition and local cache
- Sprint 03: Data validation and normalization
- Sprint 04: Leakage-safe feature engineering
- Sprint 05: Baseline lap-time model and evaluation
- Sprint 06: Reproducible experiments and model metadata
- Sprint 07: Candidate evaluation and model version selection
- Sprint 08: Inference interface and prediction records
- Sprint 09: Monitoring and delayed ground-truth evaluation
- Sprint 10: Scheduled/manual retraining workflow and promotion gate
- Sprint 11: Minimal strategy simulation using the prediction pipeline
- Sprint 12: Documentation, reproducibility, and portfolio demonstration

Sprint order can change only when a concrete dependency requires it. Each sprint must remain small and independently testable.

## Definition of done

The project is complete for the initial portfolio scope when:
- A new developer can set it up from documented instructions.
- A small, documented set of historical sessions can be processed reproducibly.
- Data quality issues are observable rather than silently hidden.
- Training/evaluation is repeatable and leakage-aware.
- A baseline can be compared with a candidate using a time-aware split.
- Model artifact, feature schema, configuration, dataset reference, and metrics are recorded.
- Inference uses the same feature contract as training.
- Predictions can be joined to actual outcomes for monitoring.
- Retraining produces a candidate and does not promote it unless explicit criteria pass.
- A small strategy simulation demonstrates how predictions may inform decisions, with limitations stated.
- Tests run without requiring network access, except for explicitly marked integration tests.

## Modeling cautions

- Use a time-aware split rather than a random row split when that better reflects intended generalization.
- Prevent target leakage from current/future lap information.
- Decide whether the goal is predicting a driver's next lap, estimating lap pace under conditions, or comparing strategy alternatives. These are different targets; document the selected one.
- Account for pit-in/out laps, safety-car periods, red flags, missing laps, and invalid timing data rather than treating all rows as equivalent.
- Establish a simple baseline before comparing more complex models.
- A lower MAE alone does not prove the model is useful for strategy decisions.
