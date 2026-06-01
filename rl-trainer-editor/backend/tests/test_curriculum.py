"""Tests for progressive training curricula."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import RlTrainerModel
from domain.trainer_core import TrainerCore
from planner.curriculum import build_stand_sprint_curriculum, curriculum_total_timesteps
from validator.validator import RlTrainerValidator


def test_stand_sprint_has_seven_stages():
    cur = build_stand_sprint_curriculum()
    assert len(cur.stages) == 7
    assert cur.stages[0].id == "none"
    assert cur.stages[0].name == "Stand"
    assert cur.stages[0].gaitTypeIds == ["none"]
    assert cur.stages[1].id == "recover"
    assert cur.stages[1].gaitTypeIds == ["none"]
    assert cur.stages[-1].gaitTypeIds == ["gallop"]
    assert cur.stages[0].targetLinVelX == 0.0
    assert cur.stages[-1].targetLinVelX > 0


def test_apply_curriculum_sets_rewards():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    m = core.get_model()
    assert m.curriculum.enabled
    assert m.curriculum.curriculumId == "stand_sprint"
    assert len(m.rewardTerms) > 0
    assert len(m.gaitTypes) == 4
    ids = {t.id for t in m.rewardTerms}
    assert "height" in ids or "forward_tracking" in ids


def test_curriculum_validates():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    result = RlTrainerValidator(core.get_model()).validate()
    assert result.valid


def test_stage_advance_updates_active_rewards():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    core.set_curriculum_stage(3)
    m = core.get_model()
    assert m.curriculum.currentStageIndex == 3
    assert m.curriculum.stages[3].gaitTypeIds == ["trot"]


def test_duplicate_stage():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    stage_id = core.get_model().curriculum.stages[0].id
    core.duplicate_stage(stage_id)
    m = core.get_model()
    assert len(m.curriculum.stages) == 8
    assert m.curriculum.stages[1].name.endswith("(copy)")


def test_add_curriculum():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    core.add_curriculum("Custom plan")
    m = core.get_model()
    assert any(e.name == "Custom plan" for e in m.curriculumLibrary)
