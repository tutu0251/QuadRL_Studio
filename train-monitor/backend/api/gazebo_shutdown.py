"""Graceful shutdown helpers for Train Monitor spawn-test Gazebo sessions."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from typing import Any, Optional

# Spawn test uses the stock empty world — scope stray cleanup to this launcher.
_SPAWN_TEST_CMD_MARKERS = (
    "ign gazebo -s /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf",
    "ign gazebo /usr/share/ignition/ignition-gazebo6/worlds/empty.sdf",
)


def request_ign_server_stop(*, timeout_ms: int = 8000) -> bool:
    """Ask a running Ignition/Gazebo sim server to stop via /server_control."""
    try:
        proc = subprocess.run(
            [
                "ign",
                "service",
                "-s",
                "/server_control",
                "--reqtype",
                "ignition.msgs.ServerControl",
                "--reptype",
                "ignition.msgs.Boolean",
                "--timeout",
                str(timeout_ms),
                "--req",
                "stop: true",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=max(5.0, timeout_ms / 1000.0 + 2.0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0 and "true" in out.lower()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_for_pid_exit(pid: int, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.2)
    return not _pid_alive(pid)


def _signal_process_group(root_pid: int, sig: int) -> None:
    try:
        pgid = os.getpgid(root_pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def _signal_process(root_pid: int, sig: int) -> None:
    try:
        os.kill(root_pid, sig)
    except ProcessLookupError:
        pass


def _pkill_spawn_test_strays(*, sig: int) -> None:
    flag = "-INT" if sig == signal.SIGINT else "-TERM" if sig == signal.SIGTERM else "-KILL"
    for pattern in _SPAWN_TEST_CMD_MARKERS:
        subprocess.run(["pkill", flag, "-f", pattern], check=False)


def graceful_stop_gazebo_process(
    proc: Optional[Any],
    pid: Optional[int],
    *,
    server_stop_timeout_s: float = 15.0,
) -> None:
    """Stop a spawn-test Gazebo session: server_control, then SIGINT/TERM/KILL."""
    root_pid: Optional[int] = None
    if proc is not None and proc.poll() is None:
        root_pid = int(proc.pid)
    elif pid is not None and _pid_alive(pid):
        root_pid = int(pid)

    if root_pid is None and not request_ign_server_stop():
        _pkill_spawn_test_strays(sig=signal.SIGTERM)
        time.sleep(0.5)
        _pkill_spawn_test_strays(sig=signal.SIGKILL)
        return

    request_ign_server_stop()
    if root_pid is not None and wait_for_pid_exit(root_pid, server_stop_timeout_s):
        if proc is not None:
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
        return

    if proc is not None and proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        if wait_for_pid_exit(proc.pid, 5.0):
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
            return

    if root_pid is not None:
        for sig, wait_s in ((signal.SIGINT, 4.0), (signal.SIGTERM, 8.0)):
            _signal_process_group(root_pid, sig)
            _signal_process(root_pid, sig)
            if wait_for_pid_exit(root_pid, wait_s):
                return

        _signal_process_group(root_pid, signal.SIGKILL)
        _signal_process(root_pid, signal.SIGKILL)
        wait_for_pid_exit(root_pid, 3.0)

    _pkill_spawn_test_strays(sig=signal.SIGINT)
    time.sleep(0.5)
    _pkill_spawn_test_strays(sig=signal.SIGTERM)
    time.sleep(0.5)
    _pkill_spawn_test_strays(sig=signal.SIGKILL)
