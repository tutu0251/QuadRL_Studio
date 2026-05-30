"""Patch exported URDF for installable ROS packages."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import yaml


def patch_controllers_parameters(urdf_text: str, controllers_path: str) -> str:
    """Rewrite Gazebo/ros2_control plugin <parameters> to an absolute or basename path."""
    try:
        root = ET.fromstring(urdf_text)
    except ET.ParseError:
        return _patch_controllers_regex(urdf_text, controllers_path)

    changed = False
    for plugin in root.iter("plugin"):
        fn = plugin.get("filename", "")
        name = plugin.get("name", "")
        if "gz_ros2_control" not in fn and "GazeboSimROS2ControlPlugin" not in name:
            continue
        params = plugin.find("parameters")
        if params is None:
            params = ET.SubElement(plugin, "parameters")
        params.text = controllers_path
        changed = True

    if not changed:
        for gz in root.findall("gazebo"):
            plugin = gz.find("plugin")
            if plugin is None:
                continue
            fn = plugin.get("filename", "")
            name = plugin.get("name", "")
            if "gz_ros2_control" in fn or "GazeboSimROS2ControlPlugin" in name:
                params = plugin.find("parameters")
                if params is not None:
                    params.text = controllers_path
                else:
                    params = ET.SubElement(plugin, "parameters")
                    params.text = controllers_path
                changed = True

    if changed:
        ET.indent(root)
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
    return urdf_text


def _patch_controllers_regex(urdf_text: str, controllers_basename: str) -> str:
    pattern = re.compile(
        r"(<parameters>)(.*?)(</parameters>)",
        re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{controllers_basename}{match.group(3)}"

    return pattern.sub(repl, urdf_text, count=1)


def _is_truthy(text: str | None) -> bool:
    return (text or "").strip().lower() in ("1", "true", "yes")


def _find_or_create_gazebo(root: ET.Element, reference: str) -> ET.Element:
    for gz in root.findall("gazebo"):
        if gz.get("reference") == reference:
            return gz
    return ET.SubElement(root, "gazebo", reference=reference)


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


def _preserved_fixed_joint_children(urdf_root: ET.Element) -> set[str]:
    """Child links whose fixed joint is marked preserveFixedJoint in URDF."""
    joint_by_name = {j.get("name"): j for j in urdf_root.findall("joint") if j.get("name")}
    preserved: set[str] = set()
    for gz in urdf_root.findall("gazebo"):
        ref = gz.get("reference")
        if not ref or ref not in joint_by_name:
            continue
        pfj = gz.find("preserveFixedJoint")
        if pfj is None or not _is_truthy(pfj.text):
            continue
        joint = joint_by_name[ref]
        if joint.get("type") != "fixed":
            continue
        child = joint.find("child")
        if child is not None and child.get("link"):
            preserved.add(child.get("link"))
    return preserved


def gazebo_effective_link(
    link: str,
    fixed_parents: dict[str, str],
    preserved_children: set[str] | None = None,
) -> str:
    """Resolve URDF link name to the link Gazebo uses after merging fixed joints."""
    if preserved_children and link in preserved_children:
        return link
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
        urdf_root = ET.fromstring(urdf_text)
        fixed_parents = _fixed_joint_parent_map(urdf_root)
        preserved = _preserved_fixed_joint_children(urdf_root)
    except ET.ParseError:
        fixed_parents = {}
        preserved = set()

    for entry in doc.get("bridge") or []:
        if not isinstance(entry, dict):
            continue
        parent_link = entry.get("parent_link")
        gz_topic = str(entry.get("gz_topic_name") or "")
        if not parent_link or not gz_topic:
            continue
        effective = gazebo_effective_link(str(parent_link), fixed_parents, preserved)
        link_match = re.search(r"/link/([^/]+)/", gz_topic)
        if link_match and link_match.group(1) != effective:
            entry["gz_topic_name"] = gz_topic.replace(
                f"/link/{link_match.group(1)}/",
                f"/link/{effective}/",
                1,
            )

    dumped = yaml.dump(doc, default_flow_style=False, sort_keys=False)
    if header:
        return f"{header.rstrip()}\n{dumped}"
    return dumped


def _is_foot_link(link: str) -> bool:
    lower = link.lower()
    return "foot" in lower or lower.endswith("_foot")


def _collision_sdf_name(link: str, collision: ET.Element, index: int) -> str:
    name = collision.get("name")
    if name:
        return f"{name}_collision"
    if index == 0:
        return f"{link}_collision"
    return f"{link}_collision_{index + 1}"


def _preserve_foot_fixed_joints(root: ET.Element) -> None:
    """Keep foot links separate in SDF so contact sensors stay on the foot link."""
    for joint in root.findall("joint"):
        if joint.get("type") != "fixed":
            continue
        child_el = joint.find("child")
        if child_el is None:
            continue
        child_link = child_el.get("link") or ""
        if not _is_foot_link(child_link):
            continue
        joint_name = joint.get("name")
        if not joint_name:
            continue
        gz = _find_or_create_gazebo(root, joint_name)
        pfj = gz.find("preserveFixedJoint")
        if pfj is None:
            pfj = ET.SubElement(gz, "preserveFixedJoint")
        pfj.text = "true"


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

    _preserve_foot_fixed_joints(root)

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
