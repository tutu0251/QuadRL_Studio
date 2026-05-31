"""Tests for machine-based PPO recommendations."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from domain.models import MachineProfile, ParallelConfig, VecEnvType
from planner.recommender import recommend_ppo_config


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
    params, parallel, notes = recommend_ppo_config(_machine(ramGb=4.0))
    assert params.nSteps == 1024
    assert params.batchSize == 32
    assert parallel.numEnvs == 1
    assert parallel.vecEnvType == VecEnvType.DUMMY
    assert any("RAM" in n for n in notes)


def test_gpu_sets_cuda():
    params, parallel, notes = recommend_ppo_config(
        _machine(gpuAvailable=True, gpuName="RTX", vramGb=8.0)
    )
    assert params.device.value == "cuda"
    assert parallel.numEnvs >= 1
    assert any("GPU" in n for n in notes)


def test_batch_divides_rollout():
    params, parallel, _ = recommend_ppo_config(_machine(ramGb=32.0, cpuCountPhysical=8))
    rollout = params.nSteps * parallel.numEnvs
    assert rollout % params.batchSize == 0


def test_subproc_sets_n_proc():
    _, parallel, notes = recommend_ppo_config(_machine(ramGb=32.0, cpuCountPhysical=8))
    if parallel.vecEnvType == VecEnvType.SUBPROC:
        assert parallel.nProc is not None
        assert parallel.nProc <= parallel.numEnvs
        assert any("n_proc" in n for n in notes)
