"""Gazebo launch bootstrap aligned with Spawn Monitor timing."""
from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from quadrl_env.project_config import ProjectArtifacts, SpawnOffset, sample_spawn_pose
from quadrl_env.ros_env import ROS_SETUP, load_ros_environ

# sim.launch.py: create @3s, bridge @5s, jsb @8s, jtc after jsb
LAUNCH_SPAWN_SETTLE_S = 12.0
_LOG_PREFIX = "[train-spawn]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", flush=True)


def build_sim_launch_command(artifacts: ProjectArtifacts, *, headless: bool) -> str:
    setup = artifacts.workspace_setup
    if setup is None or not setup.is_file():
        raise FileNotFoundError("Workspace setup.bash missing — build workspace before training")
    pkg = artifacts.bringup_pkg
    headless_arg = "true" if headless else "false"
    return (
        f"source {shlex.quote(str(ROS_SETUP))} && source {shlex.quote(str(setup))} && "
        f"ros2 launch {pkg} sim.launch.py headless:={headless_arg}"
    )


def bash_ros_cmd(
    script: str,
    *,
    workspace_setup: Path,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = load_ros_environ(env, workspace_setup=workspace_setup)
    domain = shlex.quote(str(merged.get("ROS_DOMAIN_ID", "0")))
    localhost = shlex.quote(str(merged.get("ROS_LOCALHOST_ONLY", "1")))
    prefix = f"export ROS_DOMAIN_ID={domain} && export ROS_LOCALHOST_ONLY={localhost} && "
    source = f"source {shlex.quote(str(ROS_SETUP))} && source {shlex.quote(str(workspace_setup))}"
    return subprocess.run(
        ["bash", "-lc", f"{prefix}{source} && {script}"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=merged,
    )


def wait_for_controller_active(
    workspace_setup: Path,
    env: dict[str, str],
    controller_name: str,
    *,
    timeout_s: float = 90.0,
    poll_s: float = 2.0,
) -> tuple[bool, str]:
    """Poll ``ros2 control list_controllers`` until *controller_name* is active."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        proc = bash_ros_cmd(
            "ros2 control list_controllers --controller-manager /controller_manager",
            workspace_setup=workspace_setup,
            timeout=15.0,
            env=env,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if controller_name in out and "active" in out.lower():
            return True, ""
        time.sleep(poll_s)
    return False, f"Timed out waiting for {controller_name}"


def _launch_exited_early(proc: subprocess.Popen[str]) -> tuple[bool, str]:
    if proc.poll() is None:
        return False, ""
    return True, f"sim.launch exited with code {proc.returncode}"


def _controller_warmup_s() -> float:
    return max(0.0, float(os.environ.get("QUADRL_SIM_WARMUP_S", "25")))


def wait_after_launch_settle(
    proc: subprocess.Popen[str],
    *,
    settle_s: float = LAUNCH_SPAWN_SETTLE_S,
) -> tuple[bool, str]:
    """Sleep for launch spawn timers and verify the process is still running."""
    _log(f"Waiting {settle_s:.0f}s for sim.launch spawn timers...")
    time.sleep(settle_s)
    early, msg = _launch_exited_early(proc)
    if early:
        return False, msg
    return True, ""


def wait_for_controllers_ready(
    artifacts: ProjectArtifacts,
    env: dict[str, str],
    *,
    controller_apply_delay_s: float | None = None,
) -> tuple[bool, str]:
    """Poll JSB, optional warmup delay, then JTC — same order as Spawn Monitor."""
    setup = artifacts.workspace_setup
    if setup is None:
        return False, "workspace setup missing"

    _log("Waiting for joint_state_broadcaster...")
    ok, err = wait_for_controller_active(setup, env, "joint_state_broadcaster", timeout_s=90.0)
    if not ok:
        return False, err or "joint_state_broadcaster not active"

    delay = _controller_warmup_s() if controller_apply_delay_s is None else max(0.0, float(controller_apply_delay_s))
    if delay > 0:
        _log(f"Controller warmup {delay:.0f}s (delay after spawn before control applies)")
        time.sleep(delay)
        _log("Controller warmup complete")

    _log("Waiting for joint_trajectory_controller...")
    ok, err = wait_for_controller_active(setup, env, "joint_trajectory_controller", timeout_s=60.0)
    if not ok:
        return False, err or "joint_trajectory_controller not active"
    return True, ""


def run_gazebo_bootstrap(
    artifacts: ProjectArtifacts,
    proc: subprocess.Popen[str],
    env: dict[str, str],
    *,
    controller_apply_delay_s: float | None = None,
) -> tuple[bool, str]:
    """Post-launch settle + controller readiness (no pose apply)."""
    time.sleep(2.0)
    early, msg = _launch_exited_early(proc)
    if early:
        return False, f"sim.launch exited early: {msg}"

    ok, err = wait_after_launch_settle(proc)
    if not ok:
        return False, err

    return wait_for_controllers_ready(
        artifacts,
        env,
        controller_apply_delay_s=controller_apply_delay_s,
    )


def log_sampled_spawn_pose(pose: dict[str, float], artifacts: ProjectArtifacts) -> None:
    base = artifacts.base_spawn
    _log(
        "Sampled spawn: "
        f"x={pose['x']:.3f} y={pose['y']:.3f} z={pose['z']:.3f} "
        f"rpy=({pose['roll']:.3f}, {pose['pitch']:.3f}, {pose['yaw']:.3f}) "
        f"(base x={base['x']:.3f} y={base['y']:.3f} z={base['z']:.3f})"
    )


def sample_training_spawn(artifacts: ProjectArtifacts, rng: Any | None = None) -> dict[str, float]:
    pose = sample_spawn_pose(artifacts.base_spawn, artifacts.spawn_offset, rng=rng)
    log_sampled_spawn_pose(pose, artifacts)
    return pose
