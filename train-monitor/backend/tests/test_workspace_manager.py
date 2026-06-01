"""Tests for workspace status API helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.workspace_manager import get_workspace_status
from storage import project_storage


@pytest.fixture
def sample_project(tmp_path, monkeypatch):
    name = "ws_bot"
    root = tmp_path / name
    exports = root / "exports"
    exports.mkdir(parents=True)
    (exports / f"ctrl_{name}_controllers.yaml").write_text(
        "joint_trajectory_controller:\n  ros__parameters:\n    joints: [j1]\n",
        encoding="utf-8",
    )
    (exports / f"ctrl_{name}_gains.yaml").write_text("joints:\n  j1:\n    action_scale: 0.2\n", encoding="utf-8")
    (exports / f"sens_{name}_observations.yaml").write_text("observations: {}\n", encoding="utf-8")
    (exports / f"rl_{name}_config.yaml").write_text("algorithm: PPO\n", encoding="utf-8")
    (exports / f"ppo_{name}_config.yaml").write_text("hyperparameters: {}\n", encoding="utf-8")
    ws = root / "workspace" / "install"
    ws.mkdir(parents=True)
    (ws / "setup.bash").write_text("# mock\n", encoding="utf-8")
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    return name


def test_workspace_status_build_ready(sample_project):
    status = get_workspace_status(sample_project)
    assert status.build_ready is True
    assert status.sensor_exports_ready is True
    assert status.recommended_sim_backend == "ros"
