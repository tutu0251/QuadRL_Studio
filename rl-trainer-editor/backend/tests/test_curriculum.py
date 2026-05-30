"""Tests for progressive training curricula."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import RlTrainerModel
from domain.trainer_core import TrainerCore
from planner.curriculum import build_stand_to_sprint_curriculum, curriculum_total_timesteps
from validator.validator import RlTrainerValidator


def test_stand_to_sprint_has_five_stages():
    cur = build_stand_to_sprint_curriculum()
    assert len(cur.stages) == 5
    assert cur.stages[0].targetLinVelX == 0.0
    assert cur.stages[-1].targetLinVelX == 1.5
    assert curriculum_total_timesteps(cur) == 2_100_000


def test_apply_curriculum_sets_rewards_and_timesteps():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_to_sprint")
    m = core.get_model()
    assert m.curriculum.enabled
    assert m.curriculum.curriculumId == "stand_to_sprint"
    assert len(m.rewardTerms) > 0
    assert m.hyperparams.totalTimesteps == 2_100_000
    assert m.rewardTerms[0].id in ("base_height", "lin_vel_tracking")


def test_curriculum_validates():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_to_sprint")
    result = RlTrainerValidator(core.get_model()).validate()
    assert result.valid


def test_stage_advance_updates_active_rewards():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_to_sprint")
    core.set_curriculum_stage(3)
    m = core.get_model()
    assert m.curriculum.currentStageIndex == 3
    assert any(t.params.get("target_lin_vel_x") == 1.0 for t in m.rewardTerms)
