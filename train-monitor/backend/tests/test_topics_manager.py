"""Tests for topics manager."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.topics_manager import list_topics, update_confirmations
from storage import project_storage


@pytest.fixture
def topics_project(tmp_path, monkeypatch):
    name = "top_bot"
    exports = tmp_path / name / "exports"
    exports.mkdir(parents=True)
    (exports / f"sens_{name}_observations.yaml").write_text(
        "observations:\n  imu:\n    kind: imu\n    topic: /imu/data\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(project_storage, "PROJECTS_ROOT", tmp_path)
    return name


def test_list_topics_static(topics_project):
    bundle = list_topics(topics_project)
    assert len(bundle.topics) == 1
    assert bundle.topics[0].topic == "/imu/data"
    assert bundle.topics[0].runtime_status == "pending"


def test_confirm_topics(topics_project):
    bundle, cmd = update_confirmations(topics_project, ["/imu/data"])
    assert "/imu/data" in bundle.confirmed_topics
    assert "topics/confirmations" in cmd
