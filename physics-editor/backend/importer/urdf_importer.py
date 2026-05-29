"""Import geometry-exported URDF (geo_*) into physics RobotModel."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

from domain.models import (
    CollisionFriction,
    Frame,
    Inertial,
    Joint,
    JointDynamics,
    JointType,
    Link,
    PrimitiveShape,
    PrimitiveType,
    Quat,
    RobotModel,
    Vec3,
    new_id,
)
from domain.inertia_math import parse_rpy_attr


def _parse_xyz(s: str | None) -> Vec3:
    if not s:
        return Vec3()
    p = [float(x) for x in s.split()]
    return Vec3(x=p[0], y=p[1], z=p[2]) if len(p) >= 3 else Vec3()


def _parse_origin(el: ET.Element | None) -> tuple[Vec3, Quat]:
    if el is None:
        return Vec3(), Quat(w=1.0)
    xyz = _parse_xyz(el.get("xyz"))
    rpy = el.get("rpy", "0 0 0")
    return xyz, parse_rpy_attr(rpy)


def _geom_type(tag: str) -> PrimitiveType | None:
    m = {"box": PrimitiveType.BOX, "cylinder": PrimitiveType.CYLINDER, "sphere": PrimitiveType.SPHERE}
    return m.get(tag)


def _parse_geometry(geom_el: ET.Element | None) -> PrimitiveShape | None:
    if geom_el is None:
        return None
    inner = list(geom_el)
    if not inner:
        return None
    g = inner[0]
    ptype = _geom_type(g.tag)
    if ptype is None:
        return None
    dims: list[float] = []
    if ptype == PrimitiveType.BOX:
        dims = [float(x) for x in g.get("size", "0.1 0.1 0.1").split()]
    elif ptype == PrimitiveType.CYLINDER:
        dims = [float(g.get("radius", "0.05")), float(g.get("length", "0.1"))]
    elif ptype == PrimitiveType.SPHERE:
        dims = [float(g.get("radius", "0.05"))]
    return PrimitiveShape(type=ptype, dimensions=dims, color="#808080")


def _parse_inertial(in_el: ET.Element | None) -> Inertial:
    if in_el is None:
        return Inertial()
    origin = in_el.find("origin")
    com, com_rot = _parse_origin(origin)
    mass_el = in_el.find("mass")
    mass = float(mass_el.get("value", "1.0")) if mass_el is not None else 1.0
    inertia_el = in_el.find("inertia")
    if inertia_el is None:
        return Inertial(mass=mass, com=com, comRotation=com_rot)
    return Inertial(
        mass=mass,
        com=com,
        comRotation=com_rot,
        ixx=float(inertia_el.get("ixx", "0.01")),
        ixy=float(inertia_el.get("ixy", "0")),
        ixz=float(inertia_el.get("ixz", "0")),
        iyy=float(inertia_el.get("iyy", "0.01")),
        iyz=float(inertia_el.get("iyz", "0")),
        izz=float(inertia_el.get("izz", "0.01")),
    )


def _parse_friction_from_gazebo(robot: ET.Element, link_name: str) -> CollisionFriction:
    fr = CollisionFriction()
    for gz in robot.findall("gazebo"):
        if gz.get("reference") != link_name:
            continue
        mu = gz.find("mu1")
        mu2 = gz.find("mu2")
        kp = gz.find("kp")
        kd = gz.find("kd")
        if mu is not None and mu.text:
            fr.mu = float(mu.text)
            fr.useMu = True
        if mu2 is not None and mu2.text:
            fr.mu2 = float(mu2.text)
            fr.useMu2 = True
        if kp is not None and kp.text:
            fr.kp = float(kp.text)
            fr.useKp = True
        if kd is not None and kd.text:
            fr.kd = float(kd.text)
            fr.useKd = True
        fr.enabled = fr.useMu or fr.useMu2 or fr.useKp or fr.useKd
        return fr
    return fr


def _is_foot_name(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ("foot", "toe", "pad", "sole"))


def import_urdf(path: Path, project_name: str) -> RobotModel:
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "robot":
        raise ValueError("Not a URDF robot file")

    link_els = {el.get("name", f"link_{i}"): el for i, el in enumerate(root.findall("link"))}
    joint_els = list(root.findall("joint"))

    # Build parent/child from joints
    child_of: dict[str, str] = {}  # child link -> joint name
    joint_parent: dict[str, str] = {}
    joint_child: dict[str, str] = {}
    joint_types: dict[str, JointType] = {}

    for jel in joint_els:
        jname = jel.get("name", str(uuid4()))
        parent = jel.find("parent")
        child = jel.find("child")
        if parent is None or child is None:
            continue
        plink, clink = parent.get("link"), child.get("link")
        if not plink or not clink:
            continue
        child_of[clink] = jname
        joint_parent[jname] = plink
        joint_child[jname] = clink
        jt = jel.get("type", "fixed")
        joint_types[jname] = {
            "fixed": JointType.FIXED,
            "revolute": JointType.REVOLUTE,
            "continuous": JointType.CONTINUOUS,
            "prismatic": JointType.PRISMATIC,
        }.get(jt, JointType.FIXED)

    link_ids: dict[str, str] = {}
    links: list[Link] = []
    joints: list[Joint] = []

    for lname, lel in link_els.items():
        lid = new_id()
        link_ids[lname] = lid
        shapes: list[PrimitiveShape] = []
        for vis in lel.findall("visual"):
            geom = vis.find("geometry")
            shape = _parse_geometry(geom)
            if shape is None:
                continue
            pos, rot = _parse_origin(vis.find("origin"))
            shape.localPosition = pos
            shape.localRotation = rot
            mat = vis.find("material")
            if mat is not None:
                color = mat.find("color")
                if color is not None:
                    rgba = color.get("rgba", "")
                    parts = rgba.split()
                    if len(parts) >= 3:
                        r, g, b = [int(float(x) * 255) for x in parts[:3]]
                        shape.color = f"#{r:02x}{g:02x}{b:02x}"
            shapes.append(shape)

        inertial = _parse_inertial(lel.find("inertial"))
        friction = _parse_friction_from_gazebo(root, lname)
        links.append(
            Link(
                id=lid,
                name=lname,
                shapes=shapes,
                frame=Frame(),
                inertial=inertial,
                friction=friction,
                isFoot=_is_foot_name(lname),
            )
        )

    link_by_name = {l.name: l for l in links}

    for jel in joint_els:
        jname = jel.get("name", new_id())
        parent = jel.find("parent")
        child = jel.find("child")
        if parent is None or child is None:
            continue
        plink, clink = parent.get("link"), child.get("link")
        if plink not in link_by_name or clink not in link_by_name:
            continue
        parent_link = link_by_name[plink]
        child_link = link_by_name[clink]
        child_link.parentJointId = jname

        opos, orot = _parse_origin(jel.find("origin"))
        axis_el = jel.find("axis")
        axis = Vec3(x=0, y=0, z=1)
        if axis_el is not None:
            axis = _parse_xyz(axis_el.get("xyz"))
        jtype = joint_types.get(jname, JointType.FIXED)
        dyn = JointDynamics()
        dyn_el = jel.find("dynamics")
        if dyn_el is not None:
            dyn.damping = float(dyn_el.get("damping", "0"))
            dyn.friction = float(dyn_el.get("friction", "0"))
        limit_el = jel.find("limit")
        lower, upper = -3.14, 3.14
        if limit_el is not None:
            lower = float(limit_el.get("lower", str(lower)))
            upper = float(limit_el.get("upper", str(upper)))
            dyn.effort = float(limit_el.get("effort", str(dyn.effort)))
            dyn.velocity = float(limit_el.get("velocity", str(dyn.velocity)))

        joints.append(
            Joint(
                id=new_id(),
                name=jname,
                parentLinkId=parent_link.id,
                childLinkId=child_link.id,
                type=jtype,
                originPosition=opos,
                originRotation=orot,
                axis=axis,
                lowerLimit=lower,
                upperLimit=upper,
                dynamics=dyn,
            )
        )

    return RobotModel(
        name=project_name,
        links=links,
        joints=joints,
        metadata={"importedFrom": str(path)},
    )
