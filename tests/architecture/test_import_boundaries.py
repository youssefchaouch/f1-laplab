"""Architecture guard: FastF1 may be imported ONLY in the telemetry layer.

This is the mechanical enforcement of ADR-0002. If any future contributor (or
agent) imports ``fastf1`` outside ``telemetry/``, this test fails the build —
the anti-corruption boundary cannot silently rot.
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src" / "f1strategy"
_ALLOWED_DIR = _SRC / "telemetry"
_IMPORT_RE = re.compile(r"^\s*(?:import\s+fastf1|from\s+fastf1)", re.MULTILINE)


def test_fastf1_only_imported_in_telemetry() -> None:
    offenders: list[str] = []
    for path in _SRC.rglob("*.py"):
        if _ALLOWED_DIR in path.parents:
            continue
        if _IMPORT_RE.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(_SRC)))
    assert not offenders, (
        "fastf1 must only be imported under telemetry/ (ADR-0002). "
        f"Offending files: {offenders}"
    )
