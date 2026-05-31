"""Runtime validation for geometry-editor exports."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from models import ValidationIssue, ValidationResult
from spawn_runtime import validate_spawn

LogFn = Callable[[str], None]


def _issue(severity: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(severity=severity, code=code, message=message)


def validate_geometry_runtime(
    exports_dir: Path,
    project_name: str,
    *,
    on_log: LogFn | None = None,
) -> ValidationResult:
    """Validate geometry exports by spawning geo_* SDF (or URDF fallback) in Gazebo."""
    exports = exports_dir.expanduser().resolve()
    sdf = exports / f"geo_{project_name}.sdf"
    urdf = exports / f"geo_{project_name}.urdf"
    if sdf.is_file():
        model_file = sdf
    elif urdf.is_file():
        model_file = urdf
    else:
        return ValidationResult(
            valid=False,
            errors=[
                _issue(
                    "error",
                    "missing_geometry_export",
                    f"Geometry export not found: {sdf} or {urdf}",
                )
            ],
            details={"status": "failed", "project": project_name},
        )

    return validate_spawn(
        model_file,
        project_name,
        editor="geometry",
        on_log=on_log,
    )
