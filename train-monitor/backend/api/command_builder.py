"""Build shell command previews for Train Monitor UI actions."""
from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, Optional

from storage import project_storage

REPO_ROOT = Path(__file__).resolve().parents[3]
TRAIN_SCRIPT = REPO_ROOT / "training" / "scripts" / "run_rl_train.py"
TRAIN_VENV_PYTHON = REPO_ROOT / "training" / ".venv" / "bin" / "python"
WS_SCRIPTS = REPO_ROOT / "workspace-generator" / "scripts"


def _python_executable() -> str:
    if TRAIN_VENV_PYTHON.is_file():
        return str(TRAIN_VENV_PYTHON)
    return "python3"


def _project_dir(name: str) -> Path:
    return project_storage.project_dir(name)


def build_train_command(
    project: str,
    *,
    dry_run: bool = False,
    gazebo_headless: bool = True,
    resume_checkpoint: Optional[str] = None,
    start_stage: Optional[int] = None,
    config_path: Optional[str] = None,
    controller_apply_delay_s: Optional[float] = None,
    reset_log_std: bool = False,
    vf_coef: Optional[float] = None,
) -> str:
    cmd = [
        _python_executable(),
        str(TRAIN_SCRIPT),
        str(_project_dir(project)),
    ]
    if config_path:
        cmd.extend(["--config", config_path])
    if dry_run:
        cmd.append("--dry-run")
    if gazebo_headless:
        cmd.append("--gazebo-headless")
    else:
        cmd.append("--gazebo-gui")
    if resume_checkpoint:
        cmd.extend(["--resume", resume_checkpoint])
    if start_stage is not None:
        cmd.extend(["--start-stage", str(start_stage)])
    if reset_log_std:
        cmd.append("--reset-log-std")
    if vf_coef is not None:
        cmd.extend(["--vf-coef", str(vf_coef)])

    parts = [shlex.quote(p) for p in cmd]
    env_prefix = ""
    if controller_apply_delay_s is not None:
        env_prefix = f"QUADRL_SIM_WARMUP_S={controller_apply_delay_s} "
    return env_prefix + " ".join(parts)


def build_tensorboard_command(project: str, *, run_id: Optional[str] = None) -> str:
    logdir = project_storage.runs_dir(project)
    if run_id:
        logdir = logdir / run_id
    py = _python_executable()
    return (
        f"{shlex.quote(py)} -m tensorboard.main "
        f"--logdir {shlex.quote(str(logdir))} --host 127.0.0.1 --port <auto>"
    )


def build_workspace_script(script_name: str, project: str, *extra: str) -> str:
    script = WS_SCRIPTS / script_name
    parts = ["bash", str(script), project, *extra]
    return " ".join(shlex.quote(p) for p in parts)


def build_topic_echo_command(topic: str, *, setup_bash: Optional[str] = None) -> str:
    quoted = shlex.quote(topic)
    inner = f"ros2 topic echo {quoted} --once --spin-time 12 --qos-reliability reliable"
    if setup_bash:
        return (
            f"bash -lc 'source /opt/ros/humble/setup.bash && "
            f"source {shlex.quote(setup_bash)} && {inner}'"
        )
    return inner


def build_spawn_patch_command(project: str, body: dict[str, Any]) -> str:
    payload = json.dumps(body)
    url = f"http://127.0.0.1:8006/api/projects/{project}/spawn-config"
    return (
        f"curl -sS -X PATCH {shlex.quote(url)} "
        f"-H 'Content-Type: application/json' "
        f"-d {shlex.quote(payload)}"
    )


def build_training_config_patch_command(project: str, body: dict[str, Any]) -> str:
    payload = json.dumps(body)
    url = f"http://127.0.0.1:8006/api/projects/{project}/training-config"
    return (
        f"curl -sS -X PATCH {shlex.quote(url)} "
        f"-H 'Content-Type: application/json' "
        f"-d {shlex.quote(payload)}"
    )


def build_test_spawn_command(
    project: str,
    *,
    spawn_pose: Optional[dict[str, float]] = None,
    headless: bool = True,
) -> str:
    from api.spawn_config_manager import get_spawn_config, resolve_spawn_create_pose
    from api.spawn_workspace_session import (
        LAUNCH_SPAWN_SETTLE_S,
        WORKSPACE_WORLD,
        build_sim_launch_command,
        require_workspace_setup,
    )

    setup = require_workspace_setup(project)
    cfg = get_spawn_config(project)
    if spawn_pose is None:
        spawn_pose = resolve_spawn_create_pose(cfg)
    apply_script = Path(__file__).resolve().parents[1] / "scripts" / "apply_spawn_reset.py"
    spawn_json = json.dumps({k: spawn_pose[k] for k in ("x", "y", "z", "roll", "pitch", "yaw")})
    warmup = max(0.0, float(cfg.controller_apply_delay_s))
    project_dir = _project_dir(project)
    launch = build_sim_launch_command(project, headless=headless)
    return (
        f"{launch} &\n"
        f"sleep {LAUNCH_SPAWN_SETTLE_S:.0f} && "
        f"source {shlex.quote(str(ROS_SETUP))} && source {shlex.quote(str(setup))} && "
        f"ros2 control list_controllers --controller-manager /controller_manager && "
        f"sleep {warmup:.0f} && "
        f"export QUADRL_SPAWN_POSE_JSON={shlex.quote(spawn_json)} && "
        f"python3 {shlex.quote(str(apply_script))} "
        f"{shlex.quote(str(project_dir))} {shlex.quote(WORKSPACE_WORLD)} {shlex.quote(project)}"
    )


