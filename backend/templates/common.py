"""Shared primitive helpers for templates."""
from __future__ import annotations

from domain.models import Inertial, Joint, JointType, Link, PrimitiveShape, PrimitiveType, RobotModel, Vec3


def _inertial(mass: float, radius: float = 0.05, length: float = 0.1) -> Inertial:
    """Rough diagonal inertia for template links (mass != 1.0 placeholder)."""
    i = mass * (radius**2 + length**2 / 12.0)
    return Inertial(mass=mass, ixx=i, iyy=i, izz=mass * radius**2 * 0.5)


def box_link(
    name: str,
    sx: float,
    sy: float,
    sz: float,
    color: str = "#666666",
    *,
    mass: float = 2.0,
) -> Link:
    return Link(
        name=name,
        shapes=[PrimitiveShape(type=PrimitiveType.BOX, dimensions=[sx, sy, sz], color=color)],
        inertial=_inertial(mass, radius=max(sx, sy, sz) / 2, length=sz),
    )


def hip_cylinder_link(
    name: str,
    radius: float = 0.025,
    length: float = 0.04,
    *,
    mass: float = 0.35,
) -> Link:
    return Link(
        name=name,
        shapes=[
            PrimitiveShape(
                type=PrimitiveType.CYLINDER,
                dimensions=[radius, length],
                color="#5577aa",
            )
        ],
        inertial=_inertial(mass, radius=radius, length=length),
    )


def cylinder_leg_link(
    name: str,
    radius: float,
    length: float,
    *,
    downward: bool = True,
    mass: float = 0.75,
    color: str = "#4488cc",
) -> Link:
    local_z = -length / 2 if downward else length / 2
    return Link(
        name=name,
        shapes=[
            PrimitiveShape(
                type=PrimitiveType.CYLINDER,
                dimensions=[radius, length],
                localPosition=Vec3(z=local_z),
                color=color,
            )
        ],
        inertial=_inertial(mass, radius=radius, length=length),
    )


def capsule_leg_link(name: str, radius: float, length: float, *, downward: bool = True) -> Link:
    """Capsule leg (prefer cylinder_leg_link for SDF export without fallback warnings)."""
    local_z = -length / 2 if downward else length / 2
    return Link(
        name=name,
        shapes=[
            PrimitiveShape(
                type=PrimitiveType.CAPSULE,
                dimensions=[radius, length],
                localPosition=Vec3(z=local_z),
                color="#4488cc",
            )
        ],
        inertial=_inertial(0.75, radius=radius, length=length),
    )


def sphere_foot(name: str, r: float, *, mass: float = 0.04) -> Link:
    return Link(
        name=name,
        shapes=[PrimitiveShape(type=PrimitiveType.SPHERE, dimensions=[r], color="#333333")],
        inertial=_inertial(mass, radius=r, length=r),
    )


def quadruped_stand_base_z(
    body_height: float,
    hip_attach_z: float,
    hip_half: float,
    thigh_len: float,
    calf_len: float,
    foot_radius: float,
) -> float:
    """Base link center height so feet touch z=0 at default joint angles."""
    leg_drop = hip_half + thigh_len + calf_len + foot_radius
    return -hip_attach_z + leg_drop


def revolute_joint(name: str, parent_id: str, child_id: str, axis: Vec3) -> Joint:
    return Joint(
        name=name,
        parentLinkId=parent_id,
        childLinkId=child_id,
        type=JointType.REVOLUTE,
        axis=axis,
        lowerLimit=-1.57,
        upperLimit=1.57,
    )


def attach_leg_to_base(model: RobotModel, base: Link, prefix: str, offset: Vec3, leg_factory) -> None:
    """Attach leg so base_link → hip → thigh → … (hip is never skipped)."""
    links, joints = leg_factory(prefix)
    hip = links[0]
    for link in links:
        model.links.append(link)

    mount = Joint(
        name=f"{prefix}_attach_joint",
        parentLinkId=base.id,
        childLinkId=hip.id,
        type=JointType.FIXED,
        originPosition=offset,
    )
    hip.parentJointId = mount.id
    model.joints.append(mount)

    for joint in joints:
        model.joints.append(joint)


def attach_12dof_leg_to_base(model: RobotModel, base: Link, prefix: str, offset: Vec3, leg_factory) -> None:
    """Attach leg: base_link → hip_joint → hip_link → thigh_joint → … → foot_link."""
    links, joints = leg_factory(prefix)
    hip_link = links[0]
    for link in links:
        model.links.append(link)

    hip_joint = revolute_joint(f"{prefix}_hip_joint", base.id, hip_link.id, Vec3(x=1))
    hip_joint.originPosition = offset
    hip_link.parentJointId = hip_joint.id
    model.joints.append(hip_joint)

    for joint in joints:
        model.joints.append(joint)
