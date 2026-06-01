"""ROS environment helpers (no live Gazebo)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from quadrl_env.ros_env import ROS_SETUP, load_ros_environ, probe_rclpy_import
from quadrl_env.ros_sim import ros_stack_available


def test_load_ros_environ_includes_pythonpath_when_humble_present() -> None:
    if not ROS_SETUP.is_file():
        return
    env = load_ros_environ()
    assert "rclpy" in (env.get("PYTHONPATH") or "") or any(
        "rclpy" in p for p in (env.get("PYTHONPATH") or "").split(":")
    )


def test_ros_stack_available_false_without_humble() -> None:
    with patch.object(Path, "is_file", return_value=False):
        assert ros_stack_available() is False


def test_probe_rclpy_import_when_humble_present() -> None:
    if not ROS_SETUP.is_file():
        return
    assert probe_rclpy_import() is True
