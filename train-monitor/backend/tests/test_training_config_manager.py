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


def test_patch_action_scale(train_cfg_project):
    cfg, cmd = update_training_config(
        train_cfg_project,
        TrainingConfigUpdate(action_scales=[ActionScaleEntry(joint="j1", action_scale=0.35, default_position=0.0)]),
    )
    assert cfg.action_scales[0].action_scale == pytest.approx(0.35)
    assert "training-config" in cmd
    text = (project_storage.exports_dir(train_cfg_project) / f"ctrl_{train_cfg_project}_gains.yaml").read_text()
    assert "0.35" in text
