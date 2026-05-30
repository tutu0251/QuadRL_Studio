"""Tests for machine-based PPO recommendations."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from domain.models import MachineProfile
from planner.recommender import recommend_ppo_params


def _machine(**kwargs) -> MachineProfile:
    base = {
        "hostname": "test",
        "platform": "Linux",
        "cpuCountLogical": 8,
        "cpuCountPhysical": 4,
        "ramGb": 16.0,
        "gpuAvailable": False,
        "gpuName": "",
        "vramGb": 0.0,
        "profiledAt": "2020-01-01T00:00:00+00:00",
    }
    base.update(kwargs)
    return MachineProfile(**base)


def test_low_ram_reduces_rollout():
    params, notes = recommend_ppo_params(_machine(ramGb=4.0))
    assert params.nSteps == 1024
    assert params.batchSize == 32
    assert params.numEnvs == 1
    assert any("RAM" in n for n in notes)


def test_gpu_sets_cuda():
    params, notes = recommend_ppo_params(
        _machine(gpuAvailable=True, gpuName="RTX", vramGb=8.0)
    )
    assert params.device.value == "cuda"
    assert any("GPU" in n for n in notes)


def test_batch_divides_rollout():
    params, _ = recommend_ppo_params(_machine(ramGb=32.0, cpuCountPhysical=8))
    rollout = params.nSteps * params.numEnvs
    assert rollout % params.batchSize == 0
