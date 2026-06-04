"""Tests for apply_spawn_reset script path setup."""
from __future__ import annotations

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_spawn_reset.py"


def test_apply_spawn_reset_training_dir_is_repo_training():
    training = SCRIPT.resolve().parents[3] / "training"
    assert (training / "quadrl_env").is_dir()


def test_apply_spawn_reset_reads_pose_from_os_environ():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "os.environ.get(\"QUADRL_SPAWN_POSE_JSON\"" in source
    assert "sys.environ.get(\"QUADRL_SPAWN_POSE_JSON\"" not in source


def test_apply_spawn_reset_spins_executor():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "SingleThreadedExecutor" in source
    assert "executor.spin_once" in source
    assert "wait_future=wait_future" in source
