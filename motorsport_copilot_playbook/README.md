# Motorsport Strategy + MLOps — Copilot Playbook

This playbook is designed for an existing Python project developed locally in PyCharm. It assumes some code already exists for the domain layer, telemetry, configuration, and tests.

## How to use it

1. Copy these Markdown files into the project root.
2. Open `COPILOT_RULES.md` and `PROJECT_PLAN.md` in Copilot Chat.
3. Start with `sprints/SPRINT-00-REPOSITORY-AUDIT.md`.
4. Work on exactly one sprint at a time.
5. Do not begin a sprint until the previous sprint's acceptance criteria pass.
6. After each sprint, update `PROJECT_STATUS.md` with Copilot and review the diff yourself.

## Core rule

Copilot must inspect and preserve the existing code before proposing changes. It must not rewrite the project just because a different structure would be convenient.

## Project direction

Build a reproducible motorsport data and strategy application, with a complete, testable ML lifecycle:
data acquisition → validation → features → baseline model → experiment tracking → evaluation/versioning → inference → monitoring → retraining.

A strategy simulator and decision-support layer can be added after the lap-time prediction pipeline is credible. Do not claim real-time race strategy or production readiness until those capabilities actually exist.
