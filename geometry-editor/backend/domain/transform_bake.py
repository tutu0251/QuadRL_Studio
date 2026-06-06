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
    """Return a copy with link.frame baked into shapes and incoming joint origins.

    Root links are a special case. A non-root link's frame offset is an internal
    placement that must be folded into its geometry (and into outgoing joint
    origins) so the URDF — where the link is positioned by its parent joint —
    stays correct. A root link has no parent joint: its frame *position* is the
    spawn / world reference (the editor authors it at the standing height), not an
    offset to absorb. Folding that position into the root's own shapes would push
    base_link's origin off its trunk and down to the model origin, yielding a
    misleading (often negative) grounded spawn_z. So for root links we drop the
    frame position — keeping the origin on the link's own geometry (the trunk) —
    and bake only the rotation. Grounding then reports spawn_z as the trunk-centre
    standing height.
    """
    baked = copy.deepcopy(model)
    child_ids = {j.childLinkId for j in baked.joints}

    for link in baked.links:
        if _is_identity_frame(link.frame):
            continue
        fp, fr = link.frame.position, link.frame.rotation
        if link.id not in child_ids:
            # Root link: frame position is the spawn reference, not a geometry offset.
            fp = Vec3()

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
