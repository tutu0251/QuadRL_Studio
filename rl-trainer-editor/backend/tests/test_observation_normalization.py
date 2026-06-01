"""Tests for observation normalization defaults."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import ObservationTerm
from planner.observation_normalization import (
    apply_recommended_normalization,
    recommended_normalization,
)


def test_joint_positions_scale():
    term = ObservationTerm(
        id="joint_positions",
        source="procedural",
        kind="joint_state",
        category="state",
        label="Joint positions",
        key="joint_positions",
    )
    d = recommended_normalization(term)
    assert d.scale == 2.0
    assert d.clip_min == -1.0
    assert d.clip_max == 1.0


def test_projected_gravity_no_clip():
    term = ObservationTerm(
        id="projected_gravity",
        source="procedural",
        kind="orientation",
        category="state",
        label="Projected gravity",
        key="projected_gravity",
    )
    d = recommended_normalization(term)
    assert d.clip_min is None
    assert d.clip_max is None


def test_contact_sensor_clip_0_1():
    term = ObservationTerm(
        id="sensor:fl",
        source="sensor",
        kind="contact",
        category="sensor",
        label="fl_contact",
        key="fl_contact",
    )
    apply_recommended_normalization(term)
    assert term.clipMin == 0.0
    assert term.clipMax == 1.0


def test_export_includes_normalization(monkeypatch, tmp_path):
    import yaml
    from domain.trainer_core import TrainerCore
    from exporter.rl_yaml_exporter import export_rl_yaml
    from storage import project_storage

    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    name = "norm_bot"
    project_storage.ensure_project_dirs(name)
    model = TrainerCore.bootstrap_project(name)
    model.projectName = name
    path = export_rl_yaml(model, name)
    text = path.read_text()
    yaml_body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    doc = yaml.safe_load(yaml_body)
    terms = doc["observations"]["terms"]
    assert terms
    jp = next(t for t in terms if t["id"] == "joint_positions")
    assert jp["scale"] == 2.0
    assert jp["clip_min"] == -1.0
    assert jp["clip_max"] == 1.0
