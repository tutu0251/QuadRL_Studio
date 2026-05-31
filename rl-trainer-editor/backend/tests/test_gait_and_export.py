"""Tests for gait defaults and recommender."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import CurriculumStage, RlTrainerModel
from domain.trainer_core import TrainerCore
from exporter.rl_yaml_exporter import export_rl_yaml
from planner.gait_defaults import build_gait, default_gait_library
from planner.recommender import recommend_gait, recommend_stage_params
from storage import project_storage
from validator.validator import RlTrainerValidator


def test_default_gait_library_has_seven():
    gaits = default_gait_library()
    assert len(gaits) == 7
    assert gaits[0].id == "stand"
    assert gaits[-1].id == "gallop"


def test_trot_diagonal_phases():
    trot = build_gait("trot")
    assert trot.phaseOffsets.fl == trot.phaseOffsets.rr
    assert trot.phaseOffsets.fr == trot.phaseOffsets.rl


def test_recommend_gait():
    gait, notes = recommend_gait("walk")
    assert gait.cycleTime > 0
    assert notes


def test_export_includes_gait_and_training(tmp_path, monkeypatch):
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    name = "export_bot"
    project_storage.ensure_project_dirs(name)
    model = RlTrainerModel(projectName=name, robotName=name)
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    m = core.get_model()
    path = export_rl_yaml(m, name)
    text = path.read_text()
    assert "gait_types:" in text
    assert "training:" in text
    assert "resume_checkpoint:" in text
    assert "gait_type_id:" in text


def test_rough_curriculum_has_disturbances():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint_rough")
    stages = core.get_model().curriculum.stages
    assert any(s.disturbance.enabled for s in stages)
