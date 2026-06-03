"""Probe X11 display for Train Monitor API (imports training quadrl_env)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TRAINING = _REPO / "training"
if str(_TRAINING) not in sys.path:
    sys.path.insert(0, str(_TRAINING))

from quadrl_env.display import resolve_display  # noqa: E402


def display_status_dict() -> dict:
    import os

    resolved = resolve_display()
    env_display = os.environ.get("DISPLAY", "").strip() or None
    return {
        "gui_available": resolved is not None,
        "resolved_display": resolved,
        "env_display": env_display,
    }
