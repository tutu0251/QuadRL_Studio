"""Tests for command_builder."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.command_builder import build_train_command, preview_command


def test_train_start_command_includes_script():
    cmd = build_train_command("demo_bot", dry_run=True, gazebo_headless=True, controller_apply_delay_s=30)
    assert "run_rl_train.py" in cmd
    assert "QUADRL_SIM_WARMUP_S=30" in cmd
    assert "--dry-run" in cmd


def test_preview_workspace_setup():
    out = preview_command("workspace_setup", "mybot")
    assert "setup_robot.sh" in out["command"]
    assert out["action"] == "workspace_setup"


def test_preview_test_spawn_gui():
    out = preview_command("test_spawn", "mybot", {"spawn_z": 0.6, "headless": False})
    assert "ign gazebo -s" not in out["command"]
    assert "DISPLAY=" in out["command"]


def test_preview_test_spawn():
    out = preview_command("test_spawn", "mybot", {"spawn_z": 0.6})
    assert "ros_gz_sim create" in out["command"]
    assert "0.6" in out["command"]


def test_preview_test_spawn_stop():
    out = preview_command("test_spawn_stop", "mybot")
    assert "/spawn/test/stop" in out["command"]
