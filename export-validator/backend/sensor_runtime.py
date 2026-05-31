"""Runtime validation for sensor exports via the full training workspace."""
from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bridge_and_topics import load_observations_doc
from ev_ros_env import check_control_runtime_stack
from models import ValidationIssue, ValidationResult

WG_BACKEND = Path(__file__).resolve().parents[2] / "workspace-generator" / "backend"

LogFn = Callable[[str], None]


def _issue(severity: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(severity=severity, code=code, message=message)


def _workspace_paths(exports_dir: Path, project_name: str):
    ev_backend = str(Path(__file__).resolve().parent)
    wg_backend = str(WG_BACKEND)
    saved = sys.path[:]
    try:
        sys.path[:] = [p for p in sys.path if p not in {ev_backend, wg_backend}]
        sys.path.insert(0, wg_backend)
        from paths import ProjectPaths  # noqa: WPS433

        exports = exports_dir.expanduser().resolve()
        if exports.name == "exports" and exports.parent.name == project_name:
            return ProjectPaths(project_name, exports.parent.parent)
        return ProjectPaths(project_name)
    finally:
        sys.path[:] = saved


def _import_validate_runtime():
    ev_backend = str(Path(__file__).resolve().parent)
    wg_backend = str(WG_BACKEND)
    saved = sys.path[:]
    try:
        sys.path[:] = [p for p in sys.path if p not in {ev_backend, wg_backend}]
        sys.path.insert(0, wg_backend)
        from validator.runtime_validator import validate_runtime  # noqa: WPS433

        return validate_runtime
    finally:
        sys.path[:] = saved


def validate_sensor_runtime(
    exports_dir: Path,
    project_name: str,
    *,
    auto_build: bool = False,
    auto_generate: bool = False,
    on_log: LogFn | None = None,
) -> ValidationResult:
    """Validate sensor exports using the full colcon workspace and training_readiness launch."""
    _ = auto_build, auto_generate
    paths = _workspace_paths(exports_dir, project_name)

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
                    "sensor_runtime_skipped",
                    f"Sensor runtime validation skipped (not installed): {missing}",
                )
            ],
            details={**details, "status": "skipped"},
        )

    obs_path = paths.observations_yaml()
    if not obs_path.is_file():
        return ValidationResult(
            valid=True,
            warnings=[
                _issue(
                    "warning",
                    "sensor_runtime_no_exports",
                    f"Sensor runtime validation skipped (missing {obs_path.name})",
                )
            ],
            details={**details, "status": "skipped"},
        )

    if not paths.install_setup().is_file():
        return ValidationResult(
            valid=True,
            warnings=[
                _issue(
                    "warning",
                    "sensor_runtime_no_workspace",
                    "Sensor runtime validation skipped (workspace not built)",
                )
            ],
            details={**details, "status": "skipped"},
        )

    obs_doc = load_observations_doc(obs_path.read_text(encoding="utf-8"))
    if not obs_doc.get("observations"):
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

    started = time.monotonic()
    validate_runtime = _import_validate_runtime()
    runtime = validate_runtime(paths, on_log=on_log)
    details.update(runtime)
    details["durationS"] = round(time.monotonic() - started, 2)
    status = runtime.get("status", "failed")
    if status == "ready":
        status = "passed"
    details["status"] = status

    errors = [
        _issue("error", "sensor_runtime_failed", msg)
        for msg in runtime.get("errors") or []
    ]
    if runtime.get("status") == "skipped":
        return ValidationResult(
            valid=True,
            warnings=[_issue("warning", "sensor_runtime_skipped", errors[0].message if errors else "skipped")],
            details={**details, "status": "skipped"},
        )

    return ValidationResult(
        valid=status == "passed",
        errors=errors,
        details=details,
    )
