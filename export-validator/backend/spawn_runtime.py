"""Headless Gazebo spawn validation for exported URDF/SDF files."""
from __future__ import annotations

import re
import shlex
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, IO, Optional

from ev_ros_env import ROS_SETUP, bash_ros_cmd, check_spawn_stack, sim_env
from models import ValidationIssue, ValidationResult

DEFAULT_WORLD_SDF = Path("/usr/share/ignition/ignition-gazebo6/worlds/empty.sdf")
DEFAULT_WORLD_NAME = "empty"
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_SPAWN_Z = 0.0
SIM_READY_POLL_S = 1.0
POST_SPAWN_WAIT_S = 3.0

SPAWN_SUCCESS_MARKERS = ("OK creation of entity",)
SPAWN_FAILURE_PATTERNS = (
    re.compile(r"\[ERROR\]", re.I),
    re.compile(r"Unable to create entity", re.I),
    re.compile(r"Failed to parse", re.I),
)
SIM_FAILURE_PATTERNS = (
    re.compile(r"Failed to load system plugin", re.I),
    re.compile(r"Unable to load.*plugin", re.I),
    re.compile(r"Error.*SDF", re.I),
)

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


def _analyze_spawn_logs(gz_log: str, spawn_log: str, spawn_rc: int) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    combined = f"{gz_log}\n{spawn_log}"
    spawn_ok = any(marker in spawn_log for marker in SPAWN_SUCCESS_MARKERS)

    if spawn_rc != 0 and not spawn_ok:
        excerpt = spawn_log.strip().splitlines()[-1] if spawn_log.strip() else f"exit code {spawn_rc}"
        errors.append(
            _issue(
                "error",
                "spawn_failed",
                f"ros_gz_sim create failed: {excerpt}",
            )
        )

    if not spawn_ok:
        errors.append(
            _issue(
                "error",
                "spawn_no_confirm",
                "Spawn command did not report entity creation",
            )
        )
    elif spawn_rc != 0:
        warnings.append(
            _issue(
                "warning",
                "spawn_rc_nonzero",
                f"ros_gz_sim create exited with code {spawn_rc} but reported entity creation",
            )
        )

    for pattern in SPAWN_FAILURE_PATTERNS:
        match = pattern.search(spawn_log)
        if match:
            errors.append(_issue("error", "spawn_log_error", match.group(0)))
            break

    for pattern in SIM_FAILURE_PATTERNS:
        match = pattern.search(combined)
        if match:
            errors.append(_issue("error", "sim_load_failed", match.group(0)))
            break

    return errors, warnings


