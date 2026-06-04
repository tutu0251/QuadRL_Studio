"""Tests for shared Gazebo launch reuse across acquire/close."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from quadrl_env import ros_sim as rs
from quadrl_env.project_config import ProjectArtifacts


@pytest.fixture(autouse=True)
def _reset_ros_sim_globals() -> None:
    rs._rclpy_refcount = 0
    rs._gazebo_refcount = 0
    rs._shared_launch_proc = None
    rs._bootstrap_done = False
    yield
    rs._rclpy_refcount = 0
    rs._gazebo_refcount = 0
    rs._shared_launch_proc = None
    rs._bootstrap_done = False


def _fake_artifacts() -> ProjectArtifacts:
    return ProjectArtifacts(
        project_dir=__import__("pathlib").Path("/tmp/demo"),
        project_name="demo",
        rl_config={},
        observations_doc={},
        controllers_doc={},
        gains_doc={},
        joint_names=["j0"],
        joint_gains={},
        workspace_setup=__import__("pathlib").Path("/tmp/demo/workspace/install/setup.bash"),
        bringup_pkg="demo_bringup",
    )


def test_acquire_reuses_launch_without_second_popen() -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    artifacts = _fake_artifacts()

    with (
        patch.object(rs.subprocess, "Popen", return_value=proc) as popen,
        patch.object(rs, "build_sim_launch_command", return_value="ros2 launch demo_bringup sim.launch.py"),
        patch.object(rs, "run_gazebo_bootstrap", return_value=(True, "")),
        patch.object(rs, "load_ros_environ", return_value={}),
    ):
        rs._acquire_gazebo(artifacts)
        rs._acquire_gazebo(artifacts)

    popen.assert_called_once()


def test_release_keeps_launch_when_quardrl_keep_gazebo() -> None:
    proc = MagicMock()
    proc.poll.return_value = None
    rs._shared_launch_proc = proc
    rs._gazebo_refcount = 1

    with patch.dict(os.environ, {"QUADRL_KEEP_GAZEBO": "1"}):
        rs._release_gazebo()

    assert rs._shared_launch_proc is proc
    assert rs._gazebo_refcount == 0
