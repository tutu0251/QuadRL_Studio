"""Tests for RL trainer validator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import RlTrainerModel
from domain.trainer_core import TrainerCore
from validator.validator import RlTrainerValidator


def test_empty_task_invalid():
    model = RlTrainerModel(projectName="x", rewardTerms=[], customParams={})
    result = RlTrainerValidator(model).validate()
    assert not result.valid
    assert any(e.code == "no_task_definition" for e in result.errors)


def test_bootstrapped_model_valid():
    model = TrainerCore.bootstrap_project("test_robot")
    model.projectName = "test_robot"
    result = RlTrainerValidator(model).validate()
    assert result.valid


def test_batch_divisor_warning():
    model = TrainerCore.bootstrap_project("test")
    model.hyperparams.nSteps = 2047
    model.hyperparams.batchSize = 64
    model.parallel.numEnvs = 1
    result = RlTrainerValidator(model).validate()
    assert any(w.code == "batch_divisor" for w in result.warnings)
