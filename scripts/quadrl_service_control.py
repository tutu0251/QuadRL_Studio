"""QuadRL Studio service status and control helpers."""
from __future__ import annotations

import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parent.parent

EDITOR_SERVICES: dict[str, dict[str, int | str]] = {
    "geometry-editor": {"label": "Geometry Editor", "backend": 8000, "frontend": 5173},
    "physics-editor": {"label": "Physics Editor", "backend": 8001, "frontend": 5174},
    "control-editor": {"label": "Control Editor", "backend": 8002, "frontend": 5175},
    "sensor-editor": {"label": "Sensor Editor", "backend": 8003, "frontend": 5176},
    "ppo-planner": {"label": "PPO Planner", "backend": 8004, "frontend": 5177},
    "rl-trainer-editor": {"label": "RL Trainer Editor", "backend": 8005, "frontend": 5178},
    "train-monitor": {"label": "Train Monitor", "backend": 8006, "frontend": 5179},
}

RestartScope = Literal["all"] | str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _read_uptime_seconds() -> float | None:
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            return float(f.readline().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _systemd_active(unit: str = "quadrl-studio.service") -> bool | None:
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", unit],
            text=True,
            timeout=3,
        ).strip()
        return out == "active"
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def service_status(name: str) -> dict:
    spec = EDITOR_SERVICES[name]
    backend_port = int(spec["backend"])
    frontend_port = int(spec["frontend"])
    backend_up = _port_open(backend_port)
    frontend_up = _port_open(frontend_port)
    if backend_up and frontend_up:
        state = "running"
    elif backend_up or frontend_up:
        state = "partial"
    else:
        state = "stopped"
    return {
        "id": name,
        "label": str(spec["label"]),
        "backendPort": backend_port,
        "frontendPort": frontend_port,
        "backendUp": backend_up,
        "frontendUp": frontend_up,
        "state": state,
    }


def all_services_status() -> dict:
    services = [service_status(name) for name in EDITOR_SERVICES]
    running = sum(1 for s in services if s["state"] == "running")
    partial = sum(1 for s in services if s["state"] == "partial")
    stopped = sum(1 for s in services if s["state"] == "stopped")
    uptime = _read_uptime_seconds()
    boot_at = None
    if uptime is not None:
        boot_at = datetime.fromtimestamp(time.time() - uptime, tz=timezone.utc).isoformat()

    if running == len(services):
        overall = "running"
    elif running + partial > 0:
        overall = "partial"
    else:
        overall = "stopped"

    return {
        "checkedAt": _utc_now_iso(),
        "hostname": os.uname().nodename,
        "overall": overall,
        "runningCount": running,
        "partialCount": partial,
        "stoppedCount": stopped,
        "totalServices": len(services),
        "uptimeSeconds": uptime,
        "bootAt": boot_at,
        "systemdUnit": "quadrl-studio.service",
        "systemdActive": _systemd_active(),
        "services": services,
    }


def schedule_restart(scope: RestartScope = "all", delay_sec: float = 2.0) -> dict:
    if scope != "all" and scope not in EDITOR_SERVICES:
        raise ValueError(f"Unknown service scope: {scope}")

    script = REPO_ROOT / "scripts" / "restart_services.sh"
    cmd = ["bash", str(script), str(scope), str(delay_sec)]
    subprocess.Popen(cmd, cwd=str(REPO_ROOT), start_new_session=True)
    return {
        "scheduledAt": _utc_now_iso(),
        "scope": scope,
        "delaySeconds": delay_sec,
        "message": f"Restart scheduled for {scope} in {delay_sec:.0f}s",
    }


def schedule_reboot(delay_sec: float = 5.0) -> dict:
    script = REPO_ROOT / "scripts" / "reboot_machine.sh"
    subprocess.Popen(
        ["bash", str(script), str(delay_sec)],
        cwd=str(REPO_ROOT),
        start_new_session=True,
    )
    return {
        "scheduledAt": _utc_now_iso(),
        "delaySeconds": delay_sec,
        "message": f"Machine reboot scheduled in {delay_sec:.0f}s",
    }
