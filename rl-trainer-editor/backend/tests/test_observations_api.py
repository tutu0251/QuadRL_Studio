"""Tests for observations loading from project storage."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import project_storage


def test_load_observations_doc_missing(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "nobot"
        root.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        assert project_storage.load_observations_doc("nobot") is None
        assert project_storage.load_observation_kinds("nobot") == set()
        assert project_storage.load_observations_keys("nobot") == []


def test_load_observations_doc_parsed(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "mybot"
        exports = root / "exports"
        exports.mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")

        doc = {
            "robot_name": "MyBot",
            "topic_prefix": "/mybot",
            "sim_urdf": "sens_mybot_rl.urdf",
            "observations": {
                "base_imu": {
                    "kind": "imu",
                    "topic": "/mybot/imu",
                    "msg_type": "sensor_msgs/Imu",
                    "rate_hz": 100,
                    "parent_link": "base_link",
                    "fields": ["angular_velocity", "orientation"],
                },
                "fl_contact": {
                    "kind": "contact",
                    "topic": "/mybot/fl_contact",
                    "msg_type": "ros_gz_interfaces/Contacts",
                    "rate_hz": 50,
                    "parent_link": "fl_foot",
                    "fields": ["contacts"],
                },
            },
        }
        (exports / "sens_mybot_observations.yaml").write_text(yaml.dump(doc))

        loaded = project_storage.load_observations_doc("mybot")
        assert loaded is not None
        assert loaded["robot_name"] == "MyBot"
        assert set(project_storage.load_observations_keys("mybot")) == {"base_imu", "fl_contact"}
        assert project_storage.load_observation_kinds("mybot") == {"contact", "imu"}
