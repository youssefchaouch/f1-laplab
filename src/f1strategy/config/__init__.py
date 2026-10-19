"""Configuration layer — settings, paths, logging.

A cross-cutting leaf: depends only on the standard library. Every business layer
receives a ``Settings`` instance by injection rather than reading globals.
"""

from f1strategy.config.logging import configure_logging
from f1strategy.config.paths import ProjectPaths, find_project_root
from f1strategy.config.settings import Settings

__all__ = ["Settings", "ProjectPaths", "find_project_root", "configure_logging"]
