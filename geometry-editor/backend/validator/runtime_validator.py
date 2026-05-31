"""Headless Gazebo validation for exported geometry package."""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from domain.models import ValidationIssue

LogFn = Callable[[str], None]

EXPORT_VALIDATOR_BACKEND = Path(__file__).resolve().parents[3] / "export-validator" / "backend"


class ExportValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    details: Optional[dict[str, Any]] = None


def _map_export_validator_result(result: Any) -> ExportValidationResult:
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
        return ExportValidationResult(valid=True, warnings=warnings, details=details)

    if status == "passed":
        details["status"] = "passed"
    else:
        details.setdefault("status", "failed")

    return ExportValidationResult(
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


def validate_geometry_export(exports_dir: Path, *, on_log: LogFn | None = None) -> ExportValidationResult:
    """Validate geometry exports via export-validator spawn runtime."""
    backend = EXPORT_VALIDATOR_BACKEND
    if not (backend / "geometry_runtime.py").is_file():
        return ExportValidationResult(
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

    if not exports_dir.is_dir():
        return ExportValidationResult(
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

    project_name = exports_dir.parent.name
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    try:
        from geometry_runtime import validate_geometry_runtime
    except ImportError:
        return ExportValidationResult(
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

    result = validate_geometry_runtime(exports_dir, project_name, on_log=on_log)
    return _map_export_validator_result(result)