ROS_SETUP = "/opt/ros/humble/setup.bash"


def build_spawn_test_stop_command(project: str) -> str:
    url = f"http://127.0.0.1:8006/api/projects/{project}/spawn/test/stop"
    return f"curl -sS -X POST {shlex.quote(url)}"


def build_spawn_test_api_command(project: str) -> str:
    url = f"http://127.0.0.1:8006/api/projects/{project}/spawn/test"
    return f"curl -sS -X POST {shlex.quote(url)}"


def build_topics_confirm_command(project: str, topics: list[str]) -> str:
    payload = json.dumps({"confirmed_topics": topics})
    url = f"http://127.0.0.1:8006/api/projects/{project}/topics/confirmations"
    return (
        f"curl -sS -X PATCH {shlex.quote(url)} "
        f"-H 'Content-Type: application/json' "
        f"-d {shlex.quote(payload)}"
    )


def preview_command(action: str, project: str, params: Optional[dict[str, Any]] = None) -> dict[str, str]:
    p = params or {}
    description = ""

    if action == "workspace_setup":
        cmd = build_workspace_script("setup_robot.sh", project)
        description = "Generate workspace, colcon build, headless readiness"
    elif action == "workspace_generate":
        cmd = build_workspace_script("generate_workspace.sh", project)
    elif action == "workspace_build":
        cmd = build_workspace_script("build_workspace.sh", project)
    elif action == "workspace_build_clean":
        cmd = build_workspace_script("build_workspace.sh", project, "--clean")
    elif action == "workspace_validate_exports":
        cmd = build_workspace_script("validate_sensor_exports.sh", project)
    elif action == "workspace_validate_static":
        cmd = build_workspace_script("validate_training_readiness.sh", project, "--static-only")
    elif action == "workspace_validate_no_gazebo":
        cmd = build_workspace_script("validate_training_readiness.sh", project, "--skip-runtime")
    elif action == "workspace_validate_full":
        cmd = build_workspace_script("validate_training_readiness.sh", project)
    elif action == "train_start":
        cmd = build_train_command(
            project,
            dry_run=bool(p.get("dry_run")),
            gazebo_headless=bool(p.get("gazebo_headless", True)),
            controller_apply_delay_s=p.get("controller_apply_delay_s"),
        )
    elif action == "train_stop":
        cmd = "kill -TERM <training_pid>  # or POST /api/projects/{}/train/stop".format(project)
    elif action == "train_resume":
        cmd = build_train_command(
            project,
            dry_run=bool(p.get("dry_run")),
            gazebo_headless=bool(p.get("gazebo_headless", True)),
            resume_checkpoint=str(p.get("resume_checkpoint", "")),
            start_stage=p.get("start_stage"),
            reset_log_std=bool(p.get("reset_log_std")),
            vf_coef=p.get("vf_coef"),
            controller_apply_delay_s=p.get("controller_apply_delay_s"),
        )
    elif action == "tensorboard_start":
        cmd = build_tensorboard_command(project, run_id=p.get("run_id"))
    elif action == "tensorboard_stop":
        cmd = "kill -TERM <tensorboard_pid>  # or POST /api/projects/{}/tensorboard/stop".format(project)
    elif action == "spawn_config_save":
        cmd = build_spawn_patch_command(project, p.get("body") or {})
        description = "Update spawn offset and post-spawn controller apply delay"
    elif action == "spawn_config_confirm":
        cmd = build_spawn_patch_command(project, {"pose_confirmed": True})
    elif action == "topic_echo":
        setup = p.get("setup_bash")
        cmd = build_topic_echo_command(str(p.get("topic", "/topic")), setup_bash=setup)
    elif action == "topics_confirm":
        cmd = build_topics_confirm_command(project, list(p.get("confirmed_topics") or []))
    elif action == "topics_watch_start":
        topics = p.get("topics") or []
        if topics:
            quoted = " ".join(shlex.quote(t) for t in topics)
            cmd = (
                f"curl -sS -X POST http://127.0.0.1:8006/api/projects/{shlex.quote(project)}/topics/watch/start "
                f"-H 'Content-Type: application/json' -d {shlex.quote(json.dumps({'topics': topics}))}"
            )
        else:
            cmd = (
                f"curl -sS -X POST http://127.0.0.1:8006/api/projects/{shlex.quote(project)}/topics/watch/start "
                "-H 'Content-Type: application/json' -d '{}'"
            )
        description = "Start polling observation topics with ros2 topic echo"
    elif action == "topics_watch_stop":
        cmd = (
            f"curl -sS -X POST http://127.0.0.1:8006/api/projects/{shlex.quote(project)}/topics/watch/stop"
        )
        description = "Stop topic echo polling"
    elif action == "training_config_save":
        cmd = build_training_config_patch_command(project, p.get("body") or {})
        description = "Write action/observation scales to export YAML"
    elif action == "test_spawn_stop":
        cmd = build_spawn_test_stop_command(project)
        description = "Stop active spawn test session"
    elif action == "test_spawn":
        cmd = build_test_spawn_command(
            project,
            headless=bool(p.get("headless", True)),
        )
        description = "Workspace spawn test: sim.launch.py, warmup, pose + stand joints via ros2_control"
    else:
        cmd = f"# unknown action: {action}"

    return {"action": action, "command": cmd, "description": description}
