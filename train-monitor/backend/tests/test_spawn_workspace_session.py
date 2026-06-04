"""Tests for workspace spawn session helpers."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.spawn_workspace_session import (
    bringup_package,
    build_sim_launch_command,
    require_workspace_setup,
    wait_for_controller_active,
)


def test_bringup_package_sanitizes_name():
    assert bringup_package("My-Robot") == "my_robot_bringup"


def test_require_workspace_setup_missing():
    with patch("api.spawn_workspace_session.workspace_setup_path") as mock_path:
        fake = MagicMock()
        fake.is_file.return_value = False
        mock_path.return_value = fake
        try:
            require_workspace_setup("demo")
            assert False, "expected FileNotFoundError"
        except FileNotFoundError as exc:
            assert "Workspace not built" in str(exc)


def test_build_sim_launch_command_headless():
    setup = Path("/tmp/proj/workspace/install/setup.bash")
    with patch("api.spawn_workspace_session.require_workspace_setup", return_value=setup):
        cmd = build_sim_launch_command("demo_robot", headless=True)
    assert "sim.launch.py headless:=true" in cmd
    assert "demo_robot_bringup" in cmd
    assert str(setup) in cmd


def test_wait_for_controller_active_success():
    setup = Path("/tmp/setup.bash")
    proc = MagicMock(returncode=0, stdout="joint_state_broadcaster active", stderr="")
    with patch("ev_ros_env.bash_ros_cmd", return_value=proc):
        ok, err = wait_for_controller_active(setup, {}, "joint_state_broadcaster", timeout_s=1, poll_s=0.01)
    assert ok is True
    assert err == ""
