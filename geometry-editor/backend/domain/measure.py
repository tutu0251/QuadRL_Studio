"""Forward kinematics and measurement tools."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from domain.math_utils import (
    axis_angle_quat,
    quat_multiply,
    quat_rotate_vec,
    vec3_add,
    vec3_norm,
    vec3_sub,
    angle_between,
)
from domain.models import JointType, MeasurementResult, Quat, RobotModel, Vec3


@dataclass
class WorldTransform:
    position: Vec3
    rotation: Quat


def _joint_motion_quat(joint_type: JointType, axis: Vec3, value: float) -> Quat:
    if joint_type == JointType.FIXED:
        return Quat(w=1.0)
    if joint_type == JointType.PRISMATIC:
        return Quat(w=1.0)
    return axis_angle_quat(axis, value)


def _joint_motion_offset(joint_type: JointType, axis: Vec3, value: float) -> Vec3:
    if joint_type == JointType.PRISMATIC:
        n = vec3_norm(axis) or 1.0
        return Vec3(x=axis.x / n * value, y=axis.y / n * value, z=axis.z / n * value)
    return Vec3()


def compute_world_transforms(model: RobotModel) -> dict[str, WorldTransform]:
    """Compute world-frame transform for each link at default joint values."""
    link_by_id = {l.id: l for l in model.links}
    joint_by_child: dict[str, list] = {}
    for j in model.joints:
        joint_by_child.setdefault(j.childLinkId, []).append(j)

    children = {j.childLinkId for j in model.joints}
    roots = [l for l in model.links if l.id not in children]

    transforms: dict[str, WorldTransform] = {}

    def compose(parent: WorldTransform, pos: Vec3, rot: Quat) -> WorldTransform:
        rotated = quat_rotate_vec(parent.rotation, pos)
        return WorldTransform(
            position=vec3_add(parent.position, rotated),
            rotation=quat_multiply(parent.rotation, rot),
        )

    def visit(link_id: str, parent_tf: WorldTransform) -> None:
        link = link_by_id[link_id]
        local_tf = compose(parent_tf, link.frame.position, link.frame.rotation)
        transforms[link_id] = local_tf

        for joint in model.joints:
            if joint.parentLinkId != link_id:
                continue
            child = link_by_id.get(joint.childLinkId)
            if not child:
                continue
            j_rot = quat_multiply(joint.originRotation, _joint_motion_quat(joint.type, joint.axis, joint.defaultValue))
            j_offset = vec3_add(joint.originPosition, _joint_motion_offset(joint.type, joint.axis, joint.defaultValue))
            joint_tf = compose(local_tf, j_offset, j_rot)
            visit(child.id, joint_tf)

    for root in roots:
        root_tf = WorldTransform(position=root.frame.position, rotation=root.frame.rotation)
        transforms[root.id] = root_tf
        for joint in model.joints:
            if joint.parentLinkId != root.id:
                continue
            child = link_by_id.get(joint.childLinkId)
            if not child:
                continue
            j_rot = quat_multiply(joint.originRotation, _joint_motion_quat(joint.type, joint.axis, joint.defaultValue))
            j_offset = vec3_add(joint.originPosition, _joint_motion_offset(joint.type, joint.axis, joint.defaultValue))
            joint_tf = compose(root_tf, j_offset, j_rot)
            visit(child.id, joint_tf)

    return transforms


def measure_distance(model: RobotModel, link_a_id: str, link_b_id: str) -> Optional[MeasurementResult]:
    tf = compute_world_transforms(model)
    if link_a_id not in tf or link_b_id not in tf:
        return None
    pa, pb = tf[link_a_id].position, tf[link_b_id].position
    d = vec3_norm(vec3_sub(pa, pb))
    return MeasurementResult(tool="distance", value=d, unit="m", label="Point-to-point", points=[pa, pb])


def measure_height(model: RobotModel, link_id: str, ground_z: float = 0.0) -> Optional[MeasurementResult]:
    tf = compute_world_transforms(model)
    if link_id not in tf:
        return None
    p = tf[link_id].position
    h = p.z - ground_z
    return MeasurementResult(
        tool="height",
        value=h,
        unit="m",
        label="Height from ground",
        points=[Vec3(x=p.x, y=p.y, z=ground_z), p],
    )


def measure_link_length(model: RobotModel, child_link_id: str) -> Optional[MeasurementResult]:
    joint = next((j for j in model.joints if j.childLinkId == child_link_id), None)
    if not joint:
        return None
    tf = compute_world_transforms(model)
    if joint.parentLinkId not in tf or child_link_id not in tf:
        return None
    pa = tf[joint.parentLinkId].position
    pb = tf[child_link_id].position
    d = vec3_norm(vec3_sub(pb, pa))
    return MeasurementResult(tool="link_length", value=d, unit="m", label="Parent to child link", points=[pa, pb])


def measure_angle(model: RobotModel, joint_a_id: str, joint_b_id: str) -> Optional[MeasurementResult]:
    ja = next((j for j in model.joints if j.id == joint_a_id), None)
    jb = next((j for j in model.joints if j.id == joint_b_id), None)
    if not ja or not jb:
        return None
    angle = angle_between(ja.axis, jb.axis)
    return MeasurementResult(tool="angle", value=math.degrees(angle), unit="deg", label="Joint axis angle")


def measure_leg_reach(model: RobotModel, hip_link_id: str, foot_link_id: str) -> Optional[MeasurementResult]:
    return measure_distance(model, hip_link_id, foot_link_id)
