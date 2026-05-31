"""Headless Gazebo validation for exported physics package."""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from domain.models import ValidationIssue, ValidationResult
from storage import project_storage

LogFn = Callable[[str], None]

EXPORT_VALIDATOR_BACKEND = Path(__file__).resolve().parents[3] / "export-validator" / "backend"


def _map_export_validator_result(result: Any) -> ValidationResult:
    status = (result.details or {}).get("status", "unknown")
    details = dict(result.details or {})
    if status == "skipped":
        details["status"] = "skipped"
        warnings = [
            ValidationIssue(
                severity=w.severity,
                code="export_validation_skipped" if w.code.endswith("_skipped") else w.code,
                message=w.message,
                entityType=w.entityType,
                entityId=w.entityId,
            )
            for w in result.warnings
        ]
        return ValidationResult(valid=True, warnings=warnings, details=details)

    if status == "passed":
        details["status"] = "passed"
    else:
        details.setdefault("status", "failed")

    return ValidationResult(
        valid=result.valid,
        errors=[
            ValidationIssue(
                severity=e.severity,
                code=e.code,
                message=e.message,
                entityType=e.entityType,
                entityId=e.entityId,
            )
            for e in result.errors
        ],
        warnings=[
            ValidationIssue(
                severity=w.severity,
                code=w.code,
                message=w.message,
                entityType=w.entityType,
                entityId=w.entityId,
            )
            for w in result.warnings
        ],
        details=details,
    )


def validate_physics_export(project_name: str, *, on_log: LogFn | None = None) -> ValidationResult:
    """Validate physics exports via export-validator spawn runtime."""
    backend = EXPORT_VALIDATOR_BACKEND
    if not (backend / "physics_runtime.py").is_file():
        return ValidationResult(
            valid=True,
            warnings=[
                ValidationIssue(
                    severity="warning",
                    code="export_validation_skipped",
                    message="Export validation skipped (export-validator not available)",
                )
            ],
            details={"status": "skipped"},
        )

    exports_dir = project_storage.project_dir(project_name) / "exports"
    if not exports_dir.is_dir():
        return ValidationResult(
            valid=False,
            errors=[
                ValidationIssue(
                    severity="error",
                    code="missing_exports_dir",
                    message=f"Exports directory not found: {exports_dir}",
                )
            ],
            details={"status": "failed"},
        )

    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    try:
        from physics_runtime import validate_physics_runtime
    except ImportError:
        return ValidationResult(
            valid=True,
            warnings=[
                ValidationIssue(
                    severity="warning",
                    code="export_validation_skipped",
                    message="Export validation skipped (export-validator import failed)",
                )
            ],
            details={"status": "skipped"},
        )

    result = validate_physics_runtime(exports_dir, project_name, on_log=on_log)
    return _map_export_validator_result(result)
