"""ROS 2 + Gazebo sim backend — subscribes to exported observation topics, commands JTC."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from quadrl_env.mock_sim import MockSimBackend
from quadrl_env.project_config import ProjectArtifacts
from quadrl_env.ros_env import ROS_SETUP, load_ros_environ, probe_rclpy_import
from quadrl_env.sim_state import SimState


def ros_stack_available(*, workspace_setup: Path | str | None = None) -> bool:
    if os.environ.get("QUADRL_ROS_ENV_BOOTSTRAPPED") == "1":
        try:
            import rclpy  # noqa: F401
        except ImportError:
            return False
        return True
    return probe_rclpy_import(workspace_setup=workspace_setup)


class RosSimBackend:
    """Wraps a running Gazebo workspace; falls back to mock physics if topics are unavailable."""

    def __init__(self, artifacts: ProjectArtifacts, *, env_id: int = 0) -> None:
        self._artifacts = artifacts
        self._env_id = env_id
        self._mock = MockSimBackend(artifacts, seed=env_id)
        self._launch_proc: subprocess.Popen[str] | None = None
        self._spin_thread: threading.Thread | None = None
        self._latest_joint_pos: np.ndarray | None = None
        self._latest_joint_vel: np.ndarray | None = None
        self._sensor_cache: dict[str, np.ndarray] = {}
        self._node = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        if not self._artifacts.workspace_setup or not self._artifacts.bringup_pkg:
            raise RuntimeError(
                "ROS backend requires built workspace at project/workspace — run workspace-generator setup_robot.sh"
            )
        if not ros_stack_available(workspace_setup=self._artifacts.workspace_setup):
            raise RuntimeError(
                "ROS 2 Humble + rclpy not available — install ros-humble-desktop "
                "(re-run training; the launcher re-execs with ROS sourced automatically)"
            )

        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
        from sensor_msgs.msg import Imu, JointState
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

        rclpy.init(args=None)
        self._node = Node(f"quadrl_train_{self._artifacts.project_name}_{self._env_id}")

        reliable = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        def _joint_cb(msg: JointState) -> None:
            order = self._artifacts.joint_names
            pos = np.zeros(len(order), dtype=np.float32)
            vel = np.zeros(len(order), dtype=np.float32)
            name_to_i = {n: i for i, n in enumerate(order)}
            for i, name in enumerate(msg.name):
                if name in name_to_i:
                    idx = name_to_i[name]
                    if i < len(msg.position):
                        pos[idx] = float(msg.position[i])
                    if i < len(msg.velocity):
                        vel[idx] = float(msg.velocity[i])
            self._latest_joint_pos = pos
            self._latest_joint_vel = vel

        js_topic = os.environ.get("QUADRL_JOINT_STATE_TOPIC", "/joint_states")
        self._node.create_subscription(JointState, js_topic, _joint_cb, 50)

        for key, spec in (self._artifacts.observations_doc.get("observations") or {}).items():
            topic = spec.get("topic")
            kind = (spec.get("kind") or "").lower()
            if not topic:
                continue
            if kind == "imu":

                def _imu_cb(msg: Imu, k=key) -> None:
                    g = np.array(
                        [
                            float(msg.linear_acceleration.x),
                            float(msg.linear_acceleration.y),
                            float(msg.linear_acceleration.z),
                        ],
                        dtype=np.float32,
                    )
                    norm = float(np.linalg.norm(g))
                    if norm > 1e-3:
                        self._sensor_cache[k] = g / norm
                    self._sensor_cache[f"{k}_ang"] = np.array(
                        [
                            float(msg.angular_velocity.x),
                            float(msg.angular_velocity.y),
                            float(msg.angular_velocity.z),
                        ],
                        dtype=np.float32,
                    )

                self._node.create_subscription(Imu, topic, _imu_cb, reliable)

        self._jtc_pub = self._node.create_publisher(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
            10,
        )
        self._JointTrajectory = JointTrajectory
        self._JointTrajectoryPoint = JointTrajectoryPoint

        env = self._ros_env()
        setup = self._artifacts.workspace_setup
        pkg = self._artifacts.bringup_pkg
        launch = (
            f"source /opt/ros/humble/setup.bash && source {setup} && "
            f"ros2 launch {pkg} sim.launch.py headless:=true"
        )
        self._launch_proc = subprocess.Popen(
            ["bash", "-lc", launch],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(float(os.environ.get("QUADRL_SIM_WARMUP_S", "25")))

        self._spin_thread = threading.Thread(target=rclpy.spin, args=(self._node,), daemon=True)
        self._spin_thread.start()
        self._started = True

    def _ros_env(self) -> dict[str, str]:
        return load_ros_environ(workspace_setup=self._artifacts.workspace_setup)

    def close(self) -> None:
        if self._node is not None:
            import rclpy

            self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
            self._node = None
        if self._launch_proc and self._launch_proc.poll() is None:
            self._launch_proc.send_signal(signal.SIGINT)
            try:
                self._launch_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._launch_proc.kill()
        self._launch_proc = None
        self._started = False

    def reset(self, *, command: dict[str, Any] | None = None) -> SimState:
        if not self._started:
            self.start()
        state = self._mock.reset(command=command)
        return self._merge_ros_state(state)

    def step(self, target_positions: np.ndarray, *, command: dict[str, Any] | None = None) -> SimState:
        self._publish_trajectory(target_positions)
        dt = self._artifacts.control_dt
        time.sleep(dt)
        state = self._mock.step(target_positions, command=command)
        return self._merge_ros_state(state)

    def _publish_trajectory(self, positions: np.ndarray) -> None:
        if self._node is None:
            return
        msg = self._JointTrajectory()
        msg.joint_names = list(self._artifacts.joint_names)
        point = self._JointTrajectoryPoint()
        point.positions = [float(p) for p in positions]
        point.time_from_start.sec = 0
        point.time_from_start.nanosec = int(self._artifacts.control_dt * 1e9)
        msg.points = [point]
        self._jtc_pub.publish(msg)

    def _merge_ros_state(self, fallback: SimState) -> SimState:
        state = fallback.copy()
        if self._latest_joint_pos is not None:
            state.joint_pos = self._latest_joint_pos.copy()
        if self._latest_joint_vel is not None:
            state.joint_vel = self._latest_joint_vel.copy()
        ang_key = next((k for k in self._sensor_cache if k.endswith("_ang")), None)
        if ang_key:
            state.base_ang_vel = self._sensor_cache[ang_key].copy()
        grav_key = next(
            (k for k, spec in (self._artifacts.observations_doc.get("observations") or {}).items() if (spec.get("kind") or "").lower() == "imu"),
            None,
        )
        if grav_key and grav_key in self._sensor_cache:
            state.projected_gravity = self._sensor_cache[grav_key].copy()
        return state

    def action_to_targets(self, action: np.ndarray) -> np.ndarray:
        return self._mock.action_to_targets(action)

    def sensor_vectors(self) -> dict[str, np.ndarray]:
        return dict(self._sensor_cache)
