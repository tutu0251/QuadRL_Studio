"""Validate exported ros2_control artifacts on disk."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

import yaml

from domain.models import (
    DEFAULT_HARDWARE_PLUGIN,
    DEFAULT_SIM_PLUGIN_CLASS,
    DEFAULT_SIM_PLUGIN_FILENAME,
    SIM_CONTROLLER_JOINT_TRAJECTORY,
    ControlModel,
    ValidationIssue,
    ValidationResult,
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


def _float_eq(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


class ExportValidator:
    """Validate URDF + YAML files produced by ros2_control export."""

    def __init__(
        self,
        model: ControlModel,
        urdf_path: Path,
        controllers_path: Path,
        gains_path: Path,
    ):
        self._model = model
        self._urdf_path = urdf_path
        self._controllers_path = controllers_path
        self._gains_path = gains_path

    def validate(self) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        details: dict[str, Any] = {
            "expectedJointCount": 0,
            "urdfJointCount": 0,
            "controllerJointCount": 0,
            "gainsJointCount": 0,
        }

        expected = [j for j in self._model.actuatedJoints if j.enabled]
        expected_names = [j.name for j in expected]
        details["expectedJointCount"] = len(expected)

        for label, path in (
            ("urdf", self._urdf_path),
            ("controllers", self._controllers_path),
            ("gains", self._gains_path),
        ):
            if not path.is_file():
                errors.append(
                    _issue(
                        "error",
                        f"missing_{label}_file",
                        f"Export file not found: {path}",
                        entity_type="file",
                        entity_id=str(path),
                    )
                )

        if errors:
            return ValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                details=details,
            )

        self._validate_urdf(expected, errors, warnings, details)
        self._validate_controllers(expected_names, errors, warnings, details)
        self._validate_gains(expected, errors, warnings, details)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            details=details,
        )

    def _validate_urdf(
        self,
        expected: list,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        details: dict[str, Any],
    ) -> None:
        try:
            tree = ET.parse(self._urdf_path)
            root = tree.getroot()
        except ET.ParseError as e:
            errors.append(
                _issue(
                    "error",
                    "urdf_xml_parse",
                    f"URDF is not well-formed XML: {e}",
                    entity_type="file",
                    entity_id=str(self._urdf_path),
                )
            )
            return

        rc_blocks = root.findall("ros2_control")
        if not rc_blocks:
            errors.append(
                _issue("error", "urdf_no_ros2_control", "URDF missing ros2_control block")
            )
            return
        if len(rc_blocks) > 1:
            warnings.append(
                _issue(
                    "warning",
                    "urdf_multiple_ros2_control",
                    f"URDF has {len(rc_blocks)} ros2_control blocks; validating first only",
                )
            )

        rc = rc_blocks[0]
        hardware = rc.find("hardware")
        if hardware is None:
            errors.append(
                _issue("error", "urdf_no_hardware", "ros2_control block missing hardware")
            )
        else:
            plugin = hardware.find("plugin")
            plugin_text = (plugin.text or "").strip() if plugin is not None else ""
            if plugin_text != self._model.hardwarePlugin:
                errors.append(
                    _issue(
                        "error",
                        "urdf_hardware_plugin",
                        f"Hardware plugin expected {self._model.hardwarePlugin!r}, got {plugin_text!r}",
                    )
                )
            if plugin_text != DEFAULT_HARDWARE_PLUGIN:
                warnings.append(
                    _issue(
                        "warning",
                        "urdf_non_default_hardware",
                        f"Hardware plugin is {plugin_text!r}, expected {DEFAULT_HARDWARE_PLUGIN!r}",
                    )
                )

        urdf_joints: dict[str, ET.Element] = {}
        for jel in rc.findall("joint"):
            name = jel.get("name")
            if not name:
                errors.append(_issue("error", "urdf_joint_no_name", "ros2_control joint missing name"))
                continue
            if name in urdf_joints:
                errors.append(
                    _issue(
                        "error",
                        "urdf_duplicate_joint",
                        f"Duplicate ros2_control joint: {name}",
                        entity_type="joint",
                        entity_id=name,
                    )
                )
            urdf_joints[name] = jel

        details["urdfJointCount"] = len(urdf_joints)
        expected_by_name = {j.name: j for j in expected}
        missing = set(expected_by_name) - set(urdf_joints)
        extra = set(urdf_joints) - set(expected_by_name)
        for name in sorted(missing):
            errors.append(
                _issue(
                    "error",
                    "urdf_missing_joint",
                    f"URDF ros2_control missing joint: {name}",
                    entity_type="joint",
                    entity_id=name,
                )
            )
        for name in sorted(extra):
            errors.append(
                _issue(
                    "error",
                    "urdf_extra_joint",
                    f"URDF ros2_control has unexpected joint: {name}",
                    entity_type="joint",
                    entity_id=name,
                )
            )

        for j in expected:
            jel = urdf_joints.get(j.name)
            if jel is None:
                continue
            cmd = jel.find("command_interface")
            if cmd is None:
                errors.append(
                    _issue(
                        "error",
                        "urdf_no_command_interface",
                        f"{j.name}: missing command_interface",
                        entity_type="joint",
                        entity_id=j.name,
                    )
                )
                continue
            iface = cmd.get("name", "")
            if iface != j.commandInterface:
                errors.append(
                    _issue(
                        "error",
                        "urdf_command_interface",
                        f"{j.name}: command_interface expected {j.commandInterface!r}, got {iface!r}",
                        entity_type="joint",
                        entity_id=j.name,
                    )
                )
            elif iface != "position":
                warnings.append(
                    _issue(
                        "warning",
                        "urdf_non_position_interface",
                        f"{j.name}: command_interface is {iface!r}, not position",
                        entity_type="joint",
                        entity_id=j.name,
                    )
                )

            params = {p.get("name"): (p.text or "").strip() for p in cmd.findall("param")}
            for key, model_val in (("kp", j.kp), ("kd", j.kd)):
                if key not in params:
                    errors.append(
                        _issue(
                            "error",
                            f"urdf_missing_{key}",
                            f"{j.name}: command_interface missing {key} param",
                            entity_type="joint",
                            entity_id=j.name,
                        )
                    )
                    continue
                try:
                    file_val = float(params[key])
                except ValueError:
                    errors.append(
                        _issue(
                            "error",
                            f"urdf_invalid_{key}",
                            f"{j.name}: invalid {key} value {params[key]!r}",
                            entity_type="joint",
                            entity_id=j.name,
                        )
                    )
                    continue
                if not _float_eq(file_val, model_val):
                    errors.append(
                        _issue(
                            "error",
                            f"urdf_{key}_mismatch",
                            f"{j.name}: {key}={file_val}, model has {model_val}",
                            entity_type="joint",
                            entity_id=j.name,
                        )
                    )

        self._validate_gazebo_plugin(root, errors)

    def _validate_gazebo_plugin(self, root: ET.Element, errors: list[ValidationIssue]) -> None:
        controllers_name = self._controllers_path.name
        found = False
        for gz in root.findall("gazebo"):
            plug = gz.find("plugin")
            if plug is None:
                continue
            fn = plug.get("filename", "")
            cls = plug.get("name", "")
            if "ros2_control" not in fn and "ros2_control" not in cls:
                continue
            found = True
            if fn != DEFAULT_SIM_PLUGIN_FILENAME:
                errors.append(
                    _issue(
                        "error",
                        "gazebo_plugin_filename",
                        f"Gazebo plugin filename expected {DEFAULT_SIM_PLUGIN_FILENAME!r}, got {fn!r}",
                    )
                )
            if cls != DEFAULT_SIM_PLUGIN_CLASS:
                errors.append(
                    _issue(
                        "error",
                        "gazebo_plugin_class",
                        f"Gazebo plugin class expected {DEFAULT_SIM_PLUGIN_CLASS!r}, got {cls!r}",
                    )
                )
            params = plug.find("parameters")
            params_text = (params.text or "").strip() if params is not None else ""
            if params_text != controllers_name:
                errors.append(
                    _issue(
                        "error",
                        "gazebo_plugin_parameters",
                        f"Gazebo plugin parameters expected {controllers_name!r}, got {params_text!r}",
                    )
                )
        if not found:
            errors.append(
                _issue(
                    "error",
                    "gazebo_plugin_missing",
                    "URDF missing gz_ros2_control Gazebo plugin",
                )
            )

    def _validate_controllers(
        self,
        expected_names: list[str],
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        details: dict[str, Any],
    ) -> None:
        try:
            data = yaml.safe_load(self._controllers_path.read_text())
        except yaml.YAMLError as e:
            errors.append(
                _issue(
                    "error",
                    "controllers_yaml_parse",
                    f"controllers.yaml parse error: {e}",
                    entity_type="file",
                    entity_id=str(self._controllers_path),
                )
            )
            return

        if not isinstance(data, dict):
            errors.append(
                _issue("error", "controllers_yaml_root", "controllers.yaml root must be a mapping")
            )
            return

        ctrl_name = (
            "joint_trajectory_controller"
            if self._model.controllerType == SIM_CONTROLLER_JOINT_TRAJECTORY
            else "position_controller"
        )
        cm = data.get("controller_manager") or {}
        cm_params = cm.get("ros__parameters") or {}
        if ctrl_name not in cm_params:
            errors.append(
                _issue(
                    "error",
                    "controllers_missing_controller",
                    f"controller_manager missing {ctrl_name} entry",
                )
            )

        ctrl_block = data.get(ctrl_name) or {}
        ros_params = ctrl_block.get("ros__parameters") or {}
        joints = ros_params.get("joints")
        if not isinstance(joints, list):
            errors.append(
                _issue(
                    "error",
                    "controllers_joints_missing",
                    f"{ctrl_name}.ros__parameters.joints must be a list",
                )
            )
            return

        details["controllerJointCount"] = len(joints)
        if list(joints) != expected_names:
            errors.append(
                _issue(
                    "error",
                    "controllers_joints_mismatch",
                    f"Controller joint list ({len(joints)}) does not match model ({len(expected_names)})",
                )
            )

        cmd_ifaces = ros_params.get("command_interfaces")
        if self._model.controllerType == SIM_CONTROLLER_JOINT_TRAJECTORY:
            if cmd_ifaces != ["position"]:
                errors.append(
                    _issue(
                        "error",
                        "controllers_command_interfaces",
                        f"joint_trajectory_controller command_interfaces expected ['position'], got {cmd_ifaces!r}",
                    )
                )
        else:
            iface = ros_params.get("interface_name")
            if iface != "position":
                errors.append(
                    _issue(
                        "error",
                        "controllers_interface_name",
                        f"Forward controller interface_name expected 'position', got {iface!r}",
                    )
                )

        update_rate = cm_params.get("update_rate")
        if update_rate != self._model.updateRate:
            warnings.append(
                _issue(
                    "warning",
                    "controllers_update_rate",
                    f"update_rate is {update_rate!r}, model has {self._model.updateRate}",
                )
            )

    def _validate_gains(
        self,
        expected: list,
        errors: list[ValidationIssue],
        warnings: list[ValidationIssue],
        details: dict[str, Any],
    ) -> None:
        try:
            data = yaml.safe_load(self._gains_path.read_text())
        except yaml.YAMLError as e:
            errors.append(
                _issue(
                    "error",
                    "gains_yaml_parse",
                    f"gains.yaml parse error: {e}",
                    entity_type="file",
                    entity_id=str(self._gains_path),
                )
            )
            return

        if not isinstance(data, dict):
            errors.append(_issue("error", "gains_yaml_root", "gains.yaml root must be a mapping"))
            return

        joints_block = data.get("joints")
        if not isinstance(joints_block, dict):
            errors.append(_issue("error", "gains_joints_missing", "gains.yaml missing joints mapping"))
            return

        details["gainsJointCount"] = len(joints_block)
        expected_by_name = {j.name: j for j in expected}
        for name in sorted(set(expected_by_name) - set(joints_block)):
            errors.append(
                _issue(
                    "error",
                    "gains_missing_joint",
                    f"gains.yaml missing joint: {name}",
                    entity_type="joint",
                    entity_id=name,
                )
            )
        for name in sorted(set(joints_block) - set(expected_by_name)):
            errors.append(
                _issue(
                    "error",
                    "gains_extra_joint",
                    f"gains.yaml has unexpected joint: {name}",
                    entity_type="joint",
                    entity_id=name,
                )
            )

        for j in expected:
            entry = joints_block.get(j.name)
            if not isinstance(entry, dict):
                continue
            for key, model_val in (("kp", j.kp), ("kd", j.kd)):
                if key not in entry:
                    errors.append(
                        _issue(
                            "error",
                            f"gains_missing_{key}",
                            f"{j.name}: gains.yaml missing {key}",
                            entity_type="joint",
                            entity_id=j.name,
                        )
                    )
                    continue
                file_val = entry[key]
                if not isinstance(file_val, (int, float)):
                    errors.append(
                        _issue(
                            "error",
                            f"gains_invalid_{key}",
                            f"{j.name}: invalid {key} value {file_val!r}",
                            entity_type="joint",
                            entity_id=j.name,
                        )
                    )
                    continue
                if not _float_eq(float(file_val), model_val):
                    errors.append(
                        _issue(
                            "error",
                            f"gains_{key}_mismatch",
                            f"{j.name}: {key}={file_val}, model has {model_val}",
                            entity_type="joint",
                            entity_id=j.name,
                        )
                    )

        profile = data.get("profile")
        if profile != self._model.trainingProfile.value:
            warnings.append(
                _issue(
                    "warning",
                    "gains_profile_mismatch",
                    f"gains profile is {profile!r}, model has {self._model.trainingProfile.value!r}",
                )
            )


def validate_export_files(
    model: ControlModel,
    urdf_path: Path,
    controllers_path: Path,
    gains_path: Path,
) -> ValidationResult:
    return ExportValidator(model, urdf_path, controllers_path, gains_path).validate()
