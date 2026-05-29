"""Export RobotModel to URDF."""
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

from domain.math_utils import quat_to_rpy, vec3_norm
from domain.models import JointType, RobotModel
from domain.transform_bake import bake_link_frames


def _hex_to_rgba(color_hex: str) -> str:
    if color_hex.startswith("#") and len(color_hex) >= 7:
        r = int(color_hex[1:3], 16) / 255.0
        g = int(color_hex[3:5], 16) / 255.0
        b = int(color_hex[5:7], 16) / 255.0
        return f"{r} {g} {b} 1"
    return "0.5 0.5 0.5 1"


def _geometry(shape, geom_parent: Element) -> None:
    """URDF geometry uses attributes on primitive tags, not SDF-style child elements."""
    t = shape.type.value
    dims = shape.dimensions
    if t == "box":
        g = SubElement(geom_parent, "box")
        g.set("size", f"{dims[0]} {dims[1]} {dims[2]}")
    elif t == "cylinder":
        g = SubElement(geom_parent, "cylinder")
        length = dims[1] if len(dims) > 1 else dims[0]
        g.set("radius", str(dims[0]))
        g.set("length", str(length))
    elif t == "sphere":
        g = SubElement(geom_parent, "sphere")
        g.set("radius", str(dims[0]))
    elif t == "capsule":
        g = SubElement(geom_parent, "cylinder")
        g.set("radius", str(dims[0]))
        g.set("length", str(dims[1] if len(dims) > 1 else 0.1))


def _visual_collision(link_el: Element, shape, tag: str) -> None:
    vc = SubElement(link_el, tag)
    origin = SubElement(vc, "origin")
    p, r = shape.localPosition, shape.localRotation
    roll, pitch, yaw = quat_to_rpy(r)
    origin.set("xyz", f"{p.x} {p.y} {p.z}")
    origin.set("rpy", f"{roll} {pitch} {yaw}")
    geom = SubElement(vc, "geometry")
    _geometry(shape, geom)
    if tag == "visual":
        mat = SubElement(vc, "material", name=f"{shape.id}_mat")
        SubElement(mat, "color").set("rgba", _hex_to_rgba(shape.color))


def export_urdf(model: RobotModel, output_path: Path) -> Path:
    model = bake_link_frames(model)
    robot = Element("robot", name=model.name)

    for link in model.links:
        link_el = SubElement(robot, "link", name=link.name)
        inertial = SubElement(link_el, "inertial")
        origin_in = SubElement(inertial, "origin")
        com = link.inertial.com
        origin_in.set("xyz", f"{com.x} {com.y} {com.z}")
        origin_in.set("rpy", "0 0 0")
        SubElement(inertial, "mass").set("value", str(link.inertial.mass))
        inertia = SubElement(inertial, "inertia")
        inertia.set("ixx", str(link.inertial.ixx))
        inertia.set("iyy", str(link.inertial.iyy))
        inertia.set("izz", str(link.inertial.izz))
        inertia.set("ixy", "0")
        inertia.set("ixz", "0")
        inertia.set("iyz", "0")
        for shape in link.shapes:
            _visual_collision(link_el, shape, "visual")
            _visual_collision(link_el, shape, "collision")

    joint_type_map = {
        JointType.FIXED: "fixed",
        JointType.REVOLUTE: "revolute",
        JointType.CONTINUOUS: "continuous",
        JointType.PRISMATIC: "prismatic",
    }

    link_by_id = {l.id: l for l in model.links}
    for joint in model.joints:
        parent = link_by_id.get(joint.parentLinkId)
        child = link_by_id.get(joint.childLinkId)
        if not parent or not child:
            continue
        jel = SubElement(robot, "joint", name=joint.name, type=joint_type_map.get(joint.type, "fixed"))
        SubElement(jel, "parent", link=parent.name)
        SubElement(jel, "child", link=child.name)
        origin = SubElement(jel, "origin")
        op, orot = joint.originPosition, joint.originRotation
        roll, pitch, yaw = quat_to_rpy(orot)
        origin.set("xyz", f"{op.x} {op.y} {op.z}")
        origin.set("rpy", f"{roll} {pitch} {yaw}")
        if joint.type != JointType.FIXED:
            axis_el = SubElement(jel, "axis")
            a = joint.axis
            n = vec3_norm(a) or 1.0
            axis_el.set("xyz", f"{a.x / n} {a.y / n} {a.z / n}")
        if joint.type == JointType.REVOLUTE:
            limit = SubElement(jel, "limit")
            limit.set("lower", str(joint.lowerLimit))
            limit.set("upper", str(joint.upperLimit))
            limit.set("effort", "100")
            limit.set("velocity", "10")
        elif joint.type == JointType.PRISMATIC:
            limit = SubElement(jel, "limit")
            limit.set("lower", str(joint.lowerLimit))
            limit.set("upper", str(joint.upperLimit))
            limit.set("effort", "100")
            limit.set("velocity", "1")

    indent(robot, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(robot).write(output_path, encoding="unicode", xml_declaration=True)
    return output_path


def urdf_to_string(model: RobotModel) -> str:
    import io
    robot = Element("robot", name=model.name)
    for link in model.links:
        SubElement(robot, "link", name=link.name)
    link_by_id = {l.id: l for l in model.links}
    for joint in model.joints:
        parent = link_by_id.get(joint.parentLinkId)
        child = link_by_id.get(joint.childLinkId)
        if parent and child:
            jel = SubElement(robot, "joint", name=joint.name)
            SubElement(jel, "parent", link=parent.name)
            SubElement(jel, "child", link=child.name)
    buf = io.StringIO()
    ElementTree(robot).write(buf, encoding="unicode")
    return buf.getvalue()
