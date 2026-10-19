"""Application settings.

WHY THIS FILE EXISTS
    One source of truth for configuration, injected into the layers that need it
    (dependency injection) rather than read from module-level globals. The
    telemetry loader takes ``Settings`` and enables the FastF1 cache from it in
    its constructor — never at import time. See ADR-0004.

DESIGN
    ``Settings`` is a frozen dataclass built by ``Settings.load()``, which reads
    optional ``F1STRATEGY_*`` environment variables and otherwise falls back to
    project-anchored defaults. Frozen => settings can't drift mid-run.

SCALABILITY
    Today this is a handful of fields. When the platform grows (API keys, a DB
    URL, feature flags), they slot in here with an env override and a default,
    and every consumer already receives the object by injection — no scattered
    ``os.getenv`` calls to hunt down later.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from f1strategy.config.paths import ProjectPaths, find_project_root


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime configuration for the platform."""

    paths: ProjectPaths
    log_level: str = "INFO"
    # Whether schema validation runs at layer boundaries. On by default; can be
    # disabled via env for hot paths once we have benchmarks (ADR-0003).
    validate_schemas: bool = True
    # Default for loading car telemetry channels (heavy) alongside lap timing.
    default_with_telemetry: bool = False

    @classmethod
    def load(cls, *, root: Path | None = None) -> Settings:
        """Build settings from the environment, anchored at the project root.

        Env overrides:
            F1STRATEGY_ROOT             — project root (else auto-discovered)
            F1STRATEGY_CACHE_DIR        — override only the FastF1 cache dir
            F1STRATEGY_LOG_LEVEL        — e.g. DEBUG, INFO, WARNING
            F1STRATEGY_VALIDATE_SCHEMAS — "0"/"false" to disable validation
        """
        resolved_root = root or _root_from_env() or find_project_root()
        paths = ProjectPaths.from_root(resolved_root)

        cache_override = os.getenv("F1STRATEGY_CACHE_DIR")
        if cache_override:
            paths = field_replace_cache(paths, Path(cache_override).resolve())

        return cls(
            paths=paths,
            log_level=os.getenv("F1STRATEGY_LOG_LEVEL", "INFO").upper(),
            validate_schemas=_env_flag("F1STRATEGY_VALIDATE_SCHEMAS", default=True),
        )


def _root_from_env() -> Path | None:
    value = os.getenv("F1STRATEGY_ROOT")
    return Path(value).resolve() if value else None


def _env_flag(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def field_replace_cache(paths: ProjectPaths, cache: Path) -> ProjectPaths:
    """Return a copy of ``paths`` with a different cache dir (frozen-safe)."""
    return ProjectPaths(
        root=paths.root,
        data=paths.data,
        raw=paths.raw,
        processed=paths.processed,
        cache=cache,
    )
