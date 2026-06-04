"""Tests for command_builder."""
from __future__ import annotations

import sys
from pathlib import Path

from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.command_builder import build_train_command, preview_command

FAKE_SETUP = Path("/tmp/fake_ws/install/setup.bash")


def test_train_start_command_includes_script():
    cmd = build_train_command("demo_bot", dry_run=True, gazebo_headless=True, controller_apply_delay_s=30)
    assert "run_rl_train.py" in cmd
    assert "QUADRL_SIM_WARMUP_S=30" in cmd
    assert "--dry-run" in cmd


def test_preview_workspace_setup():
    out = preview_command("workspace_setup", "mybot")
    assert "setup_robot.sh" in out["command"]
    assert out["action"] == "workspace_setup"


@patch("api.spawn_workspace_session.require_workspace_setup", return_value=FAKE_SETUP)
def test_preview_test_spawn_gui(_mock_setup):
    out = preview_command("test_spawn", "mybot", {"spawn_z": 0.6, "headless": False})
    assert "sim.launch.py headless:=false" in out["command"]
    assert "apply_spawn_reset.py" in out["command"]


@patch("api.spawn_workspace_session.require_workspace_setup", return_value=FAKE_SETUP)
def test_preview_test_spawn(_mock_setup):
    out = preview_command("test_spawn", "mybot", {"spawn_z": 0.6})
    assert "sim.launch.py headless:=true" in out["command"]
    assert "apply_spawn_reset.py" in out["command"]


def test_preview_test_spawn_stop():
    out = preview_command("test_spawn_stop", "mybot")
    assert "/spawn/test/stop" in out["command"]
