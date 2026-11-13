# Sprint 11 — Minimal Strategy Simulation

## Goal
Use the validated prediction pipeline in a small, explicitly scoped post-race strategy simulator.

## Scope
Start with one question, such as comparing a small set of candidate pit-stop laps under documented assumptions. Use a simple simulation, not reinforcement learning. Clearly state assumptions and uncertainty.

## Copilot prompt
Implement only Sprint 11. First propose one narrow strategy question and the assumptions needed to simulate it. Use the existing prediction interface; do not retrain or change the model in this sprint. Make tire degradation, pit-loss time, and other strategy assumptions configurable and clearly label any values that are illustrative rather than calibrated from data. Compare a small set of candidate strategies and report results with caveats. Do not call the result a real-world optimal strategy. Add deterministic tests for simulation mechanics. Update `PROJECT_STATUS.md` and stop.

## Acceptance criteria
- One documented scenario can be simulated reproducibly.
- Assumptions and limitations are visible.
- The simulator uses the existing prediction interface.
- Tests cover key strategy calculations.
