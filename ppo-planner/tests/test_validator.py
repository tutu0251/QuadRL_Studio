"""Tests for PPO planner validation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from domain.models import ParallelConfig, PpoHyperparams, PpoPlannerModel, VecEnvType
from validator.validator import PpoValidator


def test_valid_parallel_config():
    model = PpoPlannerModel(
        params=PpoHyperparams(nSteps=2048, batchSize=64),
        parallel=ParallelConfig(numEnvs=2, vecEnvType=VecEnvType.SUBPROC, nProc=2),
    )
    result = PpoValidator(model).validate()
    assert result.valid


def test_dummy_with_n_proc_invalid():
    model = PpoPlannerModel(
        params=PpoHyperparams(nSteps=2048, batchSize=64),
        parallel=ParallelConfig(numEnvs=2, vecEnvType=VecEnvType.DUMMY, nProc=2),
    )
    result = PpoValidator(model).validate()
    assert not result.valid
    assert any(i.code == "parallel_conflict" for i in result.errors)


def test_legacy_num_envs_migrated():
    raw = {
        "projectName": "demo",
        "params": {
            "learningRate": 3e-4,
            "nSteps": 2048,
            "batchSize": 64,
            "nEpochs": 10,
            "gamma": 0.99,
            "gaeLambda": 0.95,
            "clipRange": 0.2,
            "entCoef": 0.0,
            "vfCoef": 0.5,
            "maxGradNorm": 0.5,
            "totalTimesteps": 1_000_000,
            "numEnvs": 4,
            "device": "auto",
        },
    }
    model = PpoPlannerModel.model_validate(raw)
    assert model.parallel.numEnvs == 4
    assert "numEnvs" not in model.params.model_dump()
