"""Apply workspace spawn reset (pose + joints) from spawn test manager."""
from __future__ import annotations

import json
import shlex
from pathlib import Path

from api.spawn_workspace_session import WORKSPACE_WORLD, workspace_setup_path
from storage import project_storage

ROS_SETUP = "/opt/ros/humble/setup.bash"
APPLY_RESET_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_spawn_reset.py"


def apply_workspace_spawn_reset(
    project: str,
    *,
    spawn: dict[str, float],
    env: dict[str, str],
    timeout_s: float = 60.0,
) -> tuple[bool, str]:
    from ev_ros_env import bash_ros_cmd

    setup = workspace_setup_path(project)
    project_dir = project_storage.project_dir(project)
    merged = dict(env)
    merged["QUADRL_SPAWN_POSE_JSON"] = json.dumps(
        {k: float(spawn[k]) for k in ("x", "y", "z", "roll", "pitch", "yaw")}
    )
    cmd = (
        f"source {shlex.quote(ROS_SETUP)} && "
        f"export QUADRL_SPAWN_POSE_JSON={shlex.quote(merged['QUADRL_SPAWN_POSE_JSON'])} && "
        f"python3 {shlex.quote(str(APPLY_RESET_SCRIPT))} "
        f"{shlex.quote(str(project_dir))} {shlex.quote(WORKSPACE_WORLD)} {shlex.quote(project)}"
    )
    proc = bash_ros_cmd(cmd, setup=setup, timeout=timeout_s, env=merged)
    err = (proc.stderr or proc.stdout or "").strip()
    if proc.returncode != 0:
        return False, err or f"spawn reset exited {proc.returncode}"
    return True, ""
