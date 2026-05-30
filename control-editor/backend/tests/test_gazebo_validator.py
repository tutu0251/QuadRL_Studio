"""Tests for Gazebo export validation."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from validator.gazebo_validator import (
    GazeboExportValidator,
    _analyze_logs,
    _sim_env,
    check_gazebo_stack,
    validate_gazebo_export,
)


def test_sim_env_sets_plugin_and_library_paths():
    env = _sim_env()
    ros_lib = "/opt/ros/humble/lib"
    assert env["GZ_SIM_SYSTEM_PLUGIN_PATH"].startswith(ros_lib)
    assert ros_lib in env.get("LD_LIBRARY_PATH", "").split(":")


def test_analyze_logs_passes_on_successful_spawn_and_plugin():
    gz_log = "[INFO] [GazeboSimROS2ControlPlugin]: robot_param_node is robot_description"
    spawn_log = "[INFO] [ros_gz_sim]: OK creation of entity."
    errors, warnings = _analyze_logs(gz_log, spawn_log, spawn_rc=0)
    assert not errors
    assert not warnings


def test_analyze_logs_warns_without_robot_state_publisher():
    gz_log = "[ERROR] [gz_ros2_control]: robot_state_publisher service not available, waiting again..."
    spawn_log = "[INFO] [ros_gz_sim]: OK creation of entity."
    errors, warnings = _analyze_logs(gz_log, spawn_log, spawn_rc=0)
    assert not errors
    assert any(w.code == "gazebo_no_robot_state_publisher" for w in warnings)


def test_analyze_logs_fails_on_plugin_load_error():
    gz_log = "[Err] Failed to load system plugin [libgz_ros2_control-system.so]"
    spawn_log = "[INFO] [ros_gz_sim]: OK creation of entity."
    errors, warnings = _analyze_logs(gz_log, spawn_log, spawn_rc=0)
    assert any(e.code == "gazebo_plugin_load_failed" for e in errors)


def test_analyze_logs_fails_on_spawn_error():
    gz_log = ""
    spawn_log = "[ERROR] [ros_gz_sim]: Must specify either -file, -param, -stdin or -topic"
    errors, warnings = _analyze_logs(gz_log, spawn_log, spawn_rc=255)
    assert any(e.code == "gazebo_spawn_failed" for e in errors)


def test_validate_skipped_when_stack_unavailable(tmp_path: Path):
    urdf = tmp_path / "ctrl_test_ros2_control.urdf"
    urdf.write_text("<robot name='t'/>")
    with patch("validator.gazebo_validator.check_gazebo_stack", return_value={"available": False, "missing": ["ign"]}):
        result = validate_gazebo_export(urdf, "test")
    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "skipped"
    assert any(w.code == "gazebo_validation_skipped" for w in result.warnings)


def test_validate_fails_when_urdf_missing(tmp_path: Path):
    urdf = tmp_path / "missing.urdf"
    with patch("validator.gazebo_validator.check_gazebo_stack", return_value={"available": True, "createPackage": "ros_gz_sim"}):
        result = validate_gazebo_export(urdf, "test")
    assert not result.valid
    assert any(e.code == "missing_urdf_file" for e in result.errors)


def test_gazebo_validator_end_to_end_mocked(tmp_path: Path):
    urdf = tmp_path / "ctrl_bot_ros2_control.urdf"
    urdf.write_text("<robot name='bot'/>")

    def fake_popen(cmd, **kwargs):
        proc = MagicMock()
        proc.poll.return_value = None
        proc.returncode = 0
        proc.stdout = None
        proc.terminate = MagicMock()
        proc.wait = MagicMock()
        proc.kill = MagicMock()
        return proc

    stack = {"available": True, "createPackage": "ros_gz_sim", "missing": []}
    spawn_result = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="[INFO] [ros_gz_sim]: OK creation of entity.\n",
        stderr="",
    )

    with (
        patch("validator.gazebo_validator.check_gazebo_stack", return_value=stack),
        patch("validator.gazebo_validator.subprocess.Popen", side_effect=fake_popen),
        patch("validator.gazebo_validator._wait_for_sim", return_value=(True, "")),
        patch("validator.gazebo_validator._bash_ros_cmd", return_value=spawn_result),
        patch("validator.gazebo_validator._stop_process"),
        patch("pathlib.Path.read_text", return_value="[INFO] [GazeboSimROS2ControlPlugin]: loaded\n"),
        patch("pathlib.Path.is_file", return_value=True),
        patch("pathlib.Path.unlink"),
    ):
        result = GazeboExportValidator(urdf, "bot").validate()

    assert result.valid
    assert result.details is not None
    assert result.details["status"] == "passed"


@pytest.mark.integration
def test_gazebo_validator_live_if_available():
    if not check_gazebo_stack().get("available"):
        pytest.skip("Gazebo stack not installed")
    urdf = Path.home() / "quadruped_dev_tool/projects/my_robot/exports/ctrl_my_robot_ros2_control.urdf"
    if not urdf.is_file():
        pytest.skip("No exported URDF for my_robot")
    result = validate_gazebo_export(urdf, "my_robot")
    assert result.details is not None
    assert result.details["status"] in ("passed", "failed")
    if result.details["status"] == "passed":
        assert result.valid
