"""Forward kinematics for COM visualization."""
from __future__ import annotations

from domain.math_utils import quat_multiply, quat_rotate_vec, vec3_add
from domain.models import Quat, RobotModel, Vec3


class WorldTransform:
    __slots__ = ("position", "rotation")

    def __init__(self, position: Vec3, rotation: Quat):
        self.position = position
        self.rotation = rotation


def compute_world_transforms(model: RobotModel) -> dict[str, WorldTransform]:
    link_by_id = {l.id: l for l in model.links}
    child_ids = {j.childLinkId for j in model.joints}
    roots = [l for l in model.links if l.id not in child_ids]
    out: dict[str, WorldTransform] = {}

    def compose(parent: WorldTransform, pos: Vec3, rot: Quat) -> WorldTransform:
        rotated = quat_rotate_vec(parent.rotation, pos)
        p = vec3_add(parent.position, rotated)
        r = quat_multiply(parent.rotation, rot)
        return WorldTransform(p, r)

    def walk_link(link_id: str, parent_tf: WorldTransform) -> None:
        link = link_by_id[link_id]
        local_tf = compose(parent_tf, link.frame.position, link.frame.rotation)
        out[link_id] = local_tf
        for j in model.joints:
            if j.parentLinkId != link_id:
                continue
            joint_tf = compose(local_tf, j.originPosition, j.originRotation)
            walk_link(j.childLinkId, joint_tf)

    identity = WorldTransform(Vec3(), Quat(w=1.0))
    for root in roots:
        walk_link(root.id, identity)

    return out


def whole_robot_com(model: RobotModel) -> Vec3 | None:
    tfs = compute_world_transforms(model)
    total_m = 0.0
    com = Vec3()
    for link in model.links:
        m = link.inertial.mass
        if m <= 0:
            continue
        tf = tfs.get(link.id)
        if not tf:
            continue
        local = link.inertial.com
        world = vec3_add(tf.position, quat_rotate_vec(tf.rotation, local))
        com.x += m * world.x
        com.y += m * world.y
        com.z += m * world.z
        total_m += m
    if total_m < 1e-9:
        return None
    return Vec3(x=com.x / total_m, y=com.y / total_m, z=com.z / total_m)
