"""Recommend PPO hyperparameters from machine profile."""
from __future__ import annotations

import math

from domain.models import ComputeDevice, MachineProfile, PpoHyperparams
from planner.defaults import SB3_BASELINE


def _round_down_pow2(n: int, minimum: int = 64) -> int:
    if n <= minimum:
        return minimum
    p = 1 << (n.bit_length() - 1)
    return max(minimum, p)


def _round_up_pow2(n: int, minimum: int = 64) -> int:
    if n < minimum:
        return minimum
    return 1 << (n - 1).bit_length()


def recommend_ppo_params(machine: MachineProfile) -> tuple[PpoHyperparams, list[str]]:
    """Return SB3-style PPO params tuned for the host."""
    notes: list[str] = []
    p = SB3_BASELINE.model_copy(deep=True)

    ram = machine.ramGb or 8.0
    physical = max(1, machine.cpuCountPhysical)
    logical = max(1, machine.cpuCountLogical)

    if ram < 8:
        p.nSteps = 1024
        p.batchSize = 32
        p.numEnvs = 1
        notes.append(f"RAM {ram:.1f} GB — reduced rollout (n_steps=1024, batch=32, 1 env).")
    elif ram < 16:
        p.nSteps = 2048
        p.batchSize = 64
        p.numEnvs = min(2, max(1, physical // 4))
        notes.append(f"RAM {ram:.1f} GB — standard rollout with up to 2 parallel envs.")
    elif ram < 32:
        p.nSteps = 2048
        p.batchSize = 128
        p.numEnvs = min(4, max(1, physical // 2))
        notes.append(f"RAM {ram:.1f} GB — larger batch (128) and up to 4 envs.")
    else:
        p.nSteps = 4096
        p.batchSize = 256
        p.numEnvs = min(8, max(2, physical // 2))
        notes.append(f"RAM {ram:.1f} GB — high-memory rollout (n_steps=4096, batch=256).")

    if machine.gpuAvailable:
        p.device = ComputeDevice.CUDA
        if machine.vramGb >= 12:
            p.batchSize = min(512, p.batchSize * 2)
            p.numEnvs = min(8, max(p.numEnvs, min(4, logical // 2)))
            notes.append(
                f"GPU {machine.gpuName} ({machine.vramGb:.1f} GB VRAM) — CUDA, "
                f"scaled batch to {p.batchSize}."
            )
        elif machine.vramGb >= 6:
            p.batchSize = min(256, max(p.batchSize, 128))
            notes.append(
                f"GPU {machine.gpuName} ({machine.vramGb:.1f} GB VRAM) — CUDA with moderate batch."
            )
        else:
            notes.append(
                f"GPU {machine.gpuName} ({machine.vramGb:.1f} GB VRAM) — CUDA; "
                "keep batch moderate to avoid OOM."
            )
    else:
        p.device = ComputeDevice.CPU
        p.numEnvs = min(p.numEnvs, max(1, physical // 2))
        p.batchSize = min(p.batchSize, 64)
        notes.append("No GPU — CPU training; capped batch size and parallel envs.")

    rollout = p.nSteps * p.numEnvs
    if rollout % p.batchSize != 0:
        p.batchSize = _round_down_pow2(
            math.gcd(rollout, p.batchSize) or p.batchSize,
            minimum=32,
        )
        if rollout % p.batchSize != 0:
            for candidate in (64, 128, 256, 32):
                if rollout % candidate == 0:
                    p.batchSize = candidate
                    break
        notes.append(f"Adjusted batch_size={p.batchSize} so n_steps×num_envs divides evenly.")

    p.nSteps = _round_up_pow2(p.nSteps, minimum=512)
    p.totalTimesteps = 1_000_000 if ram >= 8 else 500_000

    return p, notes
