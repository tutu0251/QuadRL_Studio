"""Import link names and robot name from ctrl_* ros2_control URDF."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def parse_ctrl_urdf(path: Path) -> tuple[str, list[str]]:
    tree = ET.parse(path)
    root = tree.getroot()
    robot_name = root.get("name") or "robot"
    links: list[str] = []
    for link in root.findall("link"):
        name = link.get("name")
        if name:
            links.append(name)
    return robot_name, links
