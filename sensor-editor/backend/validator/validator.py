"""Sensor model validation."""
from __future__ import annotations

import re

from domain.models import SensorModel, ValidationIssue, ValidationResult
from storage import project_storage


class SensorValidator:
    def __init__(self, model: SensorModel):
        self._model = model

    def validate(self) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        if not self._model.sourceCtrlUrdf:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="no_source",
                    message="No source ctrl URDF — import ctrl package first",
                )
            )
        elif not project_storage.ctrl_urdf_path(self._model.projectName).is_file():
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="ctrl_urdf_missing",
                    message="ctrl_*_ros2_control.urdf not found on disk",
                )
            )

        if not self._model.linkNames:
            warnings.append(
                ValidationIssue(
                    severity="warning",
                    code="no_links",
                    message="No links loaded — re-import ctrl URDF",
                )
            )

        enabled = [s for s in self._model.sensors if s.enabled]
        if not enabled:
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="no_sensors",
                    message="No enabled sensors — add at least one sensor",
                )
            )

        names: set[str] = set()
        topics: set[str] = set()
        link_set = set(self._model.linkNames)

        for s in enabled:
            if s.name in names:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="duplicate_sensor_name",
                        message=f"Duplicate sensor name: {s.name}",
                        entityType="sensor",
                        entityId=s.id,
                    )
                )
            names.add(s.name)

            if not s.rosTopic or not s.rosTopic.startswith("/"):
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_ros_topic",
                        message=f"{s.name}: rosTopic must be absolute (start with /)",
                        entityType="sensor",
                        entityId=s.id,
                    )
                )
            elif s.rosTopic in topics:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="duplicate_ros_topic",
                        message=f"Duplicate ROS topic: {s.rosTopic}",
                        entityType="sensor",
                        entityId=s.id,
                    )
                )
            topics.add(s.rosTopic)

            if s.parentLink not in link_set:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="unknown_link",
                        message=f"{s.name}: parent link '{s.parentLink}' not in URDF",
                        entityType="sensor",
                        entityId=s.id,
                    )
                )

            if s.updateRate <= 0:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        code="invalid_rate",
                        message=f"{s.name}: update rate must be > 0",
                        entityType="sensor",
                        entityId=s.id,
                    )
                )

            if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", s.name):
                warnings.append(
                    ValidationIssue(
                        severity="warning",
                        code="sensor_name_style",
                        message=f"{s.name}: non-standard Gazebo sensor name",
                        entityType="sensor",
                        entityId=s.id,
                    )
                )

        if not self._model.topicPrefix.startswith("/"):
            errors.append(
                ValidationIssue(
                    severity="error",
                    code="invalid_topic_prefix",
                    message="topicPrefix must start with /",
                )
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
