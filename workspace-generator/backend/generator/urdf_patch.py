"""Patch exported URDF for installable ROS packages."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import yaml


def patch_controllers_parameters(urdf_text: str, controllers_basename: str) -> str:
    """Rewrite Gazebo plugin <parameters> to a basename in config/."""
    try:
        root = ET.fromstring(urdf_text)
    except ET.ParseError:
        return _patch_controllers_regex(urdf_text, controllers_basename)

    for gz in root.findall("gazebo"):
        plugin = gz.find("plugin")
        if plugin is None:
            continue
        fn = plugin.get("filename", "")
        name = plugin.get("name", "")
        if "gz_ros2_control" in fn or "GazeboSimROS2ControlPlugin" in name:
            params = plugin.find("parameters")
            if params is not None:
                params.text = controllers_basename
            else:
                params = ET.SubElement(plugin, "parameters")
                params.text = controllers_basename

    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _patch_controllers_regex(urdf_text: str, controllers_basename: str) -> str:
    pattern = re.compile(
        r"(<parameters>)(.*?)(</parameters>)",
        re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{controllers_basename}{match.group(3)}"

    return pattern.sub(repl, urdf_text, count=1)


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


def gazebo_effective_link(link: str, fixed_parents: dict[str, str]) -> str:
    """Resolve URDF link name to the link Gazebo uses after merging fixed joints."""
    current = link
    seen: set[str] = set()
    while current in fixed_parents and current not in seen:
        seen.add(current)
        current = fixed_parents[current]
    return current


def patch_gz_world_in_topic(gz_topic: str, world_name: str = "flat") -> str:
    """Replace placeholder world segments (/world/empty/ or /world/default/) in a GZ topic."""
    for placeholder in ("empty", "default"):
        gz_topic = gz_topic.replace(f"/world/{placeholder}/", f"/world/{world_name}/")
    if gz_topic.endswith("/contacts"):
        gz_topic = gz_topic[:-1]
    return gz_topic


def patch_bridge_world(bridge_text: str, world_name: str = "flat") -> str:
    """Replace placeholder world segments in bridge YAML."""
    for placeholder in ("empty", "default"):
        bridge_text = bridge_text.replace(f"/world/{placeholder}/", f"/world/{world_name}/")
    return bridge_text


def patch_bridge_yaml(bridge_text: str, urdf_text: str, world_name: str = "flat") -> str:
    """Patch bridge YAML for sim world name and Gazebo fixed-joint link merging."""
    header = ""
    body = bridge_text
    if body.startswith("#"):
        header, body = body.split("\n", 1)

    text = patch_bridge_world(body, world_name)
    doc: dict[str, Any] = yaml.safe_load(text) or {}
    if not isinstance(doc, dict):
        return patch_bridge_world(bridge_text, world_name)

    try:
        fixed_parents = _fixed_joint_parent_map(ET.fromstring(urdf_text))
    except ET.ParseError:
        fixed_parents = {}

    for entry in doc.get("bridge") or []:
        if not isinstance(entry, dict):
            continue
        parent_link = entry.get("parent_link")
        gz_topic = str(entry.get("gz_topic_name") or "")
        if not parent_link or not gz_topic:
            continue
        effective = gazebo_effective_link(str(parent_link), fixed_parents)
        if effective == parent_link:
            continue
        old_segment = f"/link/{parent_link}/"
        new_segment = f"/link/{effective}/"
        if old_segment in gz_topic:
            entry["gz_topic_name"] = gz_topic.replace(old_segment, new_segment)

    dumped = yaml.dump(doc, default_flow_style=False, sort_keys=False)
    if header:
        return f"{header.rstrip()}\n{dumped}"
    return dumped


def _collision_sdf_name(link: str, collision: ET.Element, index: int) -> str:
    name = collision.get("name")
    if name:
        return name
    if index == 0:
        return f"{link}_collision"
    return f"{link}_collision_{index + 1}"


def gazebo_contact_collision_name(
    urdf_root: ET.Element,
    parent_link: str,
    collision_name: str | None = None,
) -> str:
    """Resolve contact collision target for Gazebo URDF spawn."""
    collisions: list[tuple[int, ET.Element]] = []
    for link_el in urdf_root.findall("link"):
        if link_el.get("name") != parent_link:
            continue
        collisions = [(i, col) for i, col in enumerate(link_el.findall("collision"))]
        break

    if not collisions:
        return collision_name or "collision"

    chosen_idx = 0
    chosen_col = collisions[0][1]
    if collision_name and collision_name != "collision":
        for idx, col in collisions:
            if col.get("name") == collision_name:
                chosen_idx = idx
                chosen_col = col
                break

    return _collision_sdf_name(parent_link, chosen_col, chosen_idx)


def patch_contact_sensors(urdf_text: str) -> str:
    """Fix contact sensor collision names for Gazebo URDF spawn."""
    try:
        root = ET.fromstring(urdf_text)
    except ET.ParseError:
        return urdf_text

    for gz in root.findall("gazebo"):
        ref = gz.get("reference")
        if not ref:
            continue
        for sensor in gz.findall("sensor"):
            if sensor.get("type") != "contact":
                continue
            contact = sensor.find("contact")
            if contact is None:
                continue
            col = contact.find("collision")
            if col is None:
                continue
            requested = (col.text or "").strip() or None
            col.text = gazebo_contact_collision_name(root, ref, requested)

    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
