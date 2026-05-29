"""Import phy_* URDF into actuated joint records for control generation."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ACTUATED_TYPES = frozenset({"revolute", "prismatic", "continuous"})


@dataclass
class ImportedJoint:
    name: str
    type: str
    child_link: str
    parent_link: str
    lower_limit: float
    upper_limit: float
    effort: float
    velocity: float
    default_value: float = 0.0
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    child_mass: float = 1.0
    child_ixx: float = 0.01
    child_iyy: float = 0.01
    child_izz: float = 0.01


def _parse_xyz(s: str | None) -> tuple[float, float, float]:
    if not s:
        return (0.0, 0.0, 0.0)
    p = [float(x) for x in s.split()]
    if len(p) < 3:
        return (0.0, 0.0, 0.0)
    return (p[0], p[1], p[2])


def _link_inertial(link_el: ET.Element | None) -> tuple[float, float, float, float]:
    if link_el is None:
        return (1.0, 0.01, 0.01, 0.01)
    in_el = link_el.find("inertial")
    if in_el is None:
        return (1.0, 0.01, 0.01, 0.01)
    mass_el = in_el.find("mass")
    mass = float(mass_el.get("value", "1.0")) if mass_el is not None else 1.0
    inertia_el = in_el.find("inertia")
    if inertia_el is None:
        return (mass, 0.01, 0.01, 0.01)
    return (
        mass,
        float(inertia_el.get("ixx", "0.01")),
        float(inertia_el.get("iyy", "0.01")),
        float(inertia_el.get("izz", "0.01")),
    )


def import_actuated_joints(path: Path) -> tuple[str, list[ImportedJoint]]:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "robot":
        raise ValueError("Not a URDF robot file")
    robot_name = root.get("name", "robot")

    link_els = {el.get("name", ""): el for el in root.findall("link")}
    joints: list[ImportedJoint] = []

    for jel in root.findall("joint"):
        jtype = jel.get("type", "fixed")
        if jtype not in ACTUATED_TYPES:
            continue
        jname = jel.get("name", "")
        parent = jel.find("parent")
        child = jel.find("child")
        if parent is None or child is None:
            continue
        plink = parent.get("link", "")
        clink = child.get("link", "")
        lower, upper = -3.14, 3.14
        effort, velocity = 100.0, 10.0
        limit_el = jel.find("limit")
        if limit_el is not None:
            if jtype != "continuous":
                lower = float(limit_el.get("lower", str(lower)))
                upper = float(limit_el.get("upper", str(upper)))
            effort = float(limit_el.get("effort", str(effort)))
            velocity = float(limit_el.get("velocity", str(velocity)))
        axis_el = jel.find("axis")
        axis = _parse_xyz(axis_el.get("xyz") if axis_el is not None else None)
        mass, ixx, iyy, izz = _link_inertial(link_els.get(clink))

        joints.append(
            ImportedJoint(
                name=jname,
                type=jtype,
                child_link=clink,
                parent_link=plink,
                lower_limit=lower,
                upper_limit=upper,
                effort=effort,
                velocity=velocity,
                axis=axis,
                child_mass=mass,
                child_ixx=ixx,
                child_iyy=iyy,
                child_izz=izz,
            )
        )

    return robot_name, joints
