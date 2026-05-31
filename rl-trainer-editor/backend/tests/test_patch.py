"""Tests for patch and API route behavior."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import RlTrainerModel, RlTrainerPatch
from domain.trainer_core import TrainerCore


def test_patch_curriculum_keeps_model_types():
    model = RlTrainerModel(projectName="bot", robotName="bot")
    core = TrainerCore(model)
    core.apply_curriculum("stand_sprint")
    m = core.get_model()
    stage = m.curriculum.stages[0]
    stage.name = "Renamed stand"
    core.patch(RlTrainerPatch(curriculum=m.curriculum))
    updated = core.get_model()
    assert updated.curriculum.stages[0].name == "Renamed stand"
    assert hasattr(updated.curriculum, "curriculumId")
    assert updated.curriculumLibrary


def test_add_curriculum_route_not_shadowed():
    """Static /curriculum/add must be registered before apply template route."""
    from fastapi.routing import APIRoute

    from api.main import app

    paths = [r.path for r in app.routes if isinstance(r, APIRoute)]
    add_idx = paths.index("/api/projects/{name}/curriculum/add")
    apply_idx = paths.index("/api/projects/{name}/curriculum/{curriculum_id}")
    assert add_idx < apply_idx
