"""Tests for spawn config manager."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.spawn_config_manager import get_spawn_config, resolve_spawn_create_pose, update_spawn_config
from domain.models import SpawnConfigUpdate, SpawnOffset
from storage import project_storage


@pytest.fixture
def pose_project(tmp_path, monkeypatch):
    name = "spawn_bot"
    exports = tmp_path / name / "exports"
    exports.mkdir(parents=True)
    (exports / f"geo_{name}_default_pose.yaml").write_text(
        "name: Stand\nspawn:\n  x: 0\n  y: 0\n  z: 0.5\n  roll: 0\n  pitch: 0\n  yaw: 0\njoints:\n  j1: 0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    return name


def test_get_spawn_config(pose_project):
    cfg = get_spawn_config(pose_project)
    assert cfg.joints["j1"] == pytest.approx(0.1)
    assert cfg.effective_spawn["z"] == pytest.approx(0.5)


def test_update_spawn_offset(pose_project):
    cfg, _ = update_spawn_config(
        pose_project,
        SpawnConfigUpdate(spawn_offset=SpawnOffset(dz=0.1), controller_apply_delay_s=20, pose_confirmed=True),
    )
    assert cfg.effective_spawn["z"] == pytest.approx(0.6)
    assert cfg.controller_apply_delay_s == pytest.approx(20)
    assert cfg.pose_confirmed is True


def test_resolve_spawn_create_pose_uses_effective_spawn(pose_project):
    cfg, _ = update_spawn_config(
        pose_project,
        SpawnConfigUpdate(spawn_offset=SpawnOffset(dx=0.1, dy=-0.2, dz=0.05, dyaw=0.3)),
    )
    pose = resolve_spawn_create_pose(cfg)
    assert pose["x"] == pytest.approx(0.1)
    assert pose["y"] == pytest.approx(-0.2)
    assert pose["z"] == pytest.approx(0.55)
    assert pose["yaw"] == pytest.approx(0.3)
