# Copilot Working Rules

Treat these rules as mandatory for every task in this repository.

## Scope control
- Implement only the current sprint and only its stated acceptance criteria.
- Do not implement future sprints, optional enhancements, dashboards, APIs, databases, or abstractions unless the current sprint explicitly requires them.
- If you discover a dependency on future work, explain it and stop for a decision instead of implementing it pre-emptively.
- Do not create speculative placeholder modules or empty classes for future functionality.
- Do not add features merely because they are common in similar projects.

## Inspect before editing
- Read the relevant existing files and tests before proposing code.
- Reuse existing conventions, names, configuration, and architecture when reasonable.
- Do not replace or reorganize existing files without explaining why and obtaining approval.
- Do not assume Copilot's previous summaries are accurate; verify against the repository.

## Small, reviewable changes
- At the start, state: (1) what you inspected, (2) the narrow task, (3) files expected to change, and (4) the tests to run.
- Make the smallest coherent implementation that satisfies the acceptance criteria.
- Avoid unrelated refactors, formatting churn, dependency upgrades, and broad renames.
- Do not modify more files than necessary.
- Prefer a few focused functions over generic frameworks.

## Engineering quality
- Add or update tests for behavior introduced or changed.
- Use deterministic tests; do not require network access for unit tests.
- Keep network/API access at clear boundaries.
- Handle missing, malformed, duplicate, and incomplete data explicitly.
- Never silently swallow exceptions or silently substitute fabricated data.
- Keep secrets and credentials out of source control.
- Do not use race-result or future-lap information as a feature when predicting a lap at an earlier point in time.
- Make units, timestamps, session identifiers, driver identifiers, and data provenance explicit where relevant.
- Avoid claiming that data drift is model degradation; monitor them separately.
- Do not add an MLOps tool unless the current sprint needs it and the choice is justified.

## Dependencies
- Do not add a package without explaining why it is needed and what simpler alternative was considered.
- Pin or constrain dependencies using the project's existing dependency-management approach.
- Do not change Python versions or dependency managers without approval.

## Validation and reporting
- Run the narrowest relevant tests first, then the full test suite if feasible.
- Report the exact commands run and their results. Never claim tests passed if they were not run.
- List changed files and explain each change in one sentence.
- List known limitations and follow-up items.
- If requirements are ambiguous, ask one focused question instead of guessing.

## Completion gate
At the end of every sprint, provide:
1. Implemented scope
2. Changed files
3. Tests/commands run and results
4. Acceptance criteria: pass/fail with evidence
5. Known limitations
6. Recommended next sprint (do not start it)
7. Updated `PROJECT_STATUS.md`

Stop after this report and wait for my explicit instruction to continue.
