"""Tests for workspace spawn reset helper."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.spawn_pose_apply import apply_workspace_spawn_reset


def test_apply_workspace_spawn_reset_success():
    proc = MagicMock(returncode=0, stdout="", stderr="")
    with patch("ev_ros_env.bash_ros_cmd", return_value=proc) as mock_cmd:
        ok, err = apply_workspace_spawn_reset(
            "demo",
            spawn={"x": 0.0, "y": 0.0, "z": 0.5, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            env={"ROS_DOMAIN_ID": "0"},
        )
    assert ok is True
    assert err == ""
    call_args = mock_cmd.call_args
    assert "apply_spawn_reset.py" in call_args[0][0]
    assert "QUADRL_SPAWN_POSE_JSON" in call_args[0][0]


def test_apply_workspace_spawn_reset_failure():
    proc = MagicMock(returncode=1, stdout="", stderr="reset failed")
    with patch("ev_ros_env.bash_ros_cmd", return_value=proc):
        ok, err = apply_workspace_spawn_reset(
            "demo",
            spawn={"x": 0.0, "y": 0.0, "z": 0.5, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            env={},
        )
    assert ok is False
    assert "reset failed" in err
