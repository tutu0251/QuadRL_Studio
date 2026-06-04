"""Tests for spawn test command builder."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.command_builder import build_spawn_test_stop_command, build_test_spawn_command

FAKE_SETUP = Path("/tmp/fake_ws/install/setup.bash")


@patch("api.spawn_workspace_session.require_workspace_setup", return_value=FAKE_SETUP)
def test_build_test_spawn_command_gui(_mock_setup):
    cmd = build_test_spawn_command(
        "demo",
        spawn_pose={"x": 0.1, "y": 0.0, "z": 0.55, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        headless=False,
    )
    assert "sim.launch.py headless:=false" in cmd
    assert "apply_spawn_reset.py" in cmd
    assert "0.55" in cmd
    assert "ign gazebo" not in cmd


@patch("api.spawn_workspace_session.require_workspace_setup", return_value=FAKE_SETUP)
def test_build_test_spawn_command(_mock_setup):
    cmd = build_test_spawn_command(
        "demo",
        spawn_pose={"x": 0.0, "y": 0.0, "z": 0.55, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
    )
    assert "sim.launch.py headless:=true" in cmd
    assert "apply_spawn_reset.py" in cmd
    assert "flat" in cmd
    assert "list_controllers" in cmd


def test_build_spawn_test_stop_command():
    cmd = build_spawn_test_stop_command("demo")
    assert "/spawn/test/stop" in cmd
    assert "demo" in cmd
