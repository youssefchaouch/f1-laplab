"""Project path resolution.

WHY THIS FILE EXISTS
    The original loader used the relative path ``../data/cache``, which resolves
    against the *current working directory*, not the project. Run from the repo
    root and FastF1 silently writes its cache *outside* the project; run from a
    notebook and it lands somewhere else again — two caches, two truths.

    This module discovers the project root once (by walking up to the
    ``pyproject.toml`` marker) and exposes every data path as an **absolute**
    ``Path`` anchored there, so the cache is deterministic regardless of CWD.
    See docs/adr/0004-configuration-and-paths.md.

DESIGN
    ``ProjectPaths`` is a frozen dataclass — paths are computed once and never
    mutated. ``ensure()`` is the only method with a side effect (mkdir), and it
    is called explicitly by the composition root, never on import.

TRADEOFFS
    Root discovery relies on a ``pyproject.toml`` marker. If the package is ever
    installed as a wheel into site-packages (no source tree), discovery would
    fail; for that case ``F1STRATEGY_ROOT`` can override it (handled in
    settings.py). For a portfolio/analytics project run from a checkout this is
    the simplest correct approach.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_ROOT_MARKER = "pyproject.toml"


def find_project_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` (default: this file) until ``pyproject.toml``.

    Raises:
        FileNotFoundError: if no marker is found up to the filesystem root.
    """
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / _ROOT_MARKER).is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not locate project root (no {_ROOT_MARKER!r} found above {here})."
    )


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """Absolute, deterministic locations for all on-disk artifacts."""

    root: Path
    data: Path
    raw: Path
    processed: Path
    cache: Path

    @classmethod
    def from_root(cls, root: Path) -> ProjectPaths:
        data = root / "data"
        return cls(
            root=root,
            data=data,
            raw=data / "raw",
            processed=data / "processed",
            cache=data / "cache",
        )

    def ensure(self) -> ProjectPaths:
        """Create the data directories if missing. Explicit side effect."""
        for path in (self.raw, self.processed, self.cache):
            path.mkdir(parents=True, exist_ok=True)
        return self
