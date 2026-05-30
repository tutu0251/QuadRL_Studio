"""Build ros_gz_bridge parameter_bridge CLI arguments from bridge YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from generator.urdf_patch import patch_gz_world_in_topic


def load_bridge_doc(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("#"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    doc = yaml.safe_load(text) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid bridge YAML: {path}")
    return doc


def bridge_to_ros_gz_config(doc: dict[str, Any], world_name: str = "flat") -> list[dict[str, Any]]:
    """Build ros_gz_bridge config_file YAML (root list)."""
    entries: list[dict[str, Any]] = [
        {
            "ros_topic_name": "/clock",
            "gz_topic_name": "/clock",
            "ros_type_name": "rosgraph_msgs/msg/Clock",
            "gz_type_name": "gz.msgs.Clock",
            "direction": "GZ_TO_ROS",
        }
    ]
    for entry in doc.get("bridge") or []:
        gz_topic = patch_gz_world_in_topic(str(entry.get("gz_topic_name", "")), world_name)
        entries.append(
            {
                "ros_topic_name": entry.get("ros_topic_name"),
                "gz_topic_name": gz_topic,
                "ros_type_name": entry.get("ros_type_name"),
                "gz_type_name": entry.get("gz_type_name"),
                "direction": entry.get("direction", "GZ_TO_ROS"),
            }
        )
    return entries


def bridge_to_parameter_bridge_args(doc: dict[str, Any]) -> list[str]:
    """Convert bridge entries to parameter_bridge CLI arguments."""
    entries = doc.get("bridge") or []
    args: list[str] = ["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"]
    for entry in entries:
        ros_topic = entry.get("ros_topic_name")
        ros_type = entry.get("ros_type_name")
        gz_type = entry.get("gz_type_name")
        direction = entry.get("direction", "GZ_TO_ROS")
        gz_topic = entry.get("gz_topic_name")
        if not ros_topic or not ros_type or not gz_type:
            continue
        if direction == "GZ_TO_ROS":
            topic = gz_topic or ros_topic
            args.append(f"{topic}@{ros_type}[{gz_type}")
        else:
            topic = ros_topic
            args.append(f"{topic}@{ros_type}]{gz_type}")
    return args


def observation_topics(doc: dict[str, Any]) -> list[str]:
    obs = doc.get("observations") or {}
    topics: list[str] = []
    for spec in obs.values():
        if isinstance(spec, dict) and spec.get("topic"):
            topics.append(str(spec["topic"]))
    return topics
