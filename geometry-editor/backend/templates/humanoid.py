"""Humanoid robot template builders."""
from __future__ import annotations

from domain.models import Inertial, Joint, JointType, Link, PrimitiveShape, PrimitiveType, RobotModel, Vec3
from templates.common import (
    attach_leg_to_base,
    box_link,
    cylinder_leg_link,
    hip_cylinder_link,
    quadruped_stand_base_z,
    revolute_joint,
    sphere_foot,
)

_PELVIS_H = 0.08
_LEG_ATTACH_Z = -_PELVIS_H / 2


def template_humanoid_arm(prefix: str, side: float = 1.0) -> tuple[list[Link], list[Joint]]:
    upper_len, fore_len = 0.22, 0.2
    shoulder = hip_cylinder_link(f"{prefix}_shoulder", 0.02, 0.04, mass=0.3)
    shoulder.shapes[0].color = "#5588aa"
    upper = cylinder_leg_link(f"{prefix}_upper_arm", 0.015, upper_len, downward=False, mass=0.5)
    forearm = cylinder_leg_link(f"{prefix}_forearm", 0.012, fore_len, downward=False, mass=0.4)
    hand = sphere_foot(f"{prefix}_hand", 0.025)
    j1 = revolute_joint(f"{prefix}_shoulder_joint", shoulder.id, upper.id, Vec3(y=side))
    j2 = revolute_joint(f"{prefix}_elbow_joint", upper.id, forearm.id, Vec3(x=1))
    j3 = Joint(
        name=f"{prefix}_wrist_joint",
        parentLinkId=forearm.id,
        childLinkId=hand.id,
        type=JointType.FIXED,
    )
    upper.parentJointId = j1.id
    forearm.parentJointId = j2.id
    hand.parentJointId = j3.id
    j1.originPosition = Vec3(y=0.02 * side, z=0.02)
    j2.originPosition = Vec3(z=upper_len)
    j3.originPosition = Vec3(z=fore_len)
    return [shoulder, upper, forearm, hand], [j1, j2, j3]


def template_humanoid_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    thigh_len, shank_len, foot_r = 0.32, 0.30, 0.03
    hip = hip_cylinder_link(f"{prefix}_hip")
    thigh = cylinder_leg_link(f"{prefix}_thigh", 0.02, thigh_len, mass=1.2)
    shank = cylinder_leg_link(f"{prefix}_shank", 0.018, shank_len, mass=0.8)
    foot = sphere_foot(f"{prefix}_foot", foot_r)
    j1 = revolute_joint(f"{prefix}_hip_joint", hip.id, thigh.id, Vec3(x=1))
    j2 = revolute_joint(f"{prefix}_knee_joint", thigh.id, shank.id, Vec3(y=1))
    j3 = Joint(
        name=f"{prefix}_ankle_joint",
        parentLinkId=shank.id,
        childLinkId=foot.id,
        type=JointType.FIXED,
    )
    thigh.parentJointId = j1.id
    shank.parentJointId = j2.id
    foot.parentJointId = j3.id
    j1.originPosition = Vec3(z=-0.02)
    j2.originPosition = Vec3(z=-thigh_len)
    j3.originPosition = Vec3(z=-shank_len)
    return [hip, thigh, shank, foot], [j1, j2, j3]


def _attach_arm(model: RobotModel, parent: Link, prefix: str, offset: Vec3, side: float) -> None:
    links, joints = template_humanoid_arm(prefix, side)
    shoulder = links[0]
    for link in links:
        model.links.append(link)

    mount = Joint(
        name=f"{prefix}_mount_joint",
        parentLinkId=parent.id,
        childLinkId=shoulder.id,
        type=JointType.FIXED,
        originPosition=offset,
    )
    shoulder.parentJointId = mount.id
    model.joints.append(mount)

    for joint in joints:
        model.joints.append(joint)


def build_humanoid(name: str, label: str, include_arms: bool = True) -> RobotModel:
    model = RobotModel(name=name, metadata={"template": label})
    pelvis = box_link("pelvis", 0.18, 0.12, _PELVIS_H, "#666666", mass=8.0)
    torso = Link(
        name="torso",
        shapes=[
            PrimitiveShape(
                type=PrimitiveType.CYLINDER,
                dimensions=[0.11, 0.35],
                localPosition=Vec3(z=0.175),
                color="#777777",
            )
        ],
        inertial=Inertial(mass=12.0, ixx=0.45, iyy=0.45, izz=0.12),
    )
    head = sphere_foot("head", 0.09, mass=1.5)
    head.shapes[0].color = "#aaaaaa"

    leg_stand_z = quadruped_stand_base_z(_PELVIS_H, _LEG_ATTACH_Z, 0.02, 0.32, 0.30, 0.03)
    pelvis.frame.position.z = leg_stand_z

    torso_joint = Joint(
        name="torso_joint",
        parentLinkId=pelvis.id,
        childLinkId=torso.id,
        type=JointType.FIXED,
        originPosition=Vec3(z=_PELVIS_H / 2),
    )
    torso.parentJointId = torso_joint.id

    head_joint = Joint(
        name="head_joint",
        parentLinkId=torso.id,
        childLinkId=head.id,
        type=JointType.FIXED,
        originPosition=Vec3(z=0.35),
    )
    head.parentJointId = head_joint.id

    model.links.extend([pelvis, torso, head])
    model.joints.extend([torso_joint, head_joint])

    attach_leg_to_base(
        model, pelvis, "left_leg", Vec3(x=0.06, y=0.08, z=_LEG_ATTACH_Z), template_humanoid_leg
    )
    attach_leg_to_base(
        model, pelvis, "right_leg", Vec3(x=0.06, y=-0.08, z=_LEG_ATTACH_Z), template_humanoid_leg
    )

    if include_arms:
        _attach_arm(model, torso, "left_arm", Vec3(x=0.0, y=0.14, z=0.28), side=1.0)
        _attach_arm(model, torso, "right_arm", Vec3(x=0.0, y=-0.14, z=0.28), side=-1.0)

    return model


def build_humanoid_biped(name: str) -> RobotModel:
    return build_humanoid(name, "humanoid_biped", include_arms=False)
