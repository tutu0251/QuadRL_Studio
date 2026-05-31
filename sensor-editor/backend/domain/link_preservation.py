"""Assert URDF link topology is unchanged by export/patch steps."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import NamedTuple


class LinkTopology(NamedTuple):
    link_names: tuple[str, ...]
    joints: tuple[tuple[str, str, str, str], ...]  # name, type, parent, child


def extract_link_topology(root: ET.Element) -> LinkTopology:
    links = tuple(
        sorted(
            name
            for link in root.findall("link")
            if (name := link.get("name"))
        )
    )
    joints: list[tuple[str, str, str, str]] = []
    for joint in root.findall("joint"):
        parent_el = joint.find("parent")
        child_el = joint.find("child")
        if parent_el is None or child_el is None:
            continue
        parent = parent_el.get("link") or ""
        child = child_el.get("link") or ""
        joints.append((joint.get("name") or "", joint.get("type") or "", parent, child))
    return LinkTopology(links, tuple(sorted(joints)))


def assert_link_topology_unchanged(before: ET.Element, after: ET.Element, *, step: str) -> None:
    before_topo = extract_link_topology(before)
    after_topo = extract_link_topology(after)
    if before_topo != after_topo:
        added_links = set(after_topo.link_names) - set(before_topo.link_names)
        removed_links = set(before_topo.link_names) - set(after_topo.link_names)
        raise ValueError(
            f"URDF link topology changed during {step}: "
            f"added_links={sorted(added_links)!r} removed_links={sorted(removed_links)!r}"
        )
