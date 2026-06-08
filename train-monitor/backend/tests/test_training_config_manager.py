"""Tests for training config manager."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.training_config_manager import get_training_config, update_training_config
from domain.models import ActionScaleEntry, ObservationScaleEntry, TrainingConfigUpdate
from storage import project_storage


@pytest.fixture
def train_cfg_project(tmp_path, monkeypatch):
    name = "tc_bot"
    exports = tmp_path / name / "exports"
    exports.mkdir(parents=True)
    (exports / f"ctrl_{name}_gains.yaml").write_text(
        "joints:\n  j1:\n    action_scale: 0.2\n    default_position: 0.0\n",
        encoding="utf-8",
    )
    rl = {
        "observations": {
            "terms": [
                {
                    "id": "obs1",
                    "key": "imu",
                    "topic": "/imu",
                    "scale": 1.0,
                    "offset": 0.0,
                    "enabled": True,
                }
            ]
        },
        "task": {"termination": {"max_episode_steps": 500, "termination_terms": []}},
    }
    (exports / f"rl_{name}_config.yaml").write_text(yaml.dump(rl), encoding="utf-8")
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    return name


def test_get_training_config(train_cfg_project):
    cfg = get_training_config(train_cfg_project)
    assert cfg.action_scales[0].action_scale == pytest.approx(0.2)
    assert cfg.observation_scales[0].key == "imu"


@pytest.fixture
def curriculum_cfg_project(tmp_path, monkeypatch):
    name = "curr_bot"
    exports = tmp_path / name / "exports"
    exports.mkdir(parents=True)
    (exports / f"ctrl_{name}_gains.yaml").write_text("joints: {}\n", encoding="utf-8")
    rl = {
        "observations": {"terms": []},
        "curriculum": {
            "enabled": True,
            "stages": [
                {"id": "walk", "name": "Walk", "termination": {"max_episode_steps": 500}},
                # Second stage intentionally has no termination block — it must still
                # appear in stages so the UI index maps to the script's stage index.
                {"id": "walk_fast", "name": "Walk fast"},
                {"id": "turn", "name": "Turn", "termination": {"max_episode_steps": 800}},
            ],
        },
    }
    (exports / f"rl_{name}_config.yaml").write_text(yaml.dump(rl), encoding="utf-8")
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    return name


def test_curriculum_stages_populated_in_order(curriculum_cfg_project):
    cfg = get_training_config(curriculum_cfg_project)
    assert cfg.curriculum_enabled is True
    assert [(s.order, s.id, s.name) for s in cfg.stages] == [
        (0, "walk", "Walk"),
        (1, "walk_fast", "Walk fast"),
        (2, "turn", "Turn"),
    ]
    # Stage without a termination block is omitted from terminations but kept in stages.
    assert len(cfg.terminations) == 2


def test_no_curriculum_has_empty_stages(train_cfg_project):
    cfg = get_training_config(train_cfg_project)
    assert cfg.curriculum_enabled is False
    assert cfg.stages == []


def test_patch_action_scale(train_cfg_project):
    cfg, cmd = update_training_config(
        train_cfg_project,
        TrainingConfigUpdate(action_scales=[ActionScaleEntry(joint="j1", action_scale=0.35, default_position=0.0)]),
    )
    assert cfg.action_scales[0].action_scale == pytest.approx(0.35)
    assert "training-config" in cmd
    text = (project_storage.exports_dir(train_cfg_project) / f"ctrl_{train_cfg_project}_gains.yaml").read_text()
    assert "0.35" in text
