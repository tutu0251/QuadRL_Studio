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

    # Service name depends on Gazebo world name and bridge/plugin configuration.
    # We try the configured world first, then fall back to any discovered `/world/*/set_pose`.
    preferred_service = f"/world/{world_name}/set_pose"

    candidate_services: list[str] = [preferred_service]
    discovered_typed: set[str] = set()
    try:
        for name, types in node.get_service_names_and_types():
            if name.endswith("/set_pose") and "ros_gz_interfaces/srv/SetEntityPose" in types:
                candidate_services.append(name)
                discovered_typed.add(name)
    except Exception:
        pass

    # Give Gazebo/ros_gz bridge some time to advertise services on startup.
    chosen_service: str | None = None
    client = None
    deadline = time.time() + 12.0
    services = list(dict.fromkeys(candidate_services))
    while time.time() < deadline and chosen_service is None:
        for service in services:
            c = node.create_client(SetEntityPose, service)
            if c.wait_for_service(timeout_sec=0.5 if service != preferred_service else 1.0):
                chosen_service = service
                client = c
                break
        if chosen_service is None:
            time.sleep(0.1)

    # Some ROS setups can momentarily report the service name in the graph while
    # `wait_for_service()` stays false. If we can see a correctly-typed service
    # in the graph, proceed anyway and let the request timeout naturally.
    if (chosen_service is None or client is None) and discovered_typed:
        fallback = preferred_service if preferred_service in discovered_typed else sorted(discovered_typed)[0]
        client = node.create_client(SetEntityPose, fallback)
        chosen_service = fallback

    if chosen_service is None or client is None:
        visible = []
        try:
            for name, types in node.get_service_names_and_types():
                if name.startswith("/world/") and name.endswith("/set_pose"):
                    visible.append(name)
        except Exception:
            pass
        if visible:
            node.get_logger().warning(
                f"Gazebo reset: service unavailable: {preferred_service} (visible: {sorted(set(visible))})"
            )
        else:
            node.get_logger().warning(f"Gazebo reset: service unavailable: {preferred_service}")
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
    if not _wait_for_service_response(node, future, timeout_sec=3.0):
        node.get_logger().warning(
            f"Gazebo reset: set_pose call timed out on {chosen_service} (entity={entity_name})"
        )


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

    preferred_service = f"/world/{world_name}/wrench"
    candidate_services: list[str] = [preferred_service]
    try:
        for name, types in node.get_service_names_and_types():
            if name.endswith("/wrench") and "ros_gz_interfaces/srv/ApplyEntityWrench" in types:
                candidate_services.append(name)
    except Exception:
        pass

    client = None
    for service in dict.fromkeys(candidate_services):
        c = node.create_client(ApplyEntityWrench, service)
        if c.wait_for_service(timeout_sec=0.02 if service != preferred_service else 0.05):
            client = c
            break
    if client is None:
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


def _wait_for_service_response(node: Any, future: Any, *, timeout_sec: float) -> bool:
    """Wait for an async service future; requires the node's executor to be spinning."""
    try:
        import rclpy
        from rclpy.task import Future

        if not isinstance(future, Future):
            return False
        rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_sec)
        return future.done() and not future.cancelled()
    except Exception:
        deadline = time.time() + timeout_sec
        while not future.done() and time.time() < deadline:
            time.sleep(0.02)
        return bool(future.done())
