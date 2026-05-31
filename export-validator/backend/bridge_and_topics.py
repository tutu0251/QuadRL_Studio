"""Log parsing and topic helpers shared by runtime validators."""
from __future__ import annotations

import re
from typing import Any

import yaml

PLUGIN_LOADED_MARKERS = (
    "GazeboSimROS2ControlPlugin",
    "gz_ros2_control",
)
PLUGIN_FAILURE_PATTERNS = (
    re.compile(r"Failed to load system plugin", re.I),
    re.compile(r"Unable to load.*plugin", re.I),
    re.compile(r"Could not load.*plugin", re.I),
)
SPAWN_SUCCESS_MARKERS = ("OK creation of entity",)
REQUIRED_CONTROLLERS = ("joint_state_broadcaster", "joint_trajectory_controller")


def load_observations_doc(text: str) -> dict[str, Any]:
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return yaml.safe_load(text) or {}


def patch_gz_world_in_topic(topic: str, world_name: str) -> str:
    return topic.replace("/world/default/", f"/world/{world_name}/")


def bridge_to_parameter_bridge_args(bridge_doc: dict[str, Any], world_name: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for item in bridge_doc.get("bridges") or []:
        if not isinstance(item, dict):
            continue
        ros_topic = str(item.get("ros_topic", ""))
        gz_topic = str(item.get("gz_topic", ""))
        if not ros_topic or not gz_topic:
            continue
        entries.append(
            {
                "ros_topic_name": ros_topic,
                "gz_topic_name": patch_gz_world_in_topic(gz_topic, world_name),
                "ros_type_name": str(item.get("ros_type", "")),
                "gz_type_name": str(item.get("gz_type", "")),
                "direction": str(item.get("direction", "GZ_TO_ROS")),
            }
        )
    return entries


def parse_joint_states(yaml_text: str) -> dict[str, float]:
    for chunk in yaml_text.split("---"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not (chunk.startswith("header:") or chunk.startswith("name:")):
            continue
        try:
            doc = yaml.safe_load(chunk)
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        names = doc.get("name") or []
        positions = doc.get("position") or []
        if names and positions:
            return {str(name): float(pos) for name, pos in zip(names, positions, strict=False)}
    return {}


def parse_controllers_from_log(log_text: str) -> dict[str, str]:
    states: dict[str, str] = {}
    for name in REQUIRED_CONTROLLERS:
        if re.search(rf"Loading controller '{name}'", log_text):
            states[name] = "loaded"
        if re.search(rf"Configuring controller '{name}'", log_text):
            states[name] = "configured"
        if re.search(rf"Activating controller '{name}'", log_text):
            states[name] = "active"
    return states


def analyze_launch_logs(gz_log: str, spawn_log: str, spawn_rc: int) -> tuple[list[str], list[str]]:
    """Return (error_messages, warning_messages) from sim logs."""
    errors: list[str] = []
    warnings: list[str] = []
    combined = f"{gz_log}\n{spawn_log}"

    if spawn_rc != 0:
        excerpt = spawn_log.strip().splitlines()[-1] if spawn_log.strip() else f"exit code {spawn_rc}"
        errors.append(f"Spawn failed: {excerpt}")

    if spawn_rc == 0 and not any(marker in spawn_log for marker in SPAWN_SUCCESS_MARKERS):
        if "controller_manager" not in combined.lower():
            pass
        elif not any(marker in combined for marker in PLUGIN_LOADED_MARKERS):
            errors.append("gz_ros2_control plugin did not appear in simulation logs")

    for pattern in PLUGIN_FAILURE_PATTERNS:
        match = pattern.search(combined)
        if match:
            errors.append(match.group(0))
            break

    if not any(marker in combined for marker in PLUGIN_LOADED_MARKERS):
        if "controller_manager" in combined.lower() and not errors:
            pass
    elif re.search(r"robot_state_publisher service not available", combined, re.I):
        warnings.append("robot_state_publisher not ready during warmup (may recover)")

    return errors, warnings
