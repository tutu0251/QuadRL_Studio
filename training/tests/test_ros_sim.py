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
    yield
    rs._rclpy_refcount = 0
    rs._gazebo_refcount = 0
    rs._shared_launch_proc = None
    rs._ros_executor = None
    rs._ros_spin_thread = None
    rs._ros_executor_nodes = 0


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("1", True),
        ("false", False),
        ("0", False),
        ("no", False),
    ],
)
def test_gazebo_headless_enabled(monkeypatch, value: str, expected: bool) -> None:
    monkeypatch.setenv("QUADRL_GZ_HEADLESS", value)
    assert rs.gazebo_headless_enabled() is expected


def test_acquire_gazebo_launch_includes_headless_flag(monkeypatch) -> None:
    monkeypatch.setenv("QUADRL_GZ_HEADLESS", "false")
    captured: dict[str, str] = {}

    class FakeProc:
        def poll(self):
            return None

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = " ".join(cmd)
        return FakeProc()

    artifacts = MagicMock()
    artifacts.workspace_setup = "/tmp/ws/install/setup.bash"
    artifacts.bringup_pkg = "demo_bringup"

    with patch.object(rs, "load_ros_environ", return_value={}), patch.object(
        rs.subprocess, "Popen", side_effect=fake_popen
    ), patch.object(rs.time, "sleep"):
        rs._acquire_gazebo(artifacts)

    assert "headless:=false" in captured["cmd"]
