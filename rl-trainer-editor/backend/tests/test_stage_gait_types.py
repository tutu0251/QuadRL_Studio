"""Tests for multi-select stage gate types."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import CurriculumStage, RlTrainerModel
from domain.stage_gait import stage_gait_type_ids, stage_is_stand_only, stage_primary_gait_for_command
from domain.trainer_core import TrainerCore
from validator.validator import RlTrainerValidator


def test_legacy_gait_type_id_migrates_to_list():
    stage = CurriculumStage(id="s1", name="S", order=0, gaitTypeId="walk")
    assert stage.gaitTypeIds == ["walk"]


def test_multi_select_gate_types_validate():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    m = core.get_model()
    stages = [s.model_copy(deep=True) for s in m.curriculum.stages]
    stages[1].gaitTypeIds = ["walk", "trot"]
    m.curriculum.stages = stages
    result = RlTrainerValidator(m).validate()
    assert result.valid


def test_stand_only_when_all_none():
    stage = CurriculumStage(id="s", name="S", order=0, gaitTypeIds=["none"])
    assert stage_is_stand_only(stage)
    assert stage_primary_gait_for_command(stage) == "none"


def test_locomotion_when_mixed_none_and_walk():
    stage = CurriculumStage(id="s", name="S", order=0, gaitTypeIds=["none", "walk"])
    assert not stage_is_stand_only(stage)
    assert stage_primary_gait_for_command(stage) == "walk"
    assert stage_gait_type_ids(stage) == ["none", "walk"]
