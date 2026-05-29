"""Bake per-link frame offsets into joints/shapes for URDF-compatible export."""
from __future__ import annotations

import copy

from domain.math_utils import quat_multiply, quat_rotate_vec, vec3_add
from domain.models import Frame, Quat, RobotModel, Vec3


def _is_identity_frame(frame: Frame, eps: float = 1e-9) -> bool:
    p = frame.position
    if abs(p.x) > eps or abs(p.y) > eps or abs(p.z) > eps:
        return False
    q = frame.rotation
    return (
        abs(q.x) < eps
        and abs(q.y) < eps
        and abs(q.z) < eps
        and abs(q.w - 1.0) < eps
    )


def compose_pose(pos: Vec3, rot: Quat, child_pos: Vec3, child_rot: Quat) -> tuple[Vec3, Quat]:
    rotated = quat_rotate_vec(rot, child_pos)
    return vec3_add(pos, rotated), quat_multiply(rot, child_rot)


def bake_link_frames(model: RobotModel) -> RobotModel:
    """Return a copy with link.frame baked into shapes and incoming joint origins."""
    baked = copy.deepcopy(model)
    link_by_id = {l.id: l for l in baked.links}

    for link in baked.links:
        if _is_identity_frame(link.frame):
            continue
        fp, fr = link.frame.position, link.frame.rotation

        for shape in link.shapes:
            shape.localPosition, shape.localRotation = compose_pose(
                fp, fr, shape.localPosition, shape.localRotation
            )

        # Joint origins are expressed in the parent link frame (see editor FK).
        for joint in baked.joints:
            if joint.parentLinkId != link.id:
                continue
            joint.originPosition, joint.originRotation = compose_pose(
                fp, fr, joint.originPosition, joint.originRotation
            )

        link.frame = Frame()

    return baked
