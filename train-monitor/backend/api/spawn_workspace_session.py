"""Workspace-based Gazebo spawn test (sim.launch.py + ros2_control)."""
from __future__ import annotations

import re
import shlex
import time
from pathlib import Path

from storage import project_storage

ROS_SETUP = "/opt/ros/humble/setup.bash"
WORKSPACE_WORLD = "flat"
# sim.launch.py: create @3s, bridge @5s, jsb @8s, jtc after jsb
LAUNCH_SPAWN_SETTLE_S = 12.0


def _sanitize_pkg(name: str) -> str:
    n = re.sub(r"[^a-z0-9_]", "_", name.lower().strip())
    n = re.sub(r"_+", "_", n).strip("_")
    if not n or n[0].isdigit():
        n = f"robot_{n or 'unnamed'}"
    return n


def workspace_setup_path(project: str) -> Path:
    return project_storage.project_dir(project) / "workspace" / "install" / "setup.bash"


def bringup_package(project: str) -> str:
    return f"{_sanitize_pkg(project)}_bringup"


def require_workspace_setup(project: str) -> Path:
    setup = workspace_setup_path(project)
    if not setup.is_file():
        raise FileNotFoundError(
            f"Workspace not built for '{project}'. "
            f"Run Topic Monitor → Workspace setup (or colcon build) before test spawn."
        )
    return setup


def build_sim_launch_command(project: str, *, headless: bool) -> str:
    setup = require_workspace_setup(project)
    pkg = bringup_package(project)
    headless_arg = "true" if headless else "false"
    return (
        f"source {shlex.quote(ROS_SETUP)} && source {shlex.quote(str(setup))} && "
        f"ros2 launch {pkg} sim.launch.py headless:={headless_arg}"
    )


def wait_for_controller_active(
    setup: Path,
    env: dict[str, str],
    controller_name: str,
    *,
    timeout_s: float = 90.0,
    poll_s: float = 2.0,
) -> tuple[bool, str]:
    """Poll ``ros2 control list_controllers`` until *controller_name* is active."""
    from ev_ros_env import bash_ros_cmd

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        proc = bash_ros_cmd(
            "ros2 control list_controllers --controller-manager /controller_manager",
            setup=setup,
            timeout=15,
            env=env,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if controller_name in out and "active" in out.lower():
            return True, ""
        time.sleep(poll_s)
    return False, f"Timed out waiting for {controller_name}"


def wait_for_controllers_ready(
    setup: Path,
    env: dict[str, str],
    *,
    timeout_s: float = 90.0,
    poll_s: float = 2.0,
) -> tuple[bool, str]:
    """Wait until joint_state_broadcaster then joint_trajectory_controller are active."""
    ok, err = wait_for_controller_active(
        setup,
        env,
        "joint_state_broadcaster",
        timeout_s=timeout_s,
        poll_s=poll_s,
    )
    if not ok:
        return False, err or "spawn stack not ready (joint_state_broadcaster)"
    return wait_for_controller_active(
        setup,
        env,
        "joint_trajectory_controller",
        timeout_s=timeout_s,
        poll_s=poll_s,
    )
