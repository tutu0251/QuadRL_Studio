"""Stop Gazebo / ros2 launch processes left after training exits."""
from __future__ import annotations

import os
import signal
import subprocess
import time

# Patterns for orphaned sim processes (training host only).
_GAZEBO_PATTERNS = (
    "sim.launch.py",
    "gz sim",
    "ign gazebo",
    "ruby.*gz sim",
)


def pkill_gazebo_strays(*, sig: int = signal.SIGTERM) -> None:
    flag = "-TERM" if sig == signal.SIGTERM else "-KILL"
    for pattern in _GAZEBO_PATTERNS:
        subprocess.run(["pkill", flag, "-f", pattern], check=False)


def terminate_process_group(root_pid: int, *, grace_sec: float = 12.0) -> None:
    """Send SIGTERM then SIGKILL to every process in root_pid's process group."""
    try:
        pgid = os.getpgid(root_pid)
    except ProcessLookupError:
        return

    for sig, wait in ((signal.SIGTERM, grace_sec), (signal.SIGKILL, 3.0)):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        deadline = time.time() + wait
        while time.time() < deadline:
            try:
                os.kill(root_pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.15)


def cleanup_training_gazebo(launch_pid: int | None = None) -> None:
    """Best-effort shutdown of training Gazebo (launch tree + stray processes)."""
    if launch_pid is not None and launch_pid > 0:
        terminate_process_group(launch_pid)
    pkill_gazebo_strays(sig=signal.SIGTERM)
    time.sleep(0.4)
    pkill_gazebo_strays(sig=signal.SIGKILL)
