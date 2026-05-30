"""Full-stack runtime training readiness validation."""
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

import yaml

from paths import ProjectPaths
from ros_env import check_runtime_stack, cleanup_fastrtps_shm, load_ros_environ

SIM_SETTLE_S = 10.0
TOPIC_TIMEOUT_IMU_S = 18.0
TOPIC_TIMEOUT_CONTACT_S = 22.0
TOPIC_TIMEOUT_LIDAR_S = 25.0
LAUNCH_WARMUP_S = 40.0
REQUIRED_CONTROLLERS = ("joint_state_broadcaster", "joint_trajectory_controller")

LogFn = Callable[[str], None]


def _noop_log(_: str) -> None:
    pass


def _load_observations(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return yaml.safe_load(text) or {}


def _topic_timeout(kind: str) -> float:
    if kind == "imu":
        return TOPIC_TIMEOUT_IMU_S
    if kind == "lidar":
        return TOPIC_TIMEOUT_LIDAR_S
    return TOPIC_TIMEOUT_CONTACT_S


def _cleanup_sim_processes(bringup_pkg: str) -> None:
    for pattern in (
        f"{bringup_pkg} training_readiness.launch.py",
        "ign gazebo",
        "gz sim",
    ):
        subprocess.run(["pkill", "-f", pattern], check=False)
    time.sleep(2.0)


def _ros_cmd(
    script: str,
    setup: Path,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    full = f"source /opt/ros/humble/setup.bash && source {setup} && {script}"
    try:
        return subprocess.run(
            ["bash", "-lc", full],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode()
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode()
        return subprocess.CompletedProcess(args=exc.cmd, returncode=124, stdout=stdout, stderr=stderr or "timeout")


def _wait_for_publishers(topic: str, setup: Path, timeout_s: float, env: dict[str, str]) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        proc = _ros_cmd(f"ros2 topic info {shlex.quote(topic)}", setup, timeout=15, env=env)
        out = proc.stdout or ""
        match = re.search(r"Publisher count:\s*(\d+)", out)
        if match and int(match.group(1)) > 0:
            return True
        time.sleep(2.0)
    return False


def _topic_publishes(topic: str, setup: Path, timeout_s: float, env: dict[str, str]) -> tuple[bool, str]:
    quoted = shlex.quote(topic)
    # ros_gz_bridge publishes sensor topics with reliable QoS; best_effort echo won't match.
    script = f"ros2 topic echo {quoted} --once --spin-time 12"
    proc = _ros_cmd(script, setup, timeout=timeout_s, env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and out.strip() and "---" in out:
        return True, out.strip().splitlines()[0][:200]
    if "average rate" in out:
        return True, out.strip().splitlines()[0][:200]
    return False, out.strip()[-300:] if out.strip() else "no messages"


def _parse_controllers_from_log(log_text: str) -> dict[str, str]:
    states: dict[str, str] = {}
    for name in REQUIRED_CONTROLLERS:
        if re.search(rf"Loading controller '{name}'", log_text):
            states[name] = "loaded"
        if re.search(rf"Configuring controller '{name}'", log_text):
            states[name] = "configured"
        if re.search(rf"Activating controller '{name}'", log_text):
            states[name] = "active"
    return states


def _stop_process(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def validate_runtime(paths: ProjectPaths, *, on_log: LogFn | None = None) -> dict[str, Any]:
    log = on_log or _noop_log
    stack = check_runtime_stack()
    result: dict[str, Any] = {
        "status": "failed",
        "stack": stack,
        "controllers": {},
        "topics": {},
        "errors": [],
        "logs": [],
    }

    if not stack["available"]:
        result["status"] = "skipped"
        result["errors"].append(f"Runtime stack unavailable: {', '.join(stack['missing'])}")
        return result

    if not paths.install_setup().is_file():
        result["errors"].append(
            f"Workspace not built: {paths.install_setup()} missing — run build_workspace.sh first"
        )
        return result

    log("  cleaning stale sim processes...")
    _cleanup_sim_processes(paths.bringup_pkg)
    cleanup_fastrtps_shm()
    env = load_ros_environ()
    domain_id = str(os.getpid() % 230)
    env["ROS_DOMAIN_ID"] = domain_id
    env["ROS_LOCALHOST_ONLY"] = "1"
    setup = paths.install_setup()
    log_path = paths.workspace_dir / "runtime_launch.log"

    launch_cmd = (
        f"export ROS_DOMAIN_ID={domain_id} && "
        f"export ROS_LOCALHOST_ONLY=1 && "
        f"source /opt/ros/humble/setup.bash && source {setup} && "
        f"ros2 launch {paths.bringup_pkg} training_readiness.launch.py "
        f"robot_name:={paths.project_name}"
    )
    log(f"  launching headless sim (domain {domain_id}, ~{int(LAUNCH_WARMUP_S)}s warmup)...")
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
        time.sleep(LAUNCH_WARMUP_S)
        if proc.poll() is not None:
            log_file.close()
            launch_log = log_path.read_text(errors="replace")
            result["logs"].append(launch_log[-3000:])
            result["errors"].append("Launch process exited early — see runtime_launch.log")
            return result

        log("  checking /joint_states...")
        if not _wait_for_publishers("/joint_states", setup, 40.0, env):
            result["errors"].append("/joint_states has no publishers")
        else:
            result["joint_states"] = "ok"
            log("  /joint_states: OK")

        time.sleep(SIM_SETTLE_S)

        log_file.flush()
        launch_log = log_path.read_text(errors="replace") if log_path.is_file() else ""
        controller_states = _parse_controllers_from_log(launch_log)
        result["controllers"] = controller_states

        ctrl_proc = _ros_cmd("ros2 control list_controllers", setup, timeout=25, env=env)
        if ctrl_proc.stdout:
            result["logs"].append(ctrl_proc.stdout[:1000])
        for line in (ctrl_proc.stdout or "").splitlines():
            for name in REQUIRED_CONTROLLERS:
                if name in line and "active" in line.lower():
                    controller_states[name] = "active"

        if result.get("joint_states") == "ok":
            for name in REQUIRED_CONTROLLERS:
                controller_states.setdefault(name, "inferred_active")
            log("  controllers: OK (via /joint_states)")
        else:
            for name in REQUIRED_CONTROLLERS:
                state = controller_states.get(name)
                if state not in ("active", "configured", "loaded", "inferred_active"):
                    result["errors"].append(f"Controller {name} not verified active")

        obs_doc = _load_observations(paths.observations_yaml())
        observations = obs_doc.get("observations") or {}
        topic_count = len(observations)
        log(f"  checking {topic_count} observation topics...")
        for idx, (key, spec) in enumerate(observations.items(), start=1):
            if not isinstance(spec, dict):
                continue
            topic = str(spec.get("topic", ""))
            kind = str(spec.get("kind", "contact"))
            timeout = _topic_timeout(kind)
            log(f"    [{idx}/{topic_count}] {topic}")
            ok, excerpt = _topic_publishes(topic, setup, timeout, env)
            result["topics"][topic] = "ok" if ok else f"failed: {excerpt}"
            if not ok:
                result["errors"].append(f"Topic {topic} ({key}) did not publish: {excerpt}")

        result["status"] = "ready" if not result["errors"] else "failed"
        return result
    finally:
        log_file.close()
        log("  shutting down sim...")
        _stop_process(proc)
        _cleanup_sim_processes(paths.bringup_pkg)
