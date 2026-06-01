"""Tests for observation catalog and recommender."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import ObservationTerm, RlTrainerModel, RewardTerm
from planner.observation_catalog import (
    build_observation_catalog,
    merge_observation_terms,
    recommend_observation_terms,
)
from planner.observation_recommender import apply_observation_recommendation
from storage import project_storage


def test_procedural_catalog_always_present(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "bot"
        root.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        catalog = build_observation_catalog("bot")
        procedural = [t for t in catalog if t.source == "procedural"]
        assert len(procedural) == 7
        assert {t.id for t in procedural} == {
            "joint_positions",
            "joint_velocities",
            "last_actions",
            "commands",
            "base_lin_vel",
            "base_ang_vel",
            "projected_gravity",
        }


def test_sensor_catalog_from_sensor_model(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "bot"
        root.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        sensor_doc = {
            "sensors": [
                {
                    "id": "s1",
                    "kind": "imu",
                    "name": "base_imu",
                    "enabled": True,
                    "parentLink": "base_link",
                    "rosTopic": "/bot/imu",
                    "updateRate": 100,
                    "imu": {"enableOrientation": True},
                },
                {
                    "id": "s2",
                    "kind": "contact",
                    "name": "fl_contact",
                    "enabled": False,
                    "parentLink": "fl_foot",
                    "rosTopic": "/bot/fl_contact",
                    "updateRate": 50,
                },
            ]
        }
        (root / "sensor_model.json").write_text(json.dumps(sensor_doc))

        catalog = build_observation_catalog("bot")
        sensors = [t for t in catalog if t.source == "sensor"]
        assert len(sensors) == 2
        imu = next(t for t in sensors if t.kind == "imu")
        contact = next(t for t in sensors if t.kind == "contact")
        assert imu.available is True
        assert contact.available is False
        assert "orientation" in imu.fields


def test_merge_preserves_enabled_flags(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "bot"
        root.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        existing = [
            ObservationTerm(
                id="joint_positions",
                source="procedural",
                kind="joint_state",
                category="state",
                label="Joint positions",
                enabled=True,
                available=True,
                key="joint_positions",
            )
        ]
        merged = merge_observation_terms(existing, "bot")
        jp = next(t for t in merged if t.id == "joint_positions")
        assert jp.enabled is True
        assert len(merged) >= 7


def test_recommend_enables_velocity_and_contact(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "bot"
        root.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        terms = build_observation_catalog("bot")
        terms.append(
            ObservationTerm(
                id="sensor:fl",
                source="sensor",
                kind="contact",
                category="sensor",
                label="fl_contact",
                enabled=False,
                available=True,
                key="fl_contact",
            )
        )
        recommended, notes = recommend_observation_terms(
            terms,
            reward_categories={"velocity", "contact", "orientation"},
        )
        enabled_ids = {t.id for t in recommended if t.enabled}
        assert "joint_positions" in enabled_ids
        assert "base_lin_vel" in enabled_ids
        assert "projected_gravity" in enabled_ids
        assert "sensor:fl" in enabled_ids
        assert notes


def test_apply_observation_recommendation_on_model(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "bot"
        root.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        model = RlTrainerModel(
            projectName="bot",
            rewardTerms=[
                RewardTerm(id="forward_tracking", type="reward", category="velocity", enabled=True)
            ],
        )
        model, notes = apply_observation_recommendation(model)
        assert model.observationTerms
        assert any(t.enabled for t in model.observationTerms)
        assert notes
