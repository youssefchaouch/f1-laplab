# Sprint 00 — Repository Audit and Baseline Verification

## Goal
Understand the actual codebase and establish a verified baseline without changing implementation.

## Copilot prompt
Act only on Sprint 00. Inspect the repository and relevant configuration/tests. Do not edit code or restructure files.

Produce:
1. A concise directory map of relevant source, tests, configuration, and data/cache directories.
2. A map of the current data flow from source/loading through domain objects and validation.
3. A list of existing public interfaces and their callers.
4. The project's Python version and dependency-management approach, based on files actually present.
5. The exact test command and result. If tests cannot run, explain the blocker and do not claim success.
6. A gap analysis against `PROJECT_PLAN.md`, marking each item as present, partial, absent, or unknown, with file evidence.
7. A proposed list of no more than 3 risks or architectural concerns that matter immediately.
8. A recommended narrow scope for Sprint 01.

Do not implement any gap during this sprint. Do not invent filenames or capabilities. Wait for approval after the report.

## Acceptance criteria
- No implementation files changed.
- Current structure and test command documented.
- Test baseline attempted and result reported honestly.
- Existing components are distinguished from Copilot's assumptions.
- `PROJECT_STATUS.md` is updated with verified facts.
