# ADR-0004 — Centralized configuration & absolute path resolution

- Status: **Proposed**
- Date: 2026-06-17
- Deciders: Chief Architect, Telemetry Engineer

## Context

The current loader calls `fastf1.Cache.enable_cache("../data/cache")` **at import
time** with a **relative** path. Two concrete bugs follow:

1. The path resolves against the current working directory, not the project. Run
   from the repo root and FastF1 silently writes the cache to `../data/cache` —
   *outside* the project. Different CWDs produce different, duplicated caches.
2. Importing the module has a filesystem side effect, so the module cannot be
   imported for its types alone, and cannot be tested without provisioning a cache
   directory.

There is also already a discrepancy: the prompt's loader uses `"data/cache"`, the
on-disk one uses `"../data/cache"`. Two sources of truth for one setting.

## Decision

Introduce a single `config/settings.py` exposing a frozen `Settings` dataclass,
built from environment variables with defaults, that resolves **absolute** paths
anchored at a discovered project root (walk up for a `pyproject.toml` marker).

- `Settings.cache_dir`, `raw_dir`, `processed_dir` are absolute `Path`s.
- FastF1 cache is enabled **inside `FastF1SessionLoader.__init__`**, taking the
  path from injected `Settings` — never at import time.
- Logging is configured once, at the composition root, via `config/logging.py`.

## Options considered

1. **Status quo** (relative path, import-time enable). Rejected: the two bugs above.
2. **Hardcode an absolute path** in the loader. Rejected: not portable across
   machines/CI; still an import-time side effect.
3. **Injected `Settings` with project-root-anchored absolute paths** (chosen).

## Consequences

- (+) Cache lands in the same place regardless of CWD.
- (+) Modules import cleanly with no side effects; types are importable in tests.
- (+) One source of truth; overridable via env vars for CI / different machines.
- (−) Slightly more upfront code (a settings module + root discovery helper).
- (−) Callers must obtain `Settings` and pass it in — intentional dependency
  injection, wired once at the composition root.
