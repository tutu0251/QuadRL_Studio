"""Shared validation result types for export-validator."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    severity: str
    code: str
    message: str
    entityType: Optional[str] = None
    entityId: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    details: Optional[dict[str, Any]] = None
