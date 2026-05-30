"""Headless Gazebo validation for exported ros2_control URDF."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, IO, Optional

from domain.models import ValidationIssue, ValidationResult

DEFAULT_WORLD_SDF = Path("/usr/share/ignition/ignition-gazebo6/worlds/empty.sdf")
DEFAULT_WORLD_NAME = "empty"
DEFAULT_TIMEOUT_S = 60
DEFAULT_SPAWN_Z = 0.5
ROS_SETUP = Path("/opt/ros/humble/setup.bash")
ROS_PLUGIN_LIB = Path("/opt/ros/humble/lib")
SIM_READY_POLL_S = 1.0
POST_SPAWN_WAIT_S = 3.0

PLUGIN_LOADED_MARKERS = (
    "GazeboSimROS2ControlPlugin",
    "gz_ros2_control",
)
PLUGIN_FAILURE_PATTERNS = (
    re.compile(r"Failed to load system plugin", re.I),
    re.compile(r"Unable to load.*plugin", re.I),
    re.compile(r"Could not load.*plugin", re.I),
)
SPAWN_SUCCESS_MARKERS = ("OK creation of entity",)
ROBOT_STATE_PUBLISHER_WARN = re.compile(
    r"robot_state_publisher service not available", re.I
)


def _issue(
    severity: str,
    code: str,
    message: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        code=code,
        message=message,
        entityType=entity_type,
        entityId=entity_id,
    )


def _bash_ros_cmd(script: str, *, timeout: Optional[float] = None) -> subprocess.CompletedProcess[str]:
    if not ROS_SETUP.is_file():
        raise FileNotFoundError(f"ROS setup not found: {ROS_SETUP}")
    return subprocess.run(
        ["bash", "-lc", f"source {shlex.quote(str(ROS_SETUP))} && {script}"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_gazebo_stack() -> dict[str, Any]:
    """Return availability info for Gazebo / ROS2 / gz_ros2_control."""
    details: dict[str, Any] = {
        "ign": shutil.which("ign") is not None,
        "rosSetup": ROS_SETUP.is_file(),
        "worldSdf": DEFAULT_WORLD_SDF.is_file(),
        "gzRos2Control": False,
        "rosGzSim": False,
        "rosIgnGazebo": False,
        "createPackage": None,
    }
    missing: list[str] = []

    if not details["ign"]:
        missing.append("ign (Gazebo Fortress CLI)")
    if not details["rosSetup"]:
        missing.append(f"ROS 2 setup ({ROS_SETUP})")
    if not details["worldSdf"]:
        missing.append(f"world SDF ({DEFAULT_WORLD_SDF})")

    if details["rosSetup"]:
        for pkg, key in (
            ("gz_ros2_control", "gzRos2Control"),
            ("ros_gz_sim", "rosGzSim"),
            ("ros_ign_gazebo", "rosIgnGazebo"),
        ):
            try:
                proc = _bash_ros_cmd(f"ros2 pkg prefix {pkg}", timeout=10)
                details[key] = proc.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                details[key] = False

    if details["rosGzSim"]:
        details["createPackage"] = "ros_gz_sim"
    elif details["rosIgnGazebo"]:
        details["createPackage"] = "ros_ign_gazebo"
    else:
        missing.append("ros_gz_sim or ros_ign_gazebo")

    if not details["gzRos2Control"]:
        missing.append("gz_ros2_control")

    details["available"] = len(missing) == 0
    details["missing"] = missing
    return details


def is_gazebo_stack_available() -> bool:
    return bool(check_gazebo_stack()["available"])


def _prepend_path_env(env: dict[str, str], key: str, prefix: str) -> None:
    """Prepend *prefix* to a colon-separated env var if not already present."""
    existing = env.get(key, "")
    parts = [p for p in existing.split(":") if p]
    if prefix not in parts:
        env[key] = f"{prefix}:{existing}" if existing else prefix


def _sim_env() -> dict[str, str]:
    env = os.environ.copy()
    prefix = str(ROS_PLUGIN_LIB)
    _prepend_path_env(env, "GZ_SIM_SYSTEM_PLUGIN_PATH", prefix)
    # gz_ros2_control pulls in ROS 2 libs (e.g. libcontroller_manager.so) at dlopen time.
    _prepend_path_env(env, "LD_LIBRARY_PATH", prefix)
    return env


def _wait_for_sim(world_name: str, gz_proc: subprocess.Popen[Any], timeout_s: float) -> tuple[bool, str]:
    service = f"/world/{world_name}/create"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if gz_proc.poll() is not None:
            return False, "Gazebo exited before the simulation was ready"
        proc = subprocess.run(
            ["ign", "service", "-s", service, "--info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "EntityFactory" in (proc.stdout or ""):
            return True, ""
        time.sleep(SIM_READY_POLL_S)
    return False, f"Timed out waiting for {service} ({int(timeout_s)}s)"


def _stop_process(proc: Optional[subprocess.Popen[Any]]) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _analyze_logs(gz_log: str, spawn_log: str, spawn_rc: int) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    combined = f"{gz_log}\n{spawn_log}"

    if spawn_rc != 0:
        excerpt = spawn_log.strip().splitlines()[-1] if spawn_log.strip() else f"exit code {spawn_rc}"
        errors.append(
            _issue(
                "error",
                "gazebo_spawn_failed",
                f"ros_gz_sim create failed: {excerpt}",
            )
        )

    if not any(marker in spawn_log for marker in SPAWN_SUCCESS_MARKERS):
        if spawn_rc == 0:
            errors.append(
                _issue(
                    "error",
                    "gazebo_spawn_no_confirm",
                    "Spawn command did not report entity creation",
                )
            )

    for pattern in PLUGIN_FAILURE_PATTERNS:
        match = pattern.search(combined)
        if match:
            errors.append(
                _issue(
                    "error",
                    "gazebo_plugin_load_failed",
                    match.group(0),
                )
            )
            break

    plugin_loaded = any(marker in combined for marker in PLUGIN_LOADED_MARKERS)
    if plugin_loaded and not any(e.code == "gazebo_plugin_load_failed" for e in errors):
        pass
    elif spawn_rc == 0 and not any(e.code.startswith("gazebo_plugin") for e in errors):
        errors.append(
            _issue(
                "error",
                "gazebo_plugin_not_detected",
                "gz_ros2_control plugin did not appear in simulation logs",
            )
        )

    if ROBOT_STATE_PUBLISHER_WARN.search(combined):
        warnings.append(
            _issue(
                "warning",
                "gazebo_no_robot_state_publisher",
                "robot_state_publisher not running (expected for headless export check)",
            )
        )

    return errors, warnings


class GazeboExportValidator:
    """Spawn exported URDF in headless Gazebo and verify gz_ros2_control loads."""

    def __init__(
        self,
        urdf_path: Path,
        model_name: str,
        *,
        world_sdf: Path = DEFAULT_WORLD_SDF,
        world_name: str = DEFAULT_WORLD_NAME,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        spawn_z: float = DEFAULT_SPAWN_Z,
    ):
        self._urdf_path = urdf_path.resolve()
        self._model_name = model_name
        self._world_sdf = world_sdf
        self._world_name = world_name
        self._timeout_s = timeout_s
        self._spawn_z = spawn_z

    def validate(self) -> ValidationResult:
        stack = check_gazebo_stack()
        if not stack["available"]:
            missing = ", ".join(stack["missing"])
            return ValidationResult(
                valid=True,
                warnings=[
                    _issue(
                        "warning",
                        "gazebo_validation_skipped",
                        f"Gazebo validation skipped (not installed): {missing}",
                    )
                ],
                details={"status": "skipped", "stack": stack},
            )

        if not self._urdf_path.is_file():
            return ValidationResult(
                valid=False,
                errors=[
                    _issue(
                        "error",
                        "missing_urdf_file",
                        f"Export URDF not found: {self._urdf_path}",
                        entity_type="file",
                        entity_id=str(self._urdf_path),
                    )
                ],
                details={"status": "failed"},
            )

        create_pkg = stack["createPackage"]
        assert create_pkg is not None

        gz_log = ""
        spawn_log = ""
        spawn_rc = 1
        gz_proc: Optional[subprocess.Popen[Any]] = None
        gz_log_handle: Optional[IO[str]] = None
        gz_log_path: Optional[Path] = None
        started = time.monotonic()
        sim_ready_timeout = min(30.0, self._timeout_s * 0.5)

        try:
            gz_log_handle = tempfile.NamedTemporaryFile(
                mode="w+",
                prefix="gz_val_",
                suffix=".log",
                delete=False,
            )
            gz_log_path = Path(gz_log_handle.name)
            gz_proc = subprocess.Popen(
                ["ign", "gazebo", "-s", str(self._world_sdf)],
                stdout=gz_log_handle,
                stderr=subprocess.STDOUT,
                env=_sim_env(),
                text=True,
            )
            gz_log_handle.close()
            gz_log_handle = None

            ready, ready_err = _wait_for_sim(self._world_name, gz_proc, sim_ready_timeout)
            if not ready:
                if gz_log_path.is_file():
                    gz_log = gz_log_path.read_text(errors="replace")
                return ValidationResult(
                    valid=False,
                    errors=[_issue("error", "gazebo_sim_not_ready", ready_err)],
                    details={
                        "status": "failed",
                        "stack": stack,
                        "durationS": round(time.monotonic() - started, 2),
                        "gazeboLogExcerpt": "\n".join(gz_log.strip().splitlines()[-15:]) if gz_log else None,
                    },
                )

            urdf_arg = shlex.quote(str(self._urdf_path))
            name_arg = shlex.quote(self._model_name)
            spawn_script = (
                f"ros2 run {create_pkg} create "
                f"-world {shlex.quote(self._world_name)} "
                f"-file {urdf_arg} "
                f"-name {name_arg} "
                f"-z {self._spawn_z} "
                f"-allow_renaming true"
            )
            spawn_proc = _bash_ros_cmd(spawn_script, timeout=30)
            spawn_log = (spawn_proc.stdout or "") + (spawn_proc.stderr or "")
            spawn_rc = spawn_proc.returncode

            time.sleep(POST_SPAWN_WAIT_S)
            if gz_log_path.is_file():
                gz_log = gz_log_path.read_text(errors="replace")

        except subprocess.TimeoutExpired:
            return ValidationResult(
                valid=False,
                errors=[
                    _issue(
                        "error",
                        "gazebo_validation_timeout",
                        f"Gazebo validation timed out after {int(self._timeout_s)}s",
                    )
                ],
                details={"status": "failed", "stack": stack},
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[
                    _issue(
                        "error",
                        "gazebo_validation_error",
                        f"Gazebo validation error: {e}",
                    )
                ],
                details={"status": "failed", "stack": stack},
            )
        finally:
            if gz_log_handle is not None:
                gz_log_handle.close()
            _stop_process(gz_proc)
            if gz_log_path is not None and gz_log_path.is_file():
                try:
                    gz_log_path.unlink()
                except OSError:
                    pass

        errors, warnings = _analyze_logs(gz_log, spawn_log, spawn_rc)
        status = "passed" if not errors else "failed"
        details: dict[str, Any] = {
            "status": status,
            "stack": stack,
            "durationS": round(time.monotonic() - started, 2),
            "modelName": self._model_name,
            "urdfPath": str(self._urdf_path),
        }
        if gz_log.strip():
            details["gazeboLogExcerpt"] = "\n".join(gz_log.strip().splitlines()[-15:])
        if spawn_log.strip():
            details["spawnLogExcerpt"] = spawn_log.strip()[-2000:]

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details=details,
        )


def validate_gazebo_export(
    urdf_path: Path,
    model_name: str,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ValidationResult:
    return GazeboExportValidator(urdf_path, model_name, timeout_s=timeout_s).validate()
