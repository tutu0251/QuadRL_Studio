#!/usr/bin/env python3
"""Apply spawn pose + default joint positions via ros2_control (workspace sim)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAINING_DIR = REPO_ROOT / "training"
sys.path.insert(0, str(TRAINING_DIR))

import rclpy  # noqa: E402
from quadrl_env.gazebo_reset import reset_gazebo_robot  # noqa: E402
from quadrl_env.project_config import load_project_artifacts  # noqa: E402
from quadrl_env.ros_sim import _default_joint_positions  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402
from rclpy.node import Node  # noqa: E402


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: apply_spawn_reset.py PROJECT_DIR WORLD ENTITY", file=sys.stderr)
        return 2
    project_dir = Path(sys.argv[1]).resolve()
    world_name = sys.argv[2]
    entity_name = sys.argv[3]
    spawn_json = os.environ.get("QUADRL_SPAWN_POSE_JSON", "")
    if not spawn_json:
        print("QUADRL_SPAWN_POSE_JSON env required", file=sys.stderr)
        return 2
    spawn = json.loads(spawn_json)

    artifacts = load_project_artifacts(project_dir)
    if artifacts.workspace_setup is None:
        print("workspace not built", file=sys.stderr)
        return 1

    joint_positions = _default_joint_positions(artifacts)

    rclpy.init()
    node = Node("tm_apply_spawn_reset")
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    def wait_future(future, *, timeout_sec: float) -> bool:
        deadline = time.time() + timeout_sec
        while not future.done() and time.time() < deadline:
            executor.spin_once(timeout_sec=0.05)
        return bool(future.done() and not future.cancelled())

    try:
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

        jtc_pub = node.create_publisher(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
            10,
        )
        deadline = time.time() + 2.0
        while time.time() < deadline and jtc_pub.get_subscription_count() < 1:
            executor.spin_once(timeout_sec=0.05)

        reset_gazebo_robot(
            node,
            world_name=world_name,
            entity_name=entity_name,
            spawn=spawn,
            joint_names=list(artifacts.joint_names),
            joint_positions=joint_positions,
            jtc_pub=jtc_pub,
            joint_trajectory_msg_cls=JointTrajectory,
            joint_trajectory_point_cls=JointTrajectoryPoint,
            control_dt=artifacts.control_dt,
            wait_future=wait_future,
        )
        settle_deadline = time.time() + max(artifacts.control_dt * 8, 0.5)
        while time.time() < settle_deadline:
            executor.spin_once(timeout_sec=0.05)
    finally:
        executor.remove_node(node)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
