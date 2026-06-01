"""Realtime host CPU, RAM, and GPU utilization for the training machine."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime, timezone

from profiler.machine_profiler import _ram_stats, profile_machine


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cpu_percent(sample_interval: float = 0.12) -> float:
    """Host CPU utilization from /proc/stat (all cores)."""
    try:

        def snap() -> tuple[int, int]:
            with open("/proc/stat", encoding="utf-8") as f:
                parts = f.readline().split()
            if not parts or parts[0] != "cpu":
                return 0, 0
            fields = [int(x) for x in parts[1:]]
            idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
            total = sum(fields)
            return idle, total

        idle1, total1 = snap()
        time.sleep(sample_interval)
        idle2, total2 = snap()
        dt = total2 - total1
        if dt <= 0:
            return 0.0
        return round(100.0 * (1.0 - (idle2 - idle1) / dt), 1)
    except (OSError, ValueError, IndexError):
        return 0.0


def _gpu_utilization() -> dict:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {
            "gpuAvailable": False,
            "gpuName": "",
            "gpuUtilPercent": None,
            "gpuMemoryUsedMb": None,
            "gpuMemoryTotalMb": None,
            "gpuMemoryPercent": None,
        }
    try:
        out = subprocess.check_output(
            [
                smi,
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        ).strip()
        if not out:
            return {
                "gpuAvailable": False,
                "gpuName": "",
                "gpuUtilPercent": None,
                "gpuMemoryUsedMb": None,
                "gpuMemoryTotalMb": None,
                "gpuMemoryPercent": None,
            }
        name, util, mem_used, mem_total = [p.strip() for p in out.splitlines()[0].split(",", 3)]
        used_mb = float(mem_used)
        total_mb = float(mem_total)
        mem_pct = round(100.0 * used_mb / total_mb, 1) if total_mb > 0 else None
        return {
            "gpuAvailable": True,
            "gpuName": name,
            "gpuUtilPercent": float(util),
            "gpuMemoryUsedMb": round(used_mb, 1),
            "gpuMemoryTotalMb": round(total_mb, 1),
            "gpuMemoryPercent": mem_pct,
        }
    except (subprocess.SubprocessError, ValueError, OSError):
        return {
            "gpuAvailable": False,
            "gpuName": "",
            "gpuUtilPercent": None,
            "gpuMemoryUsedMb": None,
            "gpuMemoryTotalMb": None,
            "gpuMemoryPercent": None,
        }


def sample_system_stats() -> dict:
    """Lightweight sample for UI polling (~1–2 Hz)."""
    total_gb, used_gb, total_mb, used_mb, available_mb = _ram_stats()
    ram_pct = round(100.0 * used_mb / total_mb, 1) if total_mb > 0 else 0.0
    gpu = _gpu_utilization()
    return {
        "sampledAt": _utc_now_iso(),
        "hostname": os.uname().nodename,
        "cpuPercent": _cpu_percent(),
        "cpuCountLogical": os.cpu_count() or 1,
        "ramTotalMb": total_mb,
        "ramUsedMb": used_mb,
        "ramAvailableMb": available_mb,
        "ramUsedPercent": ram_pct,
        "ramTotalGb": round(total_gb, 4),
        "ramUsedGb": round(used_gb, 4),
        **gpu,
    }


def machine_profile_dict() -> dict:
    return profile_machine().model_dump()
