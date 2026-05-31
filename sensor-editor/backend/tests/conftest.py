"""Pytest path setup for sensor-editor backend tests."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
WS_BACKEND = Path(__file__).resolve().parents[3] / "workspace-generator" / "backend"
for path in (BACKEND, WS_BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
