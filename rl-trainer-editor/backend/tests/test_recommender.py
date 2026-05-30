"""Tests for machine-based training recommendations."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import MachineProfile
from planner.recommender import recommend_training_config


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
    hyper, par, notes = recommend_training_config(_machine(ramGb=4.0))
    assert hyper.nSteps == 1024
    assert hyper.batchSize == 32
    assert par.numEnvs == 1
    assert any("RAM" in n for n in notes)


def test_gpu_sets_cuda():
    hyper, _, notes = recommend_training_config(
        _machine(gpuAvailable=True, gpuName="RTX", vramGb=8.0)
    )
    assert hyper.device.value == "cuda"
    assert any("GPU" in n for n in notes)


def test_batch_divides_rollout():
    hyper, par, _ = recommend_training_config(_machine(ramGb=32.0, cpuCountPhysical=8))
    rollout = hyper.nSteps * par.numEnvs
    assert rollout % hyper.batchSize == 0
