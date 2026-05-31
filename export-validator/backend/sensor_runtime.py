"""Runtime validation for sensor-editor exports via colcon workspace + Gazebo."""
from __future__ import annotations

import os
import re
import shlex
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bridge_and_topics import (
    CONTROLLER_READY_MARKERS,
    observation_topics,
    parse_ros_topic_list,
    read_launch_log,
    topic_publishes,
    topic_timeout,
)
from ev_ros_env import ROS_SETUP, bash_ros_cmd, check_sensor_runtime_stack, cleanup_fastrtps_shm, load_ros_environ
from models import ValidationIssue, ValidationResult
from sensor_paths import SensorProjectPaths
from sensor_workspace import build_sensor_workspace, generate_sensor_workspace, pipeline_exports_stale

LAUNCH_READY_TIMEOUT_S = 120.0
JOINT_STATES_TIMEOUT_S = 30.0
SIM_SETTLE_S = 10.0

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


def _cleanup_sim_processes(bringup_pkg: str) -> None:
    for pattern in (
        f"{bringup_pkg} training_readiness.launch.py",
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
        if echo.returncode == 0 and ("position:" in echo_out or "name:" in echo_out or "orientation:" in echo_out):
            return True
        time.sleep(2.0)
    return False


def _wait_for_sim_ready(
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
            excerpt = read_launch_log(log_path)[-1500:]
            return False, f"Launch process exited early — see sensor_runtime_launch.log\n{excerpt}"
        text = read_launch_log(log_path)
        has_controller = any(marker in text for marker in CONTROLLER_READY_MARKERS)
        has_bridge = "parameter_bridge" in text.lower() or "ros_gz_bridge" in text.lower()
        if has_controller and has_bridge:
            elapsed = int(time.monotonic() - started)
            log(f"  sim ready ({elapsed}s)")
            return True, ""
        now = time.monotonic()
        if now - last_heartbeat >= 10.0:
            elapsed = int(now - started)
            flags = []
            if has_controller:
                flags.append("controllers")
            if has_bridge:
                flags.append("bridge")
            status = ", ".join(flags) if flags else "starting"
            log(f"  still waiting for sim ({elapsed}s, {status})...")
            last_heartbeat = now
        time.sleep(2.0)
    return False, f"Timed out waiting for sim bridge/controllers in launch log ({int(timeout_s)}s)"


def _run_sensor_runtime(paths: SensorProjectPaths, *, on_log: LogFn | None = None) -> dict[str, Any]:
    log = on_log or _noop_log
    result: dict[str, Any] = {
        "status": "failed",
        "topics": {},
        "topic_list": [],
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
    log_path = paths.workspace_dir / "sensor_runtime_launch.log"

    launch_cmd = (
        f"export ROS_DOMAIN_ID={domain_id} && "
        f"export ROS_LOCALHOST_ONLY=1 && "
        f"source {shlex.quote(str(ROS_SETUP))} && "
        f"source {shlex.quote(str(setup))} && "
        f"ros2 launch {paths.bringup_pkg} training_readiness.launch.py "
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
        log("  waiting for bridge and controllers...")
        ready, ready_err = _wait_for_sim_ready(log_path, proc, LAUNCH_READY_TIMEOUT_S, on_log=log)
        if not ready:
            result["errors"].append(ready_err or "Simulation did not become ready")
            result["launch_log_excerpt"] = read_launch_log(log_path)[-3000:]
            return result

        log("  checking /joint_states...")
        if not _wait_for_publishers("/joint_states", setup, JOINT_STATES_TIMEOUT_S, env):
            result["errors"].append("/joint_states has no publishers")
            result["launch_log_excerpt"] = read_launch_log(log_path)[-2000:]
            return result
        result["joint_states"] = "ok"

        log(f"  settling sim ({int(SIM_SETTLE_S)}s)...")
        time.sleep(SIM_SETTLE_S)

        topic_list_proc = bash_ros_cmd("ros2 topic list", setup=setup, timeout=20, env=env)
        ros_topics = parse_ros_topic_list((topic_list_proc.stdout or "") + (topic_list_proc.stderr or ""))
        result["topic_list"] = sorted(ros_topics)
        log(f"  ros2 topic list: {len(ros_topics)} topics")

        from bridge_and_topics import load_observations_doc

        obs_doc = load_observations_doc(paths.observations_yaml().read_text(encoding="utf-8"))
        expected = observation_topics(obs_doc)
        if not expected:
            result["errors"].append("No observation topics configured in observations YAML")
            return result

        log(f"  checking {len(expected)} observation topics...")
        for idx, (key, topic, kind) in enumerate(expected, start=1):
            log(f"    [{idx}/{len(expected)}] {topic}")
            if topic not in ros_topics:
                result["topics"][topic] = "missing from topic list"
                result["errors"].append(f"Topic {topic} ({key}) not in ros2 topic list")
                continue
            timeout = topic_timeout(kind)
            ok, excerpt = topic_publishes(topic, setup, timeout, env)
            result["topics"][topic] = "ok" if ok else f"failed: {excerpt}"
            if not ok:
                result["errors"].append(f"Topic {topic} ({key}) did not publish: {excerpt}")

        result["status"] = "passed" if not result["errors"] else "failed"
        return result
    finally:
        log_file.close()
        log("  shutting down sim...")
        _stop_process(proc)
        _cleanup_sim_processes(paths.bringup_pkg)


def validate_sensor_runtime(
    exports_dir: Path,
    project_name: str,
    *,
    auto_build: bool = True,
    auto_generate: bool = True,
    on_log: LogFn | None = None,
) -> ValidationResult:
    """Validate sensor exports by spawning the robot in Gazebo and checking observation topics."""
    log = on_log or _noop_log
    paths = SensorProjectPaths.from_exports(exports_dir, project_name)
    stack = check_sensor_runtime_stack()
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
                    "sensor_runtime_skipped",
                    f"Sensor runtime validation skipped (not installed): {missing}",
                )
            ],
            details={**details, "status": "skipped"},
        )

    for path in paths.required_sensor_exports():
        if not path.is_file():
            return ValidationResult(
                valid=False,
                errors=[
                    _issue(
                        "error",
                        "missing_sensor_export",
                        f"Sensor export not found: {path}",
                        entity_type="file",
                        entity_id=str(path),
                    )
                ],
                details={**details, "status": "failed"},
            )

    obs_doc_path = paths.observations_yaml()
    from bridge_and_topics import load_observations_doc

    obs_doc = load_observations_doc(obs_doc_path.read_text(encoding="utf-8"))
    if not observation_topics(obs_doc):
        return ValidationResult(
            valid=True,
            warnings=[
                _issue(
                    "warning",
                    "sensor_runtime_no_topics",
                    "Sensor runtime validation skipped (no observation topics configured)",
                )
            ],
            details={**details, "status": "skipped"},
        )

    workspace_ready = paths.install_setup().is_file()
    stale, changed = pipeline_exports_stale(paths)
    if stale or not (paths.workspace_dir / "src").is_dir():
        if auto_generate:
            log("  generating sensor validation workspace...")
            try:
                generate_sensor_workspace(paths)
                workspace_ready = False
            except FileNotFoundError as exc:
                return ValidationResult(
                    valid=False,
                    errors=[_issue("error", "workspace_generate_failed", str(exc))],
                    details={**details, "status": "failed"},
                )
            except RuntimeError as exc:
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
                        "sensor_runtime_no_workspace",
                        "Sensor runtime validation skipped (workspace not generated; pass auto_generate=True)",
                    )
                ],
                details={**details, "status": "skipped", "stale_exports": changed},
            )

    if not workspace_ready and auto_build:
        log("  colcon build --symlink-install...")
        build = build_sensor_workspace(paths)
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
                    "sensor_runtime_no_workspace",
                    f"Sensor runtime validation skipped (workspace not built: {paths.install_setup()})",
                )
            ],
            details={**details, "status": "skipped"},
        )

    started = time.monotonic()
    runtime = _run_sensor_runtime(paths, on_log=log)
    details.update(runtime)
    details["durationS"] = round(time.monotonic() - started, 2)
    status = runtime.get("status", "failed")
    details["status"] = status

    errors = [
        _issue("error", "sensor_runtime_failed", msg)
        for msg in runtime.get("errors") or []
    ]
    return ValidationResult(
        valid=status == "passed",
        errors=errors,
        details=details,
    )
