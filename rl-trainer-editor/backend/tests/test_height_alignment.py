"""Regression: the per-robot grounded height must reach the curriculum after a
template (re)build, not the generic PLACEHOLDER_BODY_HEIGHT_M.

Reproduces the live failure where a re-applied curriculum exported the placeholder
standing height (0.2933 -> fall threshold 0.1933) instead of the project's real
height_policy, spawning the robot below its own fall line so every episode ended
at step 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import domain.migration as migration
from domain.migration import align_model_heights
from domain.models import RlTrainerModel
from domain.trainer_core import TrainerCore
from planner.standing_heights import (
    PLACEHOLDER_BODY_HEIGHT_M,
    StandingHeightParams,
    fall_threshold_for_target,
)

# A robot whose grounded base_link sits ~4 cm below ground at stance (the my_robot case).
REAL = StandingHeightParams(
    spawn_z=-0.0417,
    target_body_height=-0.0417,
    fall_base_height_threshold=-0.1417,
    fall_drop_margin_m=0.10,
)


def _model_with_applied_curriculum() -> RlTrainerModel:
    core = TrainerCore(RlTrainerModel(projectName="bot", robotName="bot"))
    core.apply_curriculum("stand_sprint")
    return core.get_model()


def test_apply_curriculum_uses_real_height_when_project_policy_present(monkeypatch):
    monkeypatch.setattr(migration, "_load_project_heights", lambda name: REAL)
    model = _model_with_applied_curriculum()
    for s in model.curriculum.stages:
        assert s.command.targetBodyHeight == -0.0417
        assert s.termination.fallBaseHeightThreshold == -0.1417
    assert model.termination.fallBaseHeightThreshold == -0.1417


def test_align_rewrites_leaked_placeholder_to_project_height(monkeypatch):
    # No project policy at build time -> placeholder leaks in (the regen scenario).
    monkeypatch.setattr(migration, "_load_project_heights", lambda name: None)
    model = _model_with_applied_curriculum()
    s0 = model.curriculum.stages[0]
    assert s0.command.targetBodyHeight == PLACEHOLDER_BODY_HEIGHT_M
    assert s0.termination.fallBaseHeightThreshold == fall_threshold_for_target(PLACEHOLDER_BODY_HEIGHT_M)

    # Project height_policy now available -> realignment must purge the placeholder.
    monkeypatch.setattr(migration, "_load_project_heights", lambda name: REAL)
    align_model_heights(model)
    for s in model.curriculum.stages:
        assert s.command.targetBodyHeight == -0.0417
        assert s.termination.fallBaseHeightThreshold == -0.1417
    assert model.termination.fallBaseHeightThreshold == -0.1417


def test_align_falls_back_to_placeholder_without_project_policy(monkeypatch):
    monkeypatch.setattr(migration, "_load_project_heights", lambda name: None)
    model = _model_with_applied_curriculum()
    align_model_heights(model)
    # Still self-consistent (fall = target - margin), just using the placeholder.
    for s in model.curriculum.stages:
        target = s.command.targetBodyHeight
        assert s.termination.fallBaseHeightThreshold == fall_threshold_for_target(target)
