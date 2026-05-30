"""Tests for RL YAML export."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.trainer_core import TrainerCore
from exporter.rl_yaml_exporter import export_rl_yaml
from storage import project_storage


def test_export_contains_required_keys(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "mybot"
        (root / "exports").mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        model = TrainerCore.bootstrap_project("mybot")
        model.projectName = "mybot"
        path = export_rl_yaml(model, "mybot")
        assert path.exists()
        text = path.read_text()
        assert "mybot" in text
        yaml_body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
        doc = yaml.safe_load(yaml_body)
        assert doc["algorithm"] == "PPO"
        assert doc["framework"] == "stable_baselines3"
        assert "hyperparameters" in doc
        assert "parallel" in doc
        assert "task" in doc
        assert doc["logging"]["tensorboard_root"] == "runs"
        assert doc["env"]["observations_file"] == "sens_mybot_observations.yaml"
