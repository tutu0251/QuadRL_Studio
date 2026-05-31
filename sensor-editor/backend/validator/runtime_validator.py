"""Headless Gazebo validation for exported sensor RL package."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from domain.models import ValidationIssue, ValidationResult
from storage import project_storage

EXPORT_VALIDATOR_BACKEND = Path(__file__).resolve().parents[3] / "export-validator" / "backend"


def _map_export_validator_result(result: Any) -> ValidationResult:
    status = (result.details or {}).get("status", "unknown")
    details = dict(result.details or {})
    if status == "skipped":
        details["status"] = "skipped"
        warnings = [
            ValidationIssue(
                severity=w.severity,
                code="sensor_validation_skipped" if w.code.endswith("_skipped") else w.code,
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


def validate_sensor_export(project_name: str) -> ValidationResult:
    """Validate sensor exports via export-validator workspace runtime."""
    backend = EXPORT_VALIDATOR_BACKEND
    if not (backend / "sensor_runtime.py").is_file():
        return ValidationResult(
            valid=True,
            warnings=[
                ValidationIssue(
                    severity="warning",
                    code="sensor_validation_skipped",
                    message="Sensor runtime validation skipped (export-validator not available)",
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
        from sensor_runtime import validate_sensor_runtime
    except ImportError:
        return ValidationResult(
            valid=True,
            warnings=[
                ValidationIssue(
                    severity="warning",
                    code="sensor_validation_skipped",
                    message="Sensor runtime validation skipped (export-validator import failed)",
                )
            ],
            details={"status": "skipped"},
        )

    result = validate_sensor_runtime(
        exports_dir,
        project_name,
        auto_build=True,
        auto_generate=True,
    )
    return _map_export_validator_result(result)
