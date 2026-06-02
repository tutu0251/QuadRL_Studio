"""Reset Gazebo robot pose and joints to exported default pose."""
from __future__ import annotations

import time
from typing import Any

import numpy as np


def reset_gazebo_robot(
    node: Any,
    *,
    world_name: str,
    entity_name: str,
    spawn: dict[str, float],
    joint_names: list[str],
    joint_positions: np.ndarray,
    jtc_pub: Any,
    joint_trajectory_msg_cls: Any,
    joint_trajectory_point_cls: Any,
    control_dt: float,
    settle_steps: int = 8,
) -> None:
    """Teleport model and command default joint positions."""
    _set_entity_pose(node, world_name=world_name, entity_name=entity_name, spawn=spawn)
    _command_joint_positions(
        jtc_pub,
        joint_names=joint_names,
        positions=joint_positions,
        joint_trajectory_msg_cls=joint_trajectory_msg_cls,
        joint_trajectory_point_cls=joint_trajectory_point_cls,
        control_dt=control_dt,
        settle_steps=settle_steps,
    )


def _set_entity_pose(
    node: Any,
    *,
    world_name: str,
    entity_name: str,
    spawn: dict[str, float],
) -> None:
    try:
        from geometry_msgs.msg import Pose
        from ros_gz_interfaces.msg import Entity
        from ros_gz_interfaces.srv import SetEntityPose
    except ImportError:
        return

    service = f"/world/{world_name}/set_pose"
    client = node.create_client(SetEntityPose, service)
    if not client.wait_for_service(timeout_sec=2.0):
        node.get_logger().warning(f"Gazebo reset: service unavailable: {service}")
        return

    req = SetEntityPose.Request()
    req.entity = Entity()
    req.entity.name = entity_name
    req.entity.type = Entity.MODEL
    req.pose = Pose()
    req.pose.position.x = float(spawn.get("x", 0.0))
    req.pose.position.y = float(spawn.get("y", 0.0))
    req.pose.position.z = float(spawn.get("z", 0.5))
    roll = float(spawn.get("roll", 0.0))
    pitch = float(spawn.get("pitch", 0.0))
    yaw = float(spawn.get("yaw", 0.0))
    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)
    req.pose.orientation.w = cr * cp * cy + sr * sp * sy
    req.pose.orientation.x = sr * cp * cy - cr * sp * sy
    req.pose.orientation.y = cr * sp * cy + sr * cp * sy
    req.pose.orientation.z = cr * cp * sy - sr * sp * cy

    future = client.call_async(req)
    _spin_until_done(node, future, timeout_sec=3.0)


def _command_joint_positions(
    jtc_pub: Any,
    *,
    joint_names: list[str],
    positions: np.ndarray,
    joint_trajectory_msg_cls: Any,
    joint_trajectory_point_cls: Any,
    control_dt: float,
    settle_steps: int,
) -> None:
    try:
        import rclpy
    except ImportError:
        rclpy = None
    for _ in range(max(1, settle_steps)):
        if rclpy is not None and not rclpy.ok():
            return
        msg = joint_trajectory_msg_cls()
        msg.joint_names = list(joint_names)
        point = joint_trajectory_point_cls()
        point.positions = [float(p) for p in positions]
        point.time_from_start.sec = 0
        point.time_from_start.nanosec = int(max(control_dt, 0.02) * 1e9)
        msg.points = [point]
        try:
            jtc_pub.publish(msg)
        except Exception:
            return
        time.sleep(max(control_dt, 0.02))


def apply_ros_wrench(
    node: Any,
    *,
    world_name: str,
    entity_name: str,
    force: np.ndarray,
    torque: np.ndarray,
) -> None:
    try:
        from ros_gz_interfaces.msg import Entity, EntityWrench
        from ros_gz_interfaces.srv import ApplyEntityWrench
    except ImportError:
        return

    service = f"/world/{world_name}/wrench"
    client = node.create_client(ApplyEntityWrench, service)
    if not client.wait_for_service(timeout_sec=0.05):
        return

    req = ApplyEntityWrench.Request()
    req.entity = Entity()
    req.entity.name = entity_name
    req.entity.type = Entity.MODEL
    req.wrench = EntityWrench()
    req.wrench.force.x = float(force[0])
    req.wrench.force.y = float(force[1])
    req.wrench.force.z = float(force[2])
    req.wrench.torque.x = float(torque[0])
    req.wrench.torque.y = float(torque[1])
    req.wrench.torque.z = float(torque[2])
    req.duration.sec = 0
    req.duration.nanosec = int(0.05 * 1e9)
    _ = client.call_async(req)


def _spin_until_done(node: Any, future: Any, *, timeout_sec: float) -> None:
    deadline = time.time() + timeout_sec
    while not future.done() and time.time() < deadline:
        time.sleep(0.02)
