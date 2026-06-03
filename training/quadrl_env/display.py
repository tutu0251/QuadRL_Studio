"""Resolve a usable X11 DISPLAY for Gazebo GUI (desktop, VNC, ssh -X)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _display_usable(display: str) -> bool:
    display = display.strip()
    if not display:
        return False
    try:
        proc = subprocess.run(
            ["xdpyinfo"],
            env={**os.environ, "DISPLAY": display},
            capture_output=True,
            timeout=3,
        )
        if proc.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    num = display.lstrip(":")
    if num.isdigit():
        return Path(f"/tmp/.X11-unix/X{num}").exists()
    return False


def _candidate_displays() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(d: str) -> None:
        d = d.strip()
        if d and d not in seen:
            seen.add(d)
            out.append(d)

    add(os.environ.get("QUADRL_DISPLAY", ""))
    add(os.environ.get("DISPLAY", ""))

    x_dir = Path("/tmp/.X11-unix")
    if x_dir.is_dir():
        nums: list[int] = []
        for entry in x_dir.iterdir():
            if entry.name.startswith("X") and entry.name[1:].isdigit():
                nums.append(int(entry.name[1:]))
        for n in sorted(nums):
            add(f":{n}")
    return out


def resolve_display() -> str | None:
    """Return first working DISPLAY value, or None."""
    for display in _candidate_displays():
        if _display_usable(display):
            return display
    return None


def ensure_display_for_gui() -> str:
    """Set os.environ['DISPLAY'] for GUI sim; raise if no display is available."""
    display = resolve_display()
    if not display:
        raise RuntimeError(
            "No usable X11 display found — Gazebo GUI cannot start.\n"
            "Use Headless mode, start a desktop/VNC session on this host, set DISPLAY (e.g. :10), "
            "or export QUADRL_DISPLAY=:10 before training."
        )
    os.environ["DISPLAY"] = display
    return display
