"""Runtime validation for control-editor exports via colcon workspace + Gazebo."""
from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from bridge_and_topics import REQUIRED_CONTROLLERS, parse_controllers_from_log, parse_joint_states
from control_workspace import control_exports_stale, generate_control_workspace
from models import ValidationIssue, ValidationResult
from control_paths import ControlProjectPaths
from ev_ros_env import ROS_SETUP, bash_ros_cmd, check_control_runtime_stack, cleanup_fastrtps_shm, load_ros_environ

LAUNCH_READY_TIMEOUT_S = 90.0
JOINT_STATES_TIMEOUT_S = 30.0
CONTROL_PROBE_TIMEOUT_S = 30.0
MIN_JOINT_DELTA = 0.01
CONTROLLER_READY_MARKERS = (
    "Configured and activated joint_state_broadcaster",
    "Activating controller 'joint_state_broadcaster'",
)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")

LogFn = Callable[[str], None]


def _issue(
    severity: str,
    code: str,
    message: str,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        code=code,
        message=message,
        entityType=entity_type,
        entityId=entity_id,
    )


def _noop_log(_: str) -> None:
    pass


def _build_workspace(paths: ControlProjectPaths, *, on_log: LogFn | None = None) -> dict[str, Any]:
    log = on_log or _noop_log
    ws = paths.workspace_dir
    report: dict[str, Any] = {
        "success": False,
        "workspace_path": str(ws),
    }
    if not (ws / "src").is_dir():
        report["error"] = "workspace_not_generated"
        report["message"] = f"No workspace at {ws}; run generate first"
        return report

    env = load_ros_environ()
    log("  colcon build --symlink-install...")
    proc = subprocess.run(
        ["colcon", "build", "--symlink-install"],
        cwd=str(ws),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    report["return_code"] = proc.returncode
    report["success"] = proc.returncode == 0
    report["message"] = "colcon build finished" if report["success"] else "colcon build failed"
    if not report["success"]:
        tail = "\n".join((proc.stderr or proc.stdout or "").splitlines()[-20:])
        report["log_excerpt"] = tail
    return report


def _cleanup_sim_processes(bringup_pkg: str) -> None:
    for pattern in (
        f"{bringup_pkg} control_readiness.launch.py",
        "ign gazebo",
        "gz sim",
    ):
        subprocess.run(["pkill", "-f", pattern], check=False)
    time.sleep(2.0)


def _stop_process(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _wait_for_publishers(topic: str, setup: Path, timeout_s: float, env: dict[str, str]) -> bool:
    deadline = time.monotonic() + timeout_s
    quoted = shlex.quote(topic)
    while time.monotonic() < deadline:
        proc = bash_ros_cmd(f"ros2 topic info {quoted}", setup=setup, timeout=15, env=env)
        out = (proc.stdout or "") + (proc.stderr or "")
        match = re.search(r"Publisher count:\s*(\d+)", out)
        if match and int(match.group(1)) > 0:
            return True
        echo = bash_ros_cmd(
            f"ros2 topic echo {quoted} --once --spin-time 6",
            setup=setup,
            timeout=20,
            env=env,
        )
        echo_out = echo.stdout or ""
        if echo.returncode == 0 and ("position:" in echo_out or "name:" in echo_out):
            return True
        time.sleep(2.0)
    return False


def _read_launch_log(log_path: Path) -> str:
    if not log_path.is_file():
        return ""
    return _ANSI_ESCAPE_RE.sub("", log_path.read_text(errors="replace"))


def _wait_for_controllers_in_log(
    log_path: Path,
    proc: subprocess.Popen[Any],
    timeout_s: float,
    *,
    on_log: LogFn | None = None,
) -> tuple[bool, str]:
    log = on_log or _noop_log
    deadline = time.monotonic() + timeout_s
    started = time.monotonic()
    last_heartbeat = started
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            excerpt = _read_launch_log(log_path)[-1500:]
            return False, f"Launch process exited early — see control_runtime_launch.log\n{excerpt}"
        text = _read_launch_log(log_path)
        if any(marker in text for marker in CONTROLLER_READY_MARKERS):
            elapsed = int(time.monotonic() - started)
            log(f"  controllers ready ({elapsed}s)")
            return True, ""
        now = time.monotonic()
        if now - last_heartbeat >= 10.0:
            elapsed = int(now - started)
            log(f"  still waiting for controllers ({elapsed}s)...")
            last_heartbeat = now
        time.sleep(2.0)
    return False, f"Timed out waiting for controllers in launch log ({int(timeout_s)}s)"


def _read_joint_states(setup: Path, env: dict[str, str]) -> dict[str, float]:
    proc = bash_ros_cmd(
        "ros2 topic echo /joint_states --once --spin-time 8",
        setup=setup,
        timeout=15,
        env=env,
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return {}
    return parse_joint_states(proc.stdout or "")


def _joint_names_from_controllers_yaml(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    doc = yaml.safe_load(text) or {}
    params = doc.get("joint_trajectory_controller", {}).get("ros__parameters") or {}
    joints = params.get("joints") or []
    return [str(j) for j in joints]


def _send_control_probe(
    joint_name: str,
    all_joints: list[str],
    before: dict[str, float],
    target_delta: float,
    setup: Path,
    env: dict[str, str],
) -> tuple[bool, str, float]:
    start_positions = [before.get(j, 0.0) for j in all_joints]
    target_positions = start_positions.copy()
    probe_index = all_joints.index(joint_name)
    target_positions[probe_index] = start_positions[probe_index] + target_delta
    goal = {
        "trajectory": {
            "joint_names": all_joints,
            "points": [
                {
                    "positions": start_positions,
                    "velocities": [0.0] * len(all_joints),
                    "time_from_start": {"sec": 0, "nanosec": 0},
                },
                {
                    "positions": target_positions,
                    "velocities": [0.0] * len(all_joints),
                    "time_from_start": {"sec": 4, "nanosec": 0},
                },
            ],
        }
    }
    payload = json.dumps(goal)
    script = (
        "ros2 action send_goal /joint_trajectory_controller/follow_joint_trajectory "
        "control_msgs/action/FollowJointTrajectory "
        f"{shlex.quote(payload)}"
    )
    proc = bash_ros_cmd(script, setup=setup, timeout=CONTROL_PROBE_TIMEOUT_S, env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    if "Goal was rejected" in out or "REJECTED" in out:
        return False, out.strip()[-400:], target_positions[probe_index]
    if "Goal finished with status: SUCCEEDED" in out or "status: SUCCEEDED" in out:
        return True, out.strip()[-400:], target_positions[probe_index]
    if "Goal finished with status: ABORTED" in out or "status: ABORTED" in out:
        return False, out.strip()[-400:], target_positions[probe_index]
    return False, out.strip()[-400:] if out.strip() else "no action response", target_positions[probe_index]


def _run_runtime(paths: ControlProjectPaths, *, on_log: LogFn | None = None) -> dict[str, Any]:
    log = on_log or _noop_log
    result: dict[str, Any] = {
        "status": "failed",
        "controllers": {},
        "control_probe": {},
        "errors": [],
    }

    setup = paths.install_setup()
    if not setup.is_file():
        result["errors"].append(f"Workspace not built: {setup} missing")
        return result

    _cleanup_sim_processes(paths.bringup_pkg)
    cleanup_fastrtps_shm()
    env = load_ros_environ()
    env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    domain_id = str(os.getpid() % 230)
    env["ROS_DOMAIN_ID"] = domain_id
    env["ROS_LOCALHOST_ONLY"] = "1"
    log_path = paths.workspace_dir / "control_runtime_launch.log"

    launch_cmd = (
        f"export ROS_DOMAIN_ID={domain_id} && "
        f"export ROS_LOCALHOST_ONLY=1 && "
        f"source {shlex.quote(str(ROS_SETUP))} && "
        f"source {shlex.quote(str(setup))} && "
        f"ros2 launch {paths.bringup_pkg} control_readiness.launch.py "
        f"robot_name:={paths.project_name}"
    )
    log(f"  launching headless sim (domain {domain_id})...")
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["bash", "-lc", launch_cmd],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        start_new_session=True,
    )
    result["launch_pid"] = proc.pid
    result["ros_domain_id"] = domain_id

    try:
        log("  waiting for controllers in launch log...")
        ready, ready_err = _wait_for_controllers_in_log(log_path, proc, LAUNCH_READY_TIMEOUT_S, on_log=log)
        if not ready:
            launch_log = log_path.read_text(errors="replace") if log_path.is_file() else ""
            result["errors"].append(ready_err or "Controllers did not become ready")
            result["launch_log_excerpt"] = _read_launch_log(log_path)[-3000:]
            return result

        log("  checking /joint_states...")
        if not _wait_for_publishers("/joint_states", setup, JOINT_STATES_TIMEOUT_S, env):
            launch_log = _read_launch_log(log_path)
            topic_proc = bash_ros_cmd("ros2 topic list", setup=setup, timeout=15, env=env)
            result["errors"].append("/joint_states has no publishers")
            result["launch_log_excerpt"] = launch_log[-2000:]
            result["topic_list_excerpt"] = (topic_proc.stdout or topic_proc.stderr or "")[:1000]
            return result
        result["joint_states"] = "ok"
        log("  /joint_states: OK")

        launch_log = _read_launch_log(log_path)
        controller_states = parse_controllers_from_log(launch_log)
        result["controllers"] = controller_states

        ctrl_proc = bash_ros_cmd("ros2 control list_controllers", setup=setup, timeout=25, env=env)
        for line in (ctrl_proc.stdout or "").splitlines():
            for name in REQUIRED_CONTROLLERS:
                if name in line and "active" in line.lower():
                    controller_states[name] = "active"

        for name in REQUIRED_CONTROLLERS:
            state = controller_states.get(name)
            if state not in ("active", "configured", "loaded", "inferred_active"):
                result["errors"].append(f"Controller {name} not verified active")

        if result.get("joint_states") == "ok":
            for name in REQUIRED_CONTROLLERS:
                controller_states.setdefault(name, "inferred_active")

        time.sleep(3.0)
        before = _read_joint_states(setup, env)
        joints = _joint_names_from_controllers_yaml(paths.controllers_yaml())
        probe_joint = next((j for j in joints if j in before), joints[0] if joints else None)
        if probe_joint is None or not joints:
            result["errors"].append("No actuated joints found for control probe")
            return result

        start_pos = before.get(probe_joint, 0.0)
        delta = 0.15 if abs(start_pos) < 0.1 else -0.15
        log(f"  sending control probe to {probe_joint}: {start_pos:.3f} -> {start_pos + delta:.3f}")
        ok, excerpt, target = _send_control_probe(probe_joint, joints, before, delta, setup, env)
        time.sleep(4.0)
        after = _read_joint_states(setup, env)
        moved = abs(after.get(probe_joint, start_pos) - start_pos) >= MIN_JOINT_DELTA
        result["control_probe"] = {
            "joint": probe_joint,
            "start": start_pos,
            "target": target,
            "after": after.get(probe_joint),
            "action_ok": ok,
            "moved": moved,
            "excerpt": excerpt,
        }
        if not ok and not moved:
            result["errors"].append(
                f"Control probe failed for {probe_joint}: joint did not move and action did not succeed"
            )
        elif not moved:
            result["errors"].append(
                f"Control probe for {probe_joint} did not change joint position (delta < {MIN_JOINT_DELTA})"
            )
        else:
            log(f"  control probe: OK ({probe_joint} moved)")

        result["status"] = "passed" if not result["errors"] else "failed"
        return result
    finally:
        log_file.close()
        log("  shutting down sim...")
        _stop_process(proc)
        _cleanup_sim_processes(paths.bringup_pkg)


def validate_control_runtime(
    exports_dir: Path,
    project_name: str,
    *,
    auto_build: bool = True,
    auto_generate: bool = True,
    on_log: LogFn | None = None,
) -> ValidationResult:
    """Validate control exports by spawning the robot in Gazebo via colcon workspace."""
    log = on_log or _noop_log
    paths = ControlProjectPaths.from_exports(exports_dir, project_name)
    stack = check_control_runtime_stack()
    details: dict[str, Any] = {
        "status": "failed",
        "stack": stack,
        "workspace_path": str(paths.workspace_dir),
        "project": project_name,
    }

    if not stack["available"]:
        missing = ", ".join(stack["missing"])
        return ValidationResult(
            valid=True,
            warnings=[
                _issue(
                    "warning",
                    "control_runtime_skipped",
                    f"Control runtime validation skipped (not installed): {missing}",
                )
            ],
            details={**details, "status": "skipped"},
        )

    for path in (paths.ctrl_urdf(), paths.controllers_yaml(), paths.gains_yaml()):
        if not path.is_file():
            return ValidationResult(
                valid=False,
                errors=[
                    _issue(
                        "error",
                        "missing_control_export",
                        f"Control export not found: {path}",
                        entity_type="file",
                        entity_id=str(path),
                    )
                ],
                details={**details, "status": "failed"},
            )

    workspace_ready = paths.install_setup().is_file()
    stale, changed = control_exports_stale(paths)
    if stale or not (paths.workspace_dir / "src").is_dir():
        if auto_generate:
            log("  generating control validation workspace...")
            try:
                generate_control_workspace(paths)
                workspace_ready = False
            except (FileNotFoundError, RuntimeError) as exc:
                return ValidationResult(
                    valid=False,
                    errors=[_issue("error", "workspace_generate_failed", str(exc))],
                    details={**details, "status": "failed"},
                )
        else:
            return ValidationResult(
                valid=True,
                warnings=[
                    _issue(
                        "warning",
                        "control_runtime_no_workspace",
                        "Control runtime validation skipped (workspace not generated; pass auto_generate=True)",
                    )
                ],
                details={**details, "status": "skipped", "stale_exports": changed},
            )

    if not workspace_ready and auto_build:
        build = _build_workspace(paths, on_log=log)
        details["build"] = build
        if not build.get("success"):
            return ValidationResult(
                valid=False,
                errors=[
                    _issue(
                        "error",
                        "workspace_build_failed",
                        build.get("message", "colcon build failed"),
                    )
                ],
                details={**details, "status": "failed"},
            )
    elif not paths.install_setup().is_file():
        return ValidationResult(
            valid=True,
            warnings=[
                _issue(
                    "warning",
                    "control_runtime_no_workspace",
                    f"Control runtime validation skipped (workspace not built: {paths.install_setup()})",
                )
            ],
            details={**details, "status": "skipped"},
        )

    started = time.monotonic()
    runtime = _run_runtime(paths, on_log=log)
    details.update(runtime)
    details["durationS"] = round(time.monotonic() - started, 2)
    status = runtime.get("status", "failed")
    details["status"] = status

    errors = [
        _issue("error", "control_runtime_failed", msg)
        for msg in runtime.get("errors") or []
    ]
    return ValidationResult(
        valid=status == "passed",
        errors=errors,
        details=details,
    )
