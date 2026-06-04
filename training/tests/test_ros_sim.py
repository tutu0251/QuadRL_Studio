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
    rs._ros_executor = None
    rs._ros_spin_thread = None
    rs._ros_executor_nodes = 0
    rs._bootstrap_done = False
    yield
    rs._rclpy_refcount = 0
    rs._gazebo_refcount = 0
    rs._shared_launch_proc = None
    rs._ros_executor = None
    rs._ros_spin_thread = None
    rs._ros_executor_nodes = 0
    rs._bootstrap_done = False


def test_ensure_rclpy_initialized_only_inits_once() -> None:
    mock_rclpy = MagicMock()
    mock_rclpy.ok.side_effect = [False, True, True]

    with patch.dict("sys.modules", {"rclpy": mock_rclpy}):
        rs._ensure_rclpy_initialized()
        rs._ensure_rclpy_initialized()

    mock_rclpy.init.assert_called_once()
    assert rs._rclpy_refcount == 2


def test_register_ros_node_uses_single_executor() -> None:
    mock_node_a = MagicMock()
    mock_node_b = MagicMock()
    mock_executor = MagicMock()
    mock_executors = MagicMock()
    mock_executors.SingleThreadedExecutor.return_value = mock_executor

    with patch.dict("sys.modules", {"rclpy": MagicMock(), "rclpy.executors": mock_executors}):
        rs._register_ros_node(mock_node_a)
        rs._register_ros_node(mock_node_b)

    mock_executor.add_node.assert_any_call(mock_node_a)
    mock_executor.add_node.assert_any_call(mock_node_b)
    assert rs._ros_executor_nodes == 2
    assert rs._ros_spin_thread is not None


def test_release_rclpy_shutdown_when_last_user() -> None:
    mock_rclpy = MagicMock()
    mock_rclpy.ok.return_value = True

    with patch.dict("sys.modules", {"rclpy": mock_rclpy}):
        rs._rclpy_refcount = 1
        rs._release_rclpy()

    mock_rclpy.shutdown.assert_called_once()
    assert rs._rclpy_refcount == 0
