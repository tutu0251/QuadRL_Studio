"""Tests for export scanner."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage import export_scanner, project_storage


@pytest.fixture
def sample_project(tmp_path, monkeypatch):
    name = "test_robot"
    root = tmp_path / name
    exports = root / "exports"
    exports.mkdir(parents=True)
    (exports / f"rl_{name}_config.yaml").write_text("algorithm: PPO\n")
    (exports / f"ppo_{name}_config.yaml").write_text("hyperparameters: {}\n")
    (exports / f"geo_{name}.urdf").write_text("<robot/>")
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    return name


def test_scan_exports_categorizes_files(sample_project):
    bundle = export_scanner.scan_exports(sample_project)
    assert bundle.ready_for_training is True
    categories = {f.category for f in bundle.files}
    assert "geometry" in categories
    assert "rl_trainer" in categories
    assert "ppo_planner" in categories


def test_scan_exports_missing_required(tmp_path, monkeypatch):
    name = "incomplete"
    root = tmp_path / name / "exports"
    root.mkdir(parents=True)
    (root / f"geo_{name}.urdf").write_text("<robot/>")
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    bundle = export_scanner.scan_exports(name)
    assert bundle.ready_for_training is False
    assert len(bundle.missing_required) == 2


def test_read_export_text(sample_project):
    content = export_scanner.read_export_text(sample_project, f"exports/rl_{sample_project}_config.yaml")
    assert "PPO" in content
