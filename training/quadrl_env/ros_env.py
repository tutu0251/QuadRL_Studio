"""ROS 2 Humble environment for training (rclpy + Gazebo subprocesses)."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

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


def load_ros_environ(
    base: dict[str, str] | None = None,
    *,
    workspace_setup: Path | str | None = None,
) -> dict[str, str]:
    """Merge `source /opt/ros/humble/setup.bash` (+ optional workspace) into an env dict."""
    env = dict(base or os.environ)
    if not ROS_SETUP.is_file():
        return sim_env(env)

    source = f"source {shlex.quote(str(ROS_SETUP))}"
    if workspace_setup is not None:
        ws = Path(workspace_setup)
        if ws.is_file():
            source += f" && source {shlex.quote(str(ws))}"

    proc = subprocess.run(
        ["bash", "-lc", f"{source} && env"],
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


def apply_ros_to_process(
    base: dict[str, str] | None = None,
    *,
    workspace_setup: Path | str | None = None,
) -> dict[str, str]:
    """Apply ROS paths to os.environ and sys.path (PYTHONPATH only; see bootstrap_ros_runtime)."""
    merged = load_ros_environ(base, workspace_setup=workspace_setup)
    for key, value in merged.items():
        os.environ[key] = value
    for entry in (merged.get("PYTHONPATH") or "").split(":"):
        if entry and entry not in sys.path:
            sys.path.insert(0, entry)
    return merged


def bootstrap_ros_runtime(
    *,
    workspace_setup: Path | str | None = None,
    sim_mode: str = "auto",
) -> None:
    """Re-exec the current process under `source /opt/ros/humble/setup.bash` when needed.

    rclpy's native libraries must be on LD_LIBRARY_PATH before Python starts; updating
    os.environ later is not enough for the dynamic linker.
    """
    if os.environ.get("QUADRL_ROS_ENV_BOOTSTRAPPED") == "1":
        return
    mode = sim_mode.lower()
    if mode not in ("auto", "ros"):
        return
    if not ROS_SETUP.is_file():
        return

    source = f"source {shlex.quote(str(ROS_SETUP))}"
    if workspace_setup is not None:
        ws = Path(workspace_setup)
        if ws.is_file():
            source += f" && source {shlex.quote(str(ws))}"

    argv = " ".join(shlex.quote(a) for a in sys.argv)
    inner = (
        f"export QUADRL_ROS_ENV_BOOTSTRAPPED=1 && {source} && "
        f"exec {shlex.quote(sys.executable)} {argv}"
    )
    os.execvp("bash", ["bash", "-lc", inner])


def probe_rclpy_import(*, workspace_setup: Path | str | None = None) -> bool:
    """Return whether rclpy imports in a fresh shell with ROS sourced."""
    if not ROS_SETUP.is_file():
        return False
    source = f"source {shlex.quote(str(ROS_SETUP))}"
    if workspace_setup is not None:
        ws = Path(workspace_setup)
        if ws.is_file():
            source += f" && source {shlex.quote(str(ws))}"
    proc = subprocess.run(
        ["bash", "-lc", f"{source} && {shlex.quote(sys.executable)} -c 'import rclpy'"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0
