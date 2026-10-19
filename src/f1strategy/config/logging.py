"""Logging configuration.

WHY THIS FILE EXISTS
    The original script used ``print(...)`` for everything. Libraries must not
    print — they log, and the *application* decides where logs go. This module
    configures logging exactly once, at the composition root (CLI / Streamlit
    entrypoint). Importing a library module never configures logging.

DESIGN
    A single ``configure_logging(level)`` call installs a stream handler with a
    concise format. Idempotent: calling it twice does not stack duplicate
    handlers. Individual modules obtain a logger via ``logging.getLogger(__name__)``.
"""

from __future__ import annotations

import logging

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Install the root handler once. Safe to call multiple times."""
    global _CONFIGURED
    numeric = getattr(logging, level.upper(), logging.INFO)
    if _CONFIGURED:
        logging.getLogger().setLevel(numeric)
        return
    logging.basicConfig(level=numeric, format=_FORMAT)
    # FastF1 is chatty at INFO; keep its noise one level above ours.
    logging.getLogger("fastf1").setLevel(max(numeric, logging.WARNING))
    _CONFIGURED = True
