"""Tests for Gazebo reset helpers (no live Gazebo)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from quadrl_env import gazebo_reset as gr


def test_reset_gazebo_robot_skips_when_rclpy_not_ok() -> None:
    node = MagicMock()
    with patch.object(gr, "_rclpy_ok", return_value=False):
        gr.reset_gazebo_robot(
            node,
            world_name="flat",
            entity_name="robot",
            spawn={"x": 0, "y": 0, "z": 0.5},
            joint_names=["j1"],
            joint_positions=__import__("numpy").zeros(1),
            jtc_pub=MagicMock(),
            joint_trajectory_msg_cls=MagicMock,
            joint_trajectory_point_cls=MagicMock,
            control_dt=0.02,
        )
    node.create_client.assert_not_called()


def test_set_entity_pose_skips_when_rclpy_not_ok() -> None:
    node = MagicMock()
    with patch.object(gr, "_rclpy_ok", return_value=False):
        gr._set_entity_pose(node, world_name="flat", entity_name="robot", spawn={})
    node.create_client.assert_not_called()
