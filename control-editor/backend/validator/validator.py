"""Control model validation."""
from __future__ import annotations

import re

from domain.models import ControlModel, TrainingProfile, ValidationIssue, ValidationResult


class ControlValidator:
    def __init__(self, model: ControlModel):
        self._model = model

    def validate(self) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        profile = self._model.trainingProfile
        if profile in (TrainingProfile.PROFILE_B, TrainingProfile.PROFILE_C):
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="profile_not_implemented",
                    message=f"{profile.value} is a placeholder — export is disabled",
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        joints = [j for j in self._model.actuatedJoints if j.enabled]
        if not joints:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="no_actuated_joints",
                    message="No enabled actuated joints",
                )
            )

        names: set[str] = set()
        for j in joints:
            if j.name in names:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="duplicate_joint",
                        message=f"Duplicate joint name: {j.name}",
                        entityType="joint",
                        entityId=j.name,
                    )
                )
            names.add(j.name)

            if j.effort <= 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_effort",
                        message=f"{j.name}: effort must be > 0",
                        entityType="joint",
                        entityId=j.name,
                    )
                )
            if j.velocity <= 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_velocity",
                        message=f"{j.name}: velocity must be > 0",
                        entityType="joint",
                        entityId=j.name,
                    )
                )
            if j.kp <= 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_kp",
                        message=f"{j.name}: Kp must be > 0",
                        entityType="joint",
                        entityId=j.name,
                    )
                )
            if j.kd < 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_kd",
                        message=f"{j.name}: Kd must be >= 0",
                        entityType="joint",
                        entityId=j.name,
                    )
                )
            if j.type != "continuous" and j.upperLimit <= j.lowerLimit:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_limits",
                        message=f"{j.name}: upper limit must exceed lower limit",
                        entityType="joint",
                        entityId=j.name,
                    )
                )

            if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", j.name):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="joint_name_style",
                        message=f"{j.name}: non-standard joint name",
                        entityType="joint",
                        entityId=j.name,
                    )
                )

        if not self._model.metadata.get("hasPhysicsJson", False):
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="no_physics_json",
                    message="physics_model.json not found — limits from URDF only",
                )
            )

        if not self._model.sourceUrdf:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="no_source",
                    message="No source URDF path — import phy URDF",
                )
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
