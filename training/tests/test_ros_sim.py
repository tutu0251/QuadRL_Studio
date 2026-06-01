"""Unit tests for ROS sim backend lifecycle (no live Gazebo)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from quadrl_env import ros_sim as rs


@pytest.fixture(autouse=True)
def _reset_ros_sim_globals() -> None:
    rs._rclpy_refcount = 0
    rs._gazebo_refcount = 0
    rs._shared_launch_proc = None
    yield
    rs._rclpy_refcount = 0
    rs._gazebo_refcount = 0
    rs._shared_launch_proc = None


def test_ensure_rclpy_initialized_only_inits_once() -> None:
    mock_rclpy = MagicMock()
    mock_rclpy.ok.side_effect = [False, True, True]

    with patch.dict("sys.modules", {"rclpy": mock_rclpy}):
        rs._ensure_rclpy_initialized()
        rs._ensure_rclpy_initialized()

    mock_rclpy.init.assert_called_once()
    assert rs._rclpy_refcount == 2


def test_release_rclpy_shutdown_when_last_user() -> None:
    mock_rclpy = MagicMock()
    mock_rclpy.ok.return_value = True

    with patch.dict("sys.modules", {"rclpy": mock_rclpy}):
        rs._rclpy_refcount = 1
        rs._release_rclpy()

    mock_rclpy.shutdown.assert_called_once()
    assert rs._rclpy_refcount == 0
