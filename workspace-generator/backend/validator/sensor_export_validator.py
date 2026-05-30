"""Validate sensor-editor RL export artifacts on disk."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from generator.bridge_args import load_bridge_doc, observation_topics
from generator.urdf_patch import gazebo_effective_link
from paths import ProjectPaths

_KNOWN_BRIDGE_TYPES = {
    "imu": ("sensor_msgs/msg/Imu", "gz.msgs.IMU"),
    "contact": ("ros_gz_interfaces/msg/Contacts", "gz.msgs.Contacts"),
    "lidar": ("sensor_msgs/msg/LaserScan", "gz.msgs.LaserScan"),
}

_MSG_TYPE_TO_BRIDGE = {
    "sensor_msgs/Imu": "sensor_msgs/msg/Imu",
    "ros_gz_interfaces/Contacts": "ros_gz_interfaces/msg/Contacts",
    "sensor_msgs/LaserScan": "sensor_msgs/msg/LaserScan",
}


def _load_observations(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    doc = yaml.safe_load(text) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid observations YAML: {path}")
    return doc


def _fixed_joint_parent_map(urdf_root: ET.Element) -> dict[str, str]:
    parents: dict[str, str] = {}
    for joint in urdf_root.findall("joint"):
        if joint.get("type") != "fixed":
            continue
        parent = joint.find("parent")
        child = joint.find("child")
        if parent is None or child is None:
            continue
        parent_link = parent.get("link")
        child_link = child.get("link")
        if parent_link and child_link:
            parents[child_link] = parent_link
    return parents


def _urdf_sensor_names(urdf_root: ET.Element) -> set[str]:
    names: set[str] = set()
    for gz in urdf_root.findall("gazebo"):
        for sensor in gz.findall("sensor"):
            name = sensor.get("name")
            if name:
                names.add(name)
    return names


def _urdf_link_names(urdf_root: ET.Element) -> set[str]:
    return {link.get("name") for link in urdf_root.findall("link") if link.get("name")}


def validate_sensor_exports(paths: ProjectPaths) -> dict[str, Any]:
    """Validate sens_* RL export files from the sensor editor."""
    errors: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {
        "sensor_count": 0,
        "bridge_entry_count": 0,
        "observation_count": 0,
    }

    required = [
        ("rl_urdf", paths.sens_rl_urdf()),
        ("bridge", paths.bridge_yaml()),
        ("observations", paths.observations_yaml()),
        ("controllers", paths.controllers_yaml()),
        ("gains", paths.gains_yaml()),
    ]
    for label, path in required:
        if not path.is_file():
            errors.append(f"Missing sensor export ({label}): {path}")
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "details": details}

    try:
        urdf_root = ET.parse(paths.sens_rl_urdf()).getroot()
    except ET.ParseError as exc:
        return {
            "valid": False,
            "errors": [f"Invalid sens RL URDF XML: {exc}"],
            "warnings": warnings,
            "details": details,
        }

    urdf_sensors = _urdf_sensor_names(urdf_root)
    urdf_links = _urdf_link_names(urdf_root)
    fixed_parents = _fixed_joint_parent_map(urdf_root)
    details["urdf_sensor_count"] = len(urdf_sensors)

    if not urdf_sensors:
        errors.append("sens RL URDF has no Gazebo sensor blocks")

    plugin_ok = False
    for gz in urdf_root.findall("gazebo"):
        plugin = gz.find("plugin")
        if plugin is None:
            continue
        fn = plugin.get("filename", "")
        name = plugin.get("name", "")
        if "gz_ros2_control" in fn or "GazeboSimROS2ControlPlugin" in name:
            plugin_ok = True
            break
    if not plugin_ok:
        errors.append("sens RL URDF missing gz_ros2_control Gazebo plugin")

    try:
        bridge_doc = load_bridge_doc(paths.bridge_yaml())
    except (ValueError, yaml.YAMLError) as exc:
        return {
            "valid": False,
            "errors": [f"Invalid bridge YAML: {exc}"],
            "warnings": warnings,
            "details": details,
        }

    try:
        obs_doc = _load_observations(paths.observations_yaml())
    except (ValueError, yaml.YAMLError) as exc:
        return {
            "valid": False,
            "errors": [f"Invalid observations YAML: {exc}"],
            "warnings": warnings,
            "details": details,
        }

    bridge_entries = bridge_doc.get("bridge") or []
    if not bridge_entries:
        errors.append("Bridge YAML has no bridge entries")
    details["bridge_entry_count"] = len(bridge_entries)

    gz_model = str(obs_doc.get("gz_model_name") or bridge_doc.get("config", {}).get("gz_model_name") or "")
    robot_name = str(obs_doc.get("robot_name") or paths.project_name)
    if gz_model and gz_model != paths.project_name:
        warnings.append(
            f"gz_model_name '{gz_model}' differs from project name '{paths.project_name}' "
            "(spawn uses project name by default)"
        )
    if robot_name != paths.project_name:
        warnings.append(f"observations robot_name '{robot_name}' differs from project '{paths.project_name}'")

    control = obs_doc.get("control") or {}
    for key in ("controllers_yaml", "gains_yaml"):
        rel = control.get(key)
        if not rel:
            errors.append(f"observations YAML missing control.{key}")
            continue
        resolved = paths.exports_dir / str(rel)
        if not resolved.is_file():
            errors.append(f"observations control.{key} not found: {resolved}")

    sim_urdf = obs_doc.get("sim_urdf")
    if sim_urdf and sim_urdf != paths.sens_rl_urdf().name:
        warnings.append(f"observations sim_urdf '{sim_urdf}' does not match export filename")

    observations = obs_doc.get("observations") or {}
    details["observation_count"] = len(observations)
    if not observations:
        errors.append("observations YAML has no observation entries")

    bridge_by_ros: dict[str, dict] = {}
    bridge_ros_topics: set[str] = set()
    for entry in bridge_entries:
        if not isinstance(entry, dict):
            errors.append("Bridge entry is not a mapping")
            continue
        ros_topic = str(entry.get("ros_topic_name") or "")
        gz_topic = str(entry.get("gz_topic_name") or "")
        if not ros_topic.startswith("/"):
            errors.append(f"Bridge ros_topic_name must be absolute: {ros_topic!r}")
        if ros_topic in bridge_ros_topics:
            errors.append(f"Duplicate bridge ros_topic_name: {ros_topic}")
        bridge_ros_topics.add(ros_topic)
        if ros_topic:
            bridge_by_ros[ros_topic] = entry

        parent_link = entry.get("parent_link")
        if parent_link and parent_link not in urdf_links:
            errors.append(f"Bridge parent_link not in URDF: {parent_link}")

        sensor_name = entry.get("sensor_name")
        if sensor_name and sensor_name not in urdf_sensors:
            errors.append(f"Bridge sensor_name not in URDF Gazebo sensors: {sensor_name}")

        if gz_model and gz_topic and f"/model/{gz_model}/" not in gz_topic:
            warnings.append(f"Bridge gz_topic may use wrong model name: {gz_topic}")

        if parent_link and gz_topic:
            effective = gazebo_effective_link(str(parent_link), fixed_parents)
            if effective != parent_link and f"/link/{parent_link}/" in gz_topic:
                warnings.append(
                    f"Bridge gz_topic uses child link '{parent_link}' "
                    f"(Gazebo merges to '{effective}'); workspace generator will patch"
                )

    for topic in observation_topics(obs_doc):
        if topic not in bridge_ros_topics:
            errors.append(f"Observation topic not in bridge config: {topic}")

    obs_topics: set[str] = set()
    for key, spec in observations.items():
        if not isinstance(spec, dict):
            errors.append(f"Observation '{key}' is not a mapping")
            continue
        topic = str(spec.get("topic") or "")
        kind = str(spec.get("kind") or "")
        if not topic.startswith("/"):
            errors.append(f"Observation '{key}' topic must be absolute: {topic!r}")
        if topic in obs_topics:
            errors.append(f"Duplicate observation topic: {topic}")
        obs_topics.add(topic)

        rate = spec.get("rate_hz")
        if rate is not None and float(rate) <= 0:
            errors.append(f"Observation '{key}' rate_hz must be > 0")

        parent_link = spec.get("parent_link")
        if parent_link and parent_link not in urdf_links:
            errors.append(f"Observation '{key}' parent_link not in URDF: {parent_link}")

        expected_types = _KNOWN_BRIDGE_TYPES.get(kind)
        if expected_types:
            bridge_entry = bridge_by_ros.get(topic)
            if bridge_entry:
                ros_type = bridge_entry.get("ros_type_name")
                gz_type = bridge_entry.get("gz_type_name")
                if ros_type != expected_types[0] or gz_type != expected_types[1]:
                    errors.append(
                        f"Bridge types for '{key}' ({ros_type}, {gz_type}) "
                        f"do not match kind '{kind}' ({expected_types[0]}, {expected_types[1]})"
                    )
            msg_type = spec.get("msg_type")
            bridge_ros = _MSG_TYPE_TO_BRIDGE.get(str(msg_type or ""))
            if bridge_ros and bridge_ros != expected_types[0]:
                errors.append(f"Observation '{key}' msg_type inconsistent with kind '{kind}'")

        fields = spec.get("fields")
        if not fields:
            warnings.append(f"Observation '{key}' has no fields declared")

    for entry in bridge_entries:
        if not isinstance(entry, dict):
            continue
        ros_topic = str(entry.get("ros_topic_name") or "")
        if ros_topic and ros_topic not in obs_topics:
            warnings.append(f"Bridge topic not referenced in observations: {ros_topic}")

    for sensor_name in urdf_sensors:
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", sensor_name):
            warnings.append(f"Non-standard Gazebo sensor name: {sensor_name}")

    details["sensor_count"] = len(observations)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "details": details,
        "gz_model_name": gz_model,
        "robot_name": robot_name,
    }