def validate_spawn(
    model_file: Path,
    model_name: str,
    *,
    editor: str,
    world_sdf: Path = DEFAULT_WORLD_SDF,
    world_name: str = DEFAULT_WORLD_NAME,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    spawn_z: float = DEFAULT_SPAWN_Z,
    headless: bool = True,
    env: dict[str, str] | None = None,
    on_log: LogFn | None = None,
) -> ValidationResult:
    """Spawn an exported URDF/SDF in Gazebo and verify the model loads."""
    log = on_log or _noop_log
    stack = check_spawn_stack()
    details: dict[str, Any] = {
        "status": "failed",
        "stack": stack,
        "editor": editor,
        "modelName": model_name,
        "modelFile": str(model_file.resolve()),
    }

    if not stack["available"]:
        missing = ", ".join(stack["missing"])
        return ValidationResult(
            valid=True,
            warnings=[
                _issue(
                    "warning",
                    f"{editor}_runtime_skipped",
                    f"{editor.title()} runtime validation skipped (not installed): {missing}",
                )
            ],
            details={**details, "status": "skipped"},
        )

    if not model_file.is_file():
        return ValidationResult(
            valid=False,
            errors=[
                _issue(
                    "error",
                    "missing_export_file",
                    f"Export file not found: {model_file}",
                    entity_type="file",
                    entity_id=str(model_file),
                )
            ],
            details={**details, "status": "failed"},
        )

    if not world_sdf.is_file():
        return ValidationResult(
            valid=False,
            errors=[
                _issue(
                    "error",
                    "missing_world_sdf",
                    f"World SDF not found: {world_sdf}",
                )
            ],
            details={**details, "status": "failed"},
        )

    create_pkg = stack.get("createPackage")
    if not create_pkg:
        return ValidationResult(
            valid=False,
            errors=[_issue("error", "spawn_no_create_pkg", "ros_gz_sim / ros_ign_gazebo not available")],
            details={**details, "status": "failed"},
        )

    gz_log = ""
    spawn_log = ""
    spawn_rc = 1
    gz_proc: Optional[subprocess.Popen[Any]] = None
    gz_log_handle: Optional[IO[str]] = None
    gz_log_path: Optional[Path] = None
    started = time.monotonic()
    sim_ready_timeout = min(30.0, timeout_s * 0.5)

    try:
        log("  launching headless Gazebo..." if headless else "  launching Gazebo GUI...")
        gz_log_handle = tempfile.NamedTemporaryFile(
            mode="w+",
            prefix=f"{editor}_spawn_",
            suffix=".log",
            delete=False,
        )
        gz_log_path = Path(gz_log_handle.name)
        gz_args = ["ign", "gazebo"]
        if headless:
            gz_args.append("-s")
        gz_args.append(str(world_sdf))
        run_env = sim_env(env)
        gz_proc = subprocess.Popen(
            gz_args,
            stdout=gz_log_handle,
            stderr=subprocess.STDOUT,
            env=run_env,
            text=True,
        )
        gz_log_handle.close()
        gz_log_handle = None

        ready, ready_err = _wait_for_sim(world_name, gz_proc, sim_ready_timeout)
        if not ready:
            if gz_log_path.is_file():
                gz_log = gz_log_path.read_text(errors="replace")
            return ValidationResult(
                valid=False,
                errors=[_issue("error", "sim_not_ready", ready_err)],
                details={
                    **details,
                    "status": "failed",
                    "durationS": round(time.monotonic() - started, 2),
                    "gazeboLogExcerpt": "\n".join(gz_log.strip().splitlines()[-15:]) if gz_log else None,
                },
            )

        file_arg = shlex.quote(str(model_file.resolve()))
        name_arg = shlex.quote(model_name)
        spawn_script = (
            f"ros2 run {create_pkg} create "
            f"-world {shlex.quote(world_name)} "
            f"-file {file_arg} "
            f"-name {name_arg} "
            f"-z {spawn_z} "
            f"-allow_renaming true"
        )
        log(f"  spawning {model_file.name}...")
        spawn_proc = bash_ros_cmd(spawn_script, timeout=30, env=run_env)
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
                    "spawn_timeout",
                    f"Spawn validation timed out after {int(timeout_s)}s",
                )
            ],
            details={**details, "status": "failed", "durationS": round(time.monotonic() - started, 2)},
        )
    except Exception as exc:
        return ValidationResult(
            valid=False,
            errors=[_issue("error", "spawn_error", f"Spawn validation error: {exc}")],
            details={**details, "status": "failed", "durationS": round(time.monotonic() - started, 2)},
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

    errors, warnings = _analyze_spawn_logs(gz_log, spawn_log, spawn_rc)
    status = "passed" if not errors else "failed"
    details.update(
        {
            "status": status,
            "durationS": round(time.monotonic() - started, 2),
        }
    )
    if gz_log.strip():
        details["gazeboLogExcerpt"] = "\n".join(gz_log.strip().splitlines()[-15:])
    if spawn_log.strip():
        details["spawnLogExcerpt"] = spawn_log.strip()[-2000:]

    if status == "passed":
        log(f"  spawn validation passed ({details['durationS']}s)")
    else:
        log(f"  spawn validation failed ({len(errors)} error(s))")

    return ValidationResult(
        valid=status == "passed",
        errors=errors,
        warnings=warnings,
        details=details,
    )
