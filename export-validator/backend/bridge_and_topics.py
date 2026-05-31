"""Log parsing and topic helpers shared by runtime validators."""
from __future__ import annotations

import re
import shlex
from pathlib import Path
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
CONTROLLER_READY_MARKERS = (
    "Configured and activated joint_state_broadcaster",
    "Activating controller 'joint_state_broadcaster'",
)
BRIDGE_READY_MARKERS = (
    "ros_gz_bridge",
    "parameter_bridge",
    "Passing to a list of bridges",
)
TOPIC_TIMEOUT_IMU_S = 18.0
TOPIC_TIMEOUT_CONTACT_S = 22.0
TOPIC_TIMEOUT_LIDAR_S = 25.0
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def load_observations_doc(text: str) -> dict[str, Any]:
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return yaml.safe_load(text) or {}


def read_launch_log(log_path: Path) -> str:
    if not log_path.is_file():
        return ""
    return _ANSI_ESCAPE_RE.sub("", log_path.read_text(errors="replace"))


def topic_timeout(kind: str) -> float:
    if kind == "imu":
        return TOPIC_TIMEOUT_IMU_S
    if kind == "lidar":
        return TOPIC_TIMEOUT_LIDAR_S
    return TOPIC_TIMEOUT_CONTACT_S


def topic_publishes(topic: str, setup: Path, timeout_s: float, env: dict[str, str]) -> tuple[bool, str]:
    from ev_ros_env import bash_ros_cmd

    quoted = shlex.quote(topic)
    script = f"ros2 topic echo {quoted} --once --spin-time 12 --qos-reliability reliable"
    proc = bash_ros_cmd(script, setup=setup, timeout=timeout_s, env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and out.strip() and "---" in out:
        return True, out.strip().splitlines()[0][:200]
    if "average rate" in out:
        return True, out.strip().splitlines()[0][:200]
    return False, out.strip()[-300:] if out.strip() else "no messages"


def parse_ros_topic_list(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if line.strip().startswith("/")}


def observation_topics(obs_doc: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return (key, topic, kind) tuples from observations YAML."""
    items: list[tuple[str, str, str]] = []
    for key, spec in (obs_doc.get("observations") or {}).items():
        if not isinstance(spec, dict):
            continue
        topic = str(spec.get("topic", "")).strip()
        if not topic:
            continue
        kind = str(spec.get("kind", "contact"))
        items.append((str(key), topic, kind))
    return items


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
