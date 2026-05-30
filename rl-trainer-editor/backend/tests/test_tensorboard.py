"""Tests for TensorBoard helpers."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage import project_storage
from training.train_manager import runs_dir, tensorboard_info, tensorboard_url


def test_tensorboard_url():
    assert tensorboard_url("192.168.1.10", 6006) == "http://192.168.1.10:6006"
    assert tensorboard_url("localhost") == "http://localhost:6006"


def test_tensorboard_info_empty_project(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")
        info = tensorboard_info("mybot", url_host="10.0.0.5", port=6006)
        assert info["project"] == "mybot"
        assert info["logdir"].endswith("projects/mybot/runs")
        assert info["latest_run"] is None
        assert "--bind_all" in info["command"]
        assert info["url"] == "http://10.0.0.5:6006"
        assert info["bind_host"] == "0.0.0.0"


def test_tensorboard_info_latest_run(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects" / "mybot" / "runs"
        (root / "20260101_120000").mkdir(parents=True)
        (root / "20260102_120000").mkdir(parents=True)
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")
        info = tensorboard_info("mybot")
        assert info["latest_run"].endswith("20260102_120000")


def test_runs_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(project_storage, "PROJECTS_ROOT", Path(tmp) / "projects")
        assert runs_dir("demo").name == "runs"
