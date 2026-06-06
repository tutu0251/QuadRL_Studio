"""ROS 2 + Gazebo sim backend — subscribes to exported observation topics, commands JTC."""
from __future__ import annotations

import atexit
import ctypes
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from quadrl_env.disturbances import DisturbanceEngine
from quadrl_env.gazebo_bootstrap import (
    build_sim_launch_command,
    log_sampled_spawn_pose,
    run_gazebo_bootstrap,
)
from quadrl_env.gazebo_cleanup import cleanup_training_gazebo, terminate_process_group
from quadrl_env.gazebo_reset import apply_ros_wrench, reset_gazebo_robot
from quadrl_env.project_config import JointGains, ProjectArtifacts
from quadrl_env.ros_env import load_ros_environ, probe_rclpy_import
from quadrl_env.sensor_packing import normalized_gravity, pack_contact, pack_imu, pack_odom
from quadrl_env.sim_state import SimState

_rclpy_refcount = 0
_gazebo_refcount = 0
_shared_launch_proc: subprocess.Popen[str] | None = None
_ros_executor = None
_ros_spin_thread: threading.Thread | None = None
_ros_executor_lock = threading.Lock()
_ros_executor_nodes = 0
_gazebo_atexit_registered = False
_bootstrap_done = False


def _keep_gazebo_launch() -> bool:
    raw = os.environ.get("QUADRL_KEEP_GAZEBO", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _scoped_gazebo_cleanup() -> bool:
    """True under parallel training: confine cleanup to this process' own launch group."""
    raw = os.environ.get("QUADRL_GAZEBO_SCOPED_CLEANUP", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _ensure_rclpy_initialized() -> None:
    """Initialize rclpy once per process (EvalCallback uses a second env)."""
    global _rclpy_refcount
    import rclpy

    if not rclpy.ok():
        rclpy.init(args=None)
    _rclpy_refcount += 1


def _release_rclpy() -> None:
    global _rclpy_refcount
    import rclpy

    _rclpy_refcount = max(0, _rclpy_refcount - 1)
    if _rclpy_refcount == 0 and rclpy.ok():
        rclpy.shutdown()


def _register_ros_node(node: Any) -> None:
    """Attach node to a single process-wide executor (EvalCallback uses a second env)."""
    global _ros_executor, _ros_spin_thread, _ros_executor_nodes
    from rclpy.executors import SingleThreadedExecutor

    with _ros_executor_lock:
        if _ros_executor is None:
            _ros_executor = SingleThreadedExecutor()
            def _spin_safely() -> None:
                try:
                    _ros_executor.spin()
                except Exception:
                    # During SIGTERM / rclpy.shutdown(), the executor can raise
                    # ExternalShutdownException. Treat all shutdown-time errors as normal exit.
                    return

            _ros_spin_thread = threading.Thread(target=_spin_safely, daemon=True)
            _ros_spin_thread.start()
        _ros_executor.add_node(node)
        _ros_executor_nodes += 1


def wait_rcl_future(future: Any, *, timeout_sec: float) -> bool:
    """Wait for an async ROS future while the process-wide executor spins the node."""
    deadline = time.time() + timeout_sec
    while not future.done() and time.time() < deadline:
        time.sleep(0.02)
    return bool(future.done() and not future.cancelled())


def _unregister_ros_node(node: Any) -> None:
    global _ros_executor, _ros_executor_nodes
    with _ros_executor_lock:
        if _ros_executor is None or node is None:
            return
        try:
            _ros_executor.remove_node(node)
        except Exception:
            pass
        _ros_executor_nodes = max(0, _ros_executor_nodes - 1)


def _gazebo_headless_from_env() -> bool:
    """True = server-only (-s). Default headless when unset."""
    raw = os.environ.get("QUADRL_GAZEBO_HEADLESS", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def shutdown_shared_gazebo() -> None:
    """Stop the shared Gazebo launch and any stray sim processes (safe if already stopped)."""
    global _gazebo_refcount, _shared_launch_proc, _bootstrap_done
    proc = _shared_launch_proc
    _gazebo_refcount = 0
    _shared_launch_proc = None
    _bootstrap_done = False
    launch_pid = proc.pid if proc is not None and proc.poll() is None else None
    cleanup_training_gazebo(launch_pid, scoped=_scoped_gazebo_cleanup())


def _register_gazebo_atexit() -> None:
    global _gazebo_atexit_registered
    if not _gazebo_atexit_registered:
        atexit.register(shutdown_shared_gazebo)
        _gazebo_atexit_registered = True


_PR_SET_PDEATHSIG = 1  # <linux/prctl.h>


def _gazebo_preexec() -> None:
    """Child-side setup for the Gazebo launch (runs after fork, before exec).

    1. ``setsid()`` — put the launch in its own session/group so scoped cleanup can signal
       the whole tree without touching sibling envs (replaces ``start_new_session=True``).
    2. ``PR_SET_PDEATHSIG`` — ask the kernel to send SIGTERM the instant our parent (this
       env's worker process) dies, *even on SIGKILL*. A graceful exit cleans up via the
       refcount path; this covers the hard-crash case (OOM-kill / ``pkill -9`` of the
       worker tree) that would otherwise orphan the Gazebo server holding its DDS domain.
    """
    os.setsid()
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(_PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
    except Exception:
        pass  # best-effort; refcount/atexit cleanup still applies


def _reaping_launch_command(launch: str) -> str:
    """Wrap the launch so the bash leader reaps its whole process group on death.

    PR_SET_PDEATHSIG only signals the immediate bash child; the real sim tree (ros2 launch
    → gz server, bridges) are its descendants. On TERM/INT/HUP, bash kills its own group
    (it is the session leader from ``setsid``), escalating TERM→KILL so nothing survives.
    """
    return (
        "__qrl_reap() { trap - TERM INT HUP; kill -TERM 0 2>/dev/null; "
        "sleep 5; kill -KILL 0 2>/dev/null; }; "
        "trap __qrl_reap TERM INT HUP; "
        f"( {launch} ) & __qrl_pid=$!; wait \"$__qrl_pid\""
    )


def _acquire_gazebo(artifacts: ProjectArtifacts) -> subprocess.Popen[str]:
    """Launch Gazebo once; additional backends attach to the same sim."""
    global _gazebo_refcount, _shared_launch_proc, _bootstrap_done
    if _shared_launch_proc is None or _shared_launch_proc.poll() is not None:
        _bootstrap_done = False
        env = load_ros_environ(workspace_setup=artifacts.workspace_setup)
        headless = _gazebo_headless_from_env()
        launch = build_sim_launch_command(artifacts, headless=headless)
        _shared_launch_proc = subprocess.Popen(
            ["bash", "-lc", _reaping_launch_command(launch)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=_gazebo_preexec,
        )
        _register_gazebo_atexit()
        ok, err = run_gazebo_bootstrap(artifacts, _shared_launch_proc, env)
        if not ok:
            terminate_process_group(_shared_launch_proc.pid)
            _shared_launch_proc = None
            raise RuntimeError(f"Gazebo bootstrap failed: {err}")
        _bootstrap_done = True
    elif not _bootstrap_done:
        env = load_ros_environ(workspace_setup=artifacts.workspace_setup)
        ok, err = run_gazebo_bootstrap(artifacts, _shared_launch_proc, env)
        if not ok:
            raise RuntimeError(f"Gazebo bootstrap failed: {err}")
        _bootstrap_done = True
    _gazebo_refcount += 1
    return _shared_launch_proc


def _release_gazebo() -> None:
    global _gazebo_refcount, _shared_launch_proc
    _gazebo_refcount = max(0, _gazebo_refcount - 1)
    if _gazebo_refcount > 0 or _shared_launch_proc is None:
        return
    if _keep_gazebo_launch():
        return
    proc = _shared_launch_proc
    _shared_launch_proc = None
    if proc.poll() is None:
        terminate_process_group(proc.pid)
    cleanup_training_gazebo(scoped=_scoped_gazebo_cleanup())


def ros_stack_available(*, workspace_setup: Path | str | None = None) -> bool:
    if os.environ.get("QUADRL_ROS_ENV_BOOTSTRAPPED") == "1":
        try:
            import rclpy  # noqa: F401
        except ImportError:
            return False
        return True
    return probe_rclpy_import(workspace_setup=workspace_setup)


class RosSimBackend:
    """Wraps a running Gazebo workspace and streams state from ROS topics."""

    def __init__(self, artifacts: ProjectArtifacts, *, env_id: int = 0) -> None:
        self._artifacts = artifacts
        self._env_id = env_id
        self._launch_proc: subprocess.Popen[str] | None = None
        self._latest_joint_pos: np.ndarray | None = None
        self._latest_joint_vel: np.ndarray | None = None
        self._sensor_cache: dict[str, np.ndarray] = {}
        self._imu_raw: dict[str, dict[str, np.ndarray]] = {}
        self._odom_raw: dict[str, dict[str, float]] = {}
        self._contact_raw: dict[str, int] = {}
        self._disturbance = DisturbanceEngine({})
        self._world_name = os.environ.get("QUADRL_GZ_WORLD", "flat")
        self._entity_name = artifacts.project_name
        self._node = None
        self._started = False
        self._command: dict[str, Any] = {}
        self._step = 0
        self._last_state: SimState | None = None

    def set_stage_context(
        self,
        *,
        command: dict[str, Any] | None = None,
        disturbance: dict[str, Any] | None = None,
    ) -> None:
        if command is not None:
            self._command = dict(command)
        if disturbance is not None:
            self._disturbance = DisturbanceEngine(disturbance)

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
        from nav_msgs.msg import Odometry
        from rclpy.node import Node
        from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
        from ros_gz_interfaces.msg import Contacts
        from sensor_msgs.msg import Imu, JointState
        from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

        _ensure_rclpy_initialized()
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
            fields = list(spec.get("fields") or [])
            if not topic:
                continue
            if kind == "imu":

                def _imu_cb(msg: Imu, k=key, f=fields) -> None:
                    ang = np.array(
                        [
                            float(msg.angular_velocity.x),
                            float(msg.angular_velocity.y),
                            float(msg.angular_velocity.z),
                        ],
                        dtype=np.float32,
                    )
                    lin = np.array(
                        [
                            float(msg.linear_acceleration.x),
                            float(msg.linear_acceleration.y),
                            float(msg.linear_acceleration.z),
                        ],
                        dtype=np.float32,
                    )
                    orient = np.array(
                        [
                            float(msg.orientation.x),
                            float(msg.orientation.y),
                            float(msg.orientation.z),
                        ],
                        dtype=np.float32,
                    )
                    self._imu_raw[k] = {
                        "angular_velocity": ang,
                        "linear_acceleration": lin,
                        "orientation": orient,
                    }
                    self._sensor_cache[k] = pack_imu(
                        f,
                        angular_velocity=ang,
                        linear_acceleration=lin,
                        orientation=orient,
                    )

                self._node.create_subscription(Imu, topic, _imu_cb, reliable)
            elif kind == "contact":

                def _contact_cb(msg: Contacts, k=key, f=fields) -> None:
                    count = len(msg.contacts) if msg.contacts else 0
                    self._contact_raw[k] = count
                    self._sensor_cache[k] = pack_contact(f, contact_count=count)

                self._node.create_subscription(Contacts, topic, _contact_cb, reliable)
            elif kind == "odom":

                def _odom_cb(msg: Odometry, k=key, f=fields) -> None:
                    twist = msg.twist.twist
                    pos = msg.pose.pose.position
                    self._odom_raw[k] = {
                        "linear_velocity_x": float(twist.linear.x),
                        "linear_velocity_y": float(twist.linear.y),
                        "angular_velocity_z": float(twist.angular.z),
                        "position_z": float(pos.z),
                    }
                    self._sensor_cache[k] = pack_odom(
                        f,
                        linear_velocity_x=float(twist.linear.x),
                        linear_velocity_y=float(twist.linear.y),
                        angular_velocity_z=float(twist.angular.z),
                    )

                self._node.create_subscription(Odometry, topic, _odom_cb, reliable)

        self._jtc_pub = self._node.create_publisher(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
            10,
        )
        self._JointTrajectory = JointTrajectory
        self._JointTrajectoryPoint = JointTrajectoryPoint

        self._launch_proc = _acquire_gazebo(self._artifacts)

        _register_ros_node(self._node)
        self._apply_spawn_reset(self._artifacts.sample_spawn())
        self._started = True

    def close(self) -> None:
        if self._node is not None:
            _unregister_ros_node(self._node)
            self._node.destroy_node()
            self._node = None
            _release_rclpy()
        if self._launch_proc is not None:
            _release_gazebo()
        self._launch_proc = None
        self._started = False

    def _apply_spawn_reset(self, spawn_pose: dict[str, float]) -> None:
        if self._node is None:
            return
        default_targets = _default_joint_positions(self._artifacts)
        try:
            import rclpy

            if not rclpy.ok():
                return
        except ImportError:
            return
        reset_gazebo_robot(
            self._node,
            world_name=self._world_name,
            entity_name=self._entity_name,
            spawn=spawn_pose,
            joint_names=list(self._artifacts.joint_names),
            joint_positions=default_targets,
            jtc_pub=self._jtc_pub,
            joint_trajectory_msg_cls=self._JointTrajectory,
            joint_trajectory_point_cls=self._JointTrajectoryPoint,
            control_dt=self._artifacts.control_dt,
            wait_future=wait_rcl_future,
        )

    def reset(self, *, command: dict[str, Any] | None = None) -> SimState:
        if not self._started:
            self.start()
        if command:
            self._command = dict(command)
        self._disturbance.reset(seed=self._env_id)
        self._step = 0
        default_targets = _default_joint_positions(self._artifacts)
        try:
            import rclpy

            ros_live = rclpy.ok()
        except ImportError:
            ros_live = False
        spawn_pose = self._artifacts.sample_spawn()
        log_sampled_spawn_pose(spawn_pose, self._artifacts)
        if ros_live:
            self._apply_spawn_reset(spawn_pose)
        spawn_h = float(spawn_pose.get("z", 0.5))
        target_h = float(self._command.get("target_body_height", spawn_h))
        base_h = spawn_h
        fallback = SimState(
            joint_pos=default_targets.astype(np.float32, copy=True),
            joint_vel=np.zeros(len(self._artifacts.joint_names), dtype=np.float32),
            base_lin_vel=np.zeros(3, dtype=np.float32),
            base_ang_vel=np.zeros(3, dtype=np.float32),
            projected_gravity=np.array([0.0, 0.0, -1.0], dtype=np.float32),
            base_height=base_h,
            contact_forces={k: 0.0 for k in _foot_keys_from_observations(self._artifacts.observations_doc)},
            foot_air_time={},
            episode_step=0,
        )
        self._last_state = self._merge_ros_state(fallback)
        return self._last_state

    def step(self, target_positions: np.ndarray, *, command: dict[str, Any] | None = None) -> SimState:
        if command:
            self._command = dict(command)
        wrench = self._disturbance.ros_wrench()
        if wrench and self._node is not None:
            force, torque = wrench
            apply_ros_wrench(
                self._node,
                world_name=self._world_name,
                entity_name=self._entity_name,
                force=force,
                torque=torque,
            )
        self._publish_trajectory(target_positions)
        dt = self._artifacts.control_dt
        time.sleep(dt)
        self._step += 1
        last = self._last_state
        if last is None:
            last = self.reset(command=self._command)
        fallback = last.copy()
        fallback.episode_step = self._step
        # If ROS joint states aren't ready yet, prefer commanded targets over stale defaults.
        if self._latest_joint_pos is None:
            fallback.joint_pos = np.asarray(target_positions, dtype=np.float32).copy()
        self._last_state = self._merge_ros_state(fallback)
        return self._last_state

    def _publish_trajectory(self, positions: np.ndarray) -> None:
        if self._node is None:
            return
        try:
            import rclpy

            if not rclpy.ok():
                return
        except ImportError:
            return
        msg = self._JointTrajectory()
        msg.joint_names = list(self._artifacts.joint_names)
        point = self._JointTrajectoryPoint()
        point.positions = [float(p) for p in positions]
        point.time_from_start.sec = 0
        point.time_from_start.nanosec = int(self._artifacts.control_dt * 1e9)
        msg.points = [point]
        try:
            self._jtc_pub.publish(msg)
        except Exception:
            return

    def _merge_ros_state(self, fallback: SimState) -> SimState:
        state = fallback.copy()
        if self._latest_joint_pos is not None:
            state.joint_pos = self._latest_joint_pos.copy()
        if self._latest_joint_vel is not None:
            state.joint_vel = self._latest_joint_vel.copy()

        grav_key = next(
            (
                k
                for k, spec in (self._artifacts.observations_doc.get("observations") or {}).items()
                if (spec.get("kind") or "").lower() == "imu"
            ),
            None,
        )
        if grav_key and grav_key in self._imu_raw:
            raw = self._imu_raw[grav_key]
            state.base_ang_vel = raw["angular_velocity"].copy()
            state.projected_gravity = normalized_gravity(raw["linear_acceleration"])

        odom_key = next(
            (
                k
                for k, spec in (self._artifacts.observations_doc.get("observations") or {}).items()
                if (spec.get("kind") or "").lower() == "odom"
            ),
            None,
        )
        if odom_key and odom_key in self._odom_raw:
            raw = self._odom_raw[odom_key]
            state.base_lin_vel[0] = float(raw.get("linear_velocity_x", state.base_lin_vel[0]))
            state.base_lin_vel[1] = float(raw.get("linear_velocity_y", state.base_lin_vel[1]))
            if "position_z" in raw:
                state.base_height = float(raw["position_z"])

        foot_keys = _foot_keys_from_observations(self._artifacts.observations_doc)
        contacts: dict[str, float] = {}
        for key in foot_keys:
            count = self._contact_raw.get(key, 0)
            contacts[key] = 40.0 if count > 0 else 0.0
        if contacts:
            state.contact_forces = contacts

        return state

    def action_to_targets(self, action: np.ndarray) -> np.ndarray:
        return _action_to_targets(self._artifacts, action)

    def sensor_vectors(self) -> dict[str, np.ndarray]:
        obs_keys = set((self._artifacts.observations_doc.get("observations") or {}).keys())
        return {k: v.copy() for k, v in self._sensor_cache.items() if k in obs_keys}


def _default_joint_positions(artifacts: ProjectArtifacts) -> np.ndarray:
    return np.array(
        [artifacts.joint_gains[n].default_position for n in artifacts.joint_names],
        dtype=np.float32,
    )


def _action_to_targets(artifacts: ProjectArtifacts, action: np.ndarray) -> np.ndarray:
    action = np.asarray(action, dtype=np.float32)
    targets = np.zeros(len(artifacts.joint_names), dtype=np.float32)
    for i, name in enumerate(artifacts.joint_names):
        g = artifacts.joint_gains.get(name) or JointGains(name=name)
        a = float(action[i]) if i < len(action) else 0.0
        targets[i] = g.default_position + a * g.action_scale
    return targets


def _foot_keys_from_observations(doc: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for key, spec in (doc.get("observations") or {}).items():
        if (spec.get("kind") or "").lower() == "contact":
            keys.append(key)
    return keys or ["fl_contact", "fr_contact", "rl_contact", "rr_contact"]
