"""Detect host CPU, RAM, and GPU — shared with RL Trainer profiler patterns."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone

from pydantic import BaseModel


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MachineProfile(BaseModel):
    hostname: str
    platform: str
    cpuCountLogical: int
    cpuCountPhysical: int
    ramGb: float
    ramUsedGb: float
    ramTotalMb: int
    ramUsedMb: int
    ramAvailableMb: int
    gpuAvailable: bool
    gpuName: str
    vramGb: float
    profiledAt: str


def _ram_stats() -> tuple[float, float, int, int, int]:
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            mem_total_kb = 0
            mem_available_kb = 0
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available_kb = int(line.split()[1])
            if mem_total_kb > 0:
                used_kb = max(0, mem_total_kb - mem_available_kb)
                total_mb = mem_total_kb // 1024
                used_mb = used_kb // 1024
                available_mb = mem_available_kb // 1024
                total_gb = mem_total_kb / (1024 * 1024)
                used_gb = used_kb / (1024 * 1024)
                return total_gb, used_gb, total_mb, used_mb, available_mb
    except OSError:
        pass
    return 0.0, 0.0, 0, 0, 0


def _physical_cpu_count() -> int:
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            physical_ids: set[str] = set()
            for line in f:
                if line.startswith("physical id"):
                    physical_ids.add(line.split(":")[1].strip())
            if physical_ids:
                cores_per_socket = 0
                f.seek(0)
                for line in f:
                    if line.startswith("cpu cores"):
                        cores_per_socket = int(line.split(":")[1].strip())
                        break
                if cores_per_socket:
                    return max(1, len(physical_ids) * cores_per_socket)
    except OSError:
        pass
    return os.cpu_count() or 1


def _gpu_via_nvidia_smi() -> tuple[bool, str, float]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return False, "", 0.0
    try:
        out = subprocess.check_output(
            [smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        ).strip()
        if not out:
            return False, "", 0.0
        line = out.splitlines()[0]
        name, mem = [p.strip() for p in line.split(",", 1)]
        vram = float(mem) / 1024.0 if mem else 0.0
        return True, name, round(vram, 1)
    except (subprocess.SubprocessError, ValueError, OSError):
        return False, "", 0.0


def _gpu_via_torch() -> tuple[bool, str, float]:
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return False, "", 0.0
    if not torch.cuda.is_available():
        return False, "", 0.0
    idx = 0
    name = torch.cuda.get_device_name(idx)
    props = torch.cuda.get_device_properties(idx)
    vram = props.total_memory / (1024**3)
    return True, name, round(vram, 1)


def profile_machine() -> MachineProfile:
    gpu_ok, gpu_name, vram = _gpu_via_torch()
    if not gpu_ok:
        gpu_ok, gpu_name, vram = _gpu_via_nvidia_smi()

    logical = os.cpu_count() or 1
    physical = _physical_cpu_count()
    ram_total, ram_used, total_mb, used_mb, available_mb = _ram_stats()

    return MachineProfile(
        hostname=platform.node(),
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        cpuCountLogical=logical,
        cpuCountPhysical=physical,
        ramGb=round(ram_total, 2),
        ramUsedGb=round(ram_used, 4),
        ramTotalMb=total_mb,
        ramUsedMb=used_mb,
        ramAvailableMb=available_mb,
        gpuAvailable=gpu_ok,
        gpuName=gpu_name,
        vramGb=vram,
        profiledAt=utc_now_iso(),
    )
