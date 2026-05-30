"""ROS 2 / Gazebo environment helpers."""
from __future__ import annotations

import glob
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROS_SETUP = Path("/opt/ros/humble/setup.bash")
ROS_PLUGIN_LIB = Path("/opt/ros/humble/lib")


def prepend_path_env(env: dict[str, str], key: str, prefix: str) -> None:
    existing = env.get(key, "")
    parts = [p for p in existing.split(":") if p]
    if prefix not in parts:
        env[key] = f"{prefix}:{existing}" if existing else prefix


def sim_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    prefix = str(ROS_PLUGIN_LIB)
    prepend_path_env(env, "GZ_SIM_SYSTEM_PLUGIN_PATH", prefix)
    prepend_path_env(env, "LD_LIBRARY_PATH", prefix)
    env.setdefault("ROS_LOCALHOST_ONLY", "1")
    return env


def load_ros_environ(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    if not ROS_SETUP.is_file():
        return sim_env(env)
    proc = subprocess.run(
        ["bash", "-lc", f"source {shlex.quote(str(ROS_SETUP))} && env"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return sim_env(env)
    for line in proc.stdout.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key] = value
    return sim_env(env)


def cleanup_fastrtps_shm() -> None:
    for pattern in ("/dev/shm/fastrtps*", "/dev/shm/*fastdds*"):
        for path in glob.glob(pattern):
            try:
                os.remove(path)
            except OSError:
                pass


def bash_ros_cmd(
    script: str,
    *,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not ROS_SETUP.is_file():
        raise FileNotFoundError(f"ROS setup not found: {ROS_SETUP}")
    merged = load_ros_environ(env)
    return subprocess.run(
        ["bash", "-lc", f"source {shlex.quote(str(ROS_SETUP))} && {script}"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=merged,
    )


def check_runtime_stack() -> dict[str, Any]:
    details: dict[str, Any] = {
        "rosSetup": ROS_SETUP.is_file(),
        "colcon": shutil.which("colcon") is not None,
        "gzRos2Control": False,
        "rosGzSim": False,
        "rosGzBridge": False,
        "controllerManager": False,
        "jointStateBroadcaster": False,
        "jointTrajectoryController": False,
    }
    missing: list[str] = []

    if not details["rosSetup"]:
        missing.append(f"ROS 2 setup ({ROS_SETUP})")
    if not details["colcon"]:
        missing.append("colcon")

    if details["rosSetup"]:
        for pkg, key in (
            ("gz_ros2_control", "gzRos2Control"),
            ("ros_gz_sim", "rosGzSim"),
            ("ros_gz_bridge", "rosGzBridge"),
            ("controller_manager", "controllerManager"),
            ("joint_state_broadcaster", "jointStateBroadcaster"),
            ("joint_trajectory_controller", "jointTrajectoryController"),
        ):
            try:
                proc = bash_ros_cmd(f"ros2 pkg prefix {pkg}", timeout=10)
                details[key] = proc.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                details[key] = False
            if not details[key]:
                missing.append(pkg)

    details["available"] = len(missing) == 0
    details["missing"] = missing
    return details
