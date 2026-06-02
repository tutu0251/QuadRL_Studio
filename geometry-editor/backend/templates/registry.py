"""Insertable geometry templates (primitive-only)."""
from __future__ import annotations

from domain.models import (
    Joint,
    JointType,
    Link,
    PrimitiveShape,
    PrimitiveType,
    Quat,
    RobotModel,
    Vec3,
    new_id,
)
from templates.common import (
    attach_12dof_leg_to_base,
    attach_leg_to_base,
    box_link,
    cylinder_leg_link,
    hip_cylinder_link,
    quadruped_stand_base_z,
    revolute_joint,
    sphere_foot,
)
from templates.humanoid import (
    build_humanoid,
    build_humanoid_biped,
    template_humanoid_arm,
    template_humanoid_leg,
)


def _box_link(name: str, sx: float, sy: float, sz: float, color: str = "#666666", **kwargs) -> Link:
    return box_link(name, sx, sy, sz, color, **kwargs)


def _cylinder_leg_link(name: str, radius: float, length: float, **kwargs) -> Link:
    return cylinder_leg_link(name, radius, length, **kwargs)


def _hip_cylinder_link(name: str, radius: float = 0.025, length: float = 0.04, **kwargs) -> Link:
    return hip_cylinder_link(name, radius, length, **kwargs)


def _sphere_foot(name: str, r: float) -> Link:
    return sphere_foot(name, r)


def _revolute_joint(name: str, parent_id: str, child_id: str, axis: Vec3) -> Joint:
    return revolute_joint(name, parent_id, child_id, axis)


def _attach_leg_to_base(model: RobotModel, base: Link, prefix: str, offset: Vec3, leg_factory) -> None:
    attach_leg_to_base(model, base, prefix, offset, leg_factory)


_BODY_H = 0.08
_BODY_HALF_X = 0.2
_BODY_HALF_Y = 0.1
_HIP_RADIUS = 0.025
_HIP_HALF_LEN = 0.02
# Mount hips outside body collision (template hip cylinder r=0.025, len=0.04).
_HIP_MOUNT_Z = -_BODY_H / 2 - _HIP_HALF_LEN
_HIP_MOUNT_X = _BODY_HALF_X + _HIP_RADIUS
_HIP_MOUNT_Y = _BODY_HALF_Y + _HIP_RADIUS


def template_body_box() -> list[Link]:
    """Body box: x×y footprint, z is height (robot stands on XY ground plane)."""
    return [_box_link("base_link", 0.4, 0.2, _BODY_H, "#888888", mass=4.5)]


def template_single_leg_module(prefix: str = "leg") -> tuple[list[Link], list[Joint]]:
    thigh_len, shank_len, foot_r = 0.15, 0.14, 0.025
    hip = _hip_cylinder_link(f"{prefix}_hip")
    thigh = _cylinder_leg_link(f"{prefix}_thigh", 0.02, thigh_len, mass=0.85)
    shank = _cylinder_leg_link(f"{prefix}_shank", 0.018, shank_len, mass=0.55)
    foot = _sphere_foot(f"{prefix}_foot", foot_r)
    j1 = _revolute_joint(f"{prefix}_hip_joint", hip.id, thigh.id, Vec3(x=1))
    j2 = _revolute_joint(f"{prefix}_knee_joint", thigh.id, shank.id, Vec3(y=1))
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


def template_quadruped_12dof_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    """base_link → hip_joint → hip_link → thigh_joint → thigh_link → knee_joint → calf_link → ankle_joint → foot_link."""
    thigh_len, calf_len, foot_r = 0.12, 0.11, 0.025
    hip_link = _hip_cylinder_link(f"{prefix}_hip_link")
    thigh_link = _cylinder_leg_link(f"{prefix}_thigh_link", 0.02, thigh_len, mass=0.85)
    calf_link = _cylinder_leg_link(f"{prefix}_calf_link", 0.018, calf_len, mass=0.55)
    foot_link = _sphere_foot(f"{prefix}_foot_link", foot_r)
    thigh_joint = _revolute_joint(f"{prefix}_thigh_joint", hip_link.id, thigh_link.id, Vec3(y=1))
    knee_joint = _revolute_joint(f"{prefix}_knee_joint", thigh_link.id, calf_link.id, Vec3(y=1))
    ankle_joint = Joint(
        name=f"{prefix}_ankle_joint",
        parentLinkId=calf_link.id,
        childLinkId=foot_link.id,
        type=JointType.FIXED,
    )
    thigh_link.parentJointId = thigh_joint.id
    calf_link.parentJointId = knee_joint.id
    foot_link.parentJointId = ankle_joint.id
    thigh_joint.originPosition = Vec3(z=-0.02)
    knee_joint.originPosition = Vec3(z=-thigh_len)
    ankle_joint.originPosition = Vec3(z=-calf_len)
    return [hip_link, thigh_link, calf_link, foot_link], [thigh_joint, knee_joint, ankle_joint]


def template_quadruped_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    return template_quadruped_12dof_leg(prefix)


def template_mit_cheetah_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    """4-DOF serial leg: abduct (X) → hip yaw (Y) → knee (X) → fixed foot."""
    thigh_len, shank_len, foot_r = 0.18, 0.17, 0.02
    hip = _hip_cylinder_link(f"{prefix}_abduct", 0.02, 0.04, mass=0.4)
    hip_yaw = _hip_cylinder_link(f"{prefix}_hip_yaw", 0.015, 0.03, mass=0.25)
    thigh = _cylinder_leg_link(f"{prefix}_thigh", 0.015, thigh_len, mass=0.9)
    shank = _cylinder_leg_link(f"{prefix}_shank", 0.012, shank_len, mass=0.6)
    foot = _sphere_foot(f"{prefix}_foot", foot_r)
    j0 = _revolute_joint(f"{prefix}_abduct_joint", hip.id, hip_yaw.id, Vec3(x=1))
    j1 = _revolute_joint(f"{prefix}_hip_joint", hip_yaw.id, thigh.id, Vec3(y=1))
    j2 = _revolute_joint(f"{prefix}_knee_joint", thigh.id, shank.id, Vec3(y=1))
    j3 = Joint(name=f"{prefix}_foot_fixed", parentLinkId=shank.id, childLinkId=foot.id, type=JointType.FIXED)
    hip_yaw.parentJointId = j0.id
    thigh.parentJointId = j1.id
    shank.parentJointId = j2.id
    foot.parentJointId = j3.id
    j1.originPosition = Vec3(z=-0.02)
    j2.originPosition = Vec3(z=-0.18)
    j3.originPosition = Vec3(z=-0.17)
    return [hip, hip_yaw, thigh, shank, foot], [j0, j1, j2, j3]


def template_unitree_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    return template_mit_cheetah_leg(prefix)


def template_mini_dog_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    thigh_len, foot_r = 0.08, 0.015
    hip = _hip_cylinder_link(f"{prefix}_hip", 0.015, 0.03, mass=0.2)
    thigh = _cylinder_leg_link(f"{prefix}_thigh", 0.01, thigh_len, mass=0.35)
    foot = _sphere_foot(f"{prefix}_foot", foot_r)
    j1 = _revolute_joint(f"{prefix}_hip_joint", hip.id, thigh.id, Vec3(x=1))
    j2 = Joint(name=f"{prefix}_foot_joint", parentLinkId=thigh.id, childLinkId=foot.id, type=JointType.FIXED)
    thigh.parentJointId = j1.id
    foot.parentJointId = j2.id
    j1.originPosition = Vec3(z=-0.015)
    j2.originPosition = Vec3(z=-thigh_len)
    return [hip, thigh, foot], [j1, j2]


def template_humanoid_limb(prefix: str) -> tuple[list[Link], list[Joint]]:
    return template_single_leg_module(prefix)


def template_capsule_leg(prefix: str) -> tuple[list[Link], list[Joint]]:
    seg_len = 0.2
    thigh = _cylinder_leg_link(f"{prefix}_capsule", 0.025, seg_len, mass=0.5)
    foot = _sphere_foot(f"{prefix}_foot", 0.02)
    j = Joint(name=f"{prefix}_joint", parentLinkId=thigh.id, childLinkId=foot.id, type=JointType.FIXED)
    foot.parentJointId = j.id
    j.originPosition = Vec3(z=-seg_len)
    return [thigh, foot], [j]


def template_sphere_foot_only(prefix: str) -> list[Link]:
    return [_sphere_foot(f"{prefix}_foot", 0.03)]


def build_quadruped(
    name: str,
    leg_factory,
    dof_label: str,
    *,
    use_12dof_attach: bool = False,
    stand_base_z: float | None = None,
) -> RobotModel:
    model = RobotModel(name=name, metadata={"template": dof_label})
    bodies = template_body_box()
    base = bodies[0]
    if stand_base_z is not None:
        base.frame.position.z = stand_base_z
    model.links.extend(bodies)
    offsets = [
        Vec3(x=_HIP_MOUNT_X, y=_HIP_MOUNT_Y, z=_HIP_MOUNT_Z),
        Vec3(x=_HIP_MOUNT_X, y=-_HIP_MOUNT_Y, z=_HIP_MOUNT_Z),
        Vec3(x=-_HIP_MOUNT_X, y=_HIP_MOUNT_Y, z=_HIP_MOUNT_Z),
        Vec3(x=-_HIP_MOUNT_X, y=-_HIP_MOUNT_Y, z=_HIP_MOUNT_Z),
    ]
    prefixes = ["fl", "fr", "rl", "rr"]
    attach = attach_12dof_leg_to_base if use_12dof_attach else _attach_leg_to_base
    for prefix, off in zip(prefixes, offsets):
        attach(model, base, prefix, off, leg_factory)
    return model


def _stand_12dof() -> float:
    return quadruped_stand_base_z(_BODY_H, _HIP_MOUNT_Z, 0.02, 0.12, 0.11, 0.025)


def _stand_mit() -> float:
    return quadruped_stand_base_z(_BODY_H, _HIP_MOUNT_Z, 0.02, 0.18, 0.17, 0.02)


def _stand_mini() -> float:
    return quadruped_stand_base_z(_BODY_H, _HIP_MOUNT_Z, 0.015, 0.08, 0.0, 0.015)


def _leg_only_model(name: str, factory, *, stand_z: float | None = None) -> RobotModel:
    links, joints = factory("leg")
    if stand_z is not None:
        links[0].frame.position.z = stand_z
    return RobotModel(name=name, links=links, joints=joints)


TEMPLATE_BUILDERS = {
    "body_box": lambda: RobotModel(name="body_box", links=template_body_box()),
    "single_leg_module": lambda: _leg_only_model("leg", template_single_leg_module, stand_z=0.335),
    "quadruped_leg": lambda: _leg_only_model("leg", template_quadruped_leg, stand_z=_stand_12dof() + _HIP_MOUNT_Z),
    "mit_cheetah_leg": lambda: _leg_only_model("cheetah_leg", template_mit_cheetah_leg, stand_z=0.43),
    "unitree_leg": lambda: _leg_only_model("unitree_leg", template_unitree_leg, stand_z=0.43),
    "mini_dog_leg": lambda: _leg_only_model("mini_leg", template_mini_dog_leg, stand_z=_stand_mini() + _HIP_MOUNT_Z),
    "humanoid_limb": lambda: _leg_only_model("limb", template_humanoid_limb, stand_z=0.335),
    "humanoid_arm": lambda: _leg_only_model("arm", template_humanoid_arm, stand_z=0.0),
    "humanoid_leg": lambda: _leg_only_model("leg", template_humanoid_leg, stand_z=0.67),
    "capsule_leg": lambda: _leg_only_model("cap_leg", template_capsule_leg, stand_z=0.22),
    "sphere_foot": lambda: RobotModel(name="sphere_foot", links=template_sphere_foot_only("foot")),
    "quadruped_12dof": lambda: build_quadruped(
        "quadruped_12dof",
        template_quadruped_12dof_leg,
        "12-DOF",
        use_12dof_attach=True,
        stand_base_z=_stand_12dof(),
    ),
    "quadruped_8dof": lambda: build_quadruped(
        "quadruped_8dof", template_mini_dog_leg, "8-DOF", stand_base_z=_stand_mini()
    ),
    "quadruped": lambda: build_quadruped(
        "quadruped",
        template_quadruped_12dof_leg,
        "standard",
        use_12dof_attach=True,
        stand_base_z=_stand_12dof(),
    ),
    "mit_cheetah": lambda: build_quadruped(
        "mit_cheetah", template_mit_cheetah_leg, "MIT Cheetah", stand_base_z=_stand_mit()
    ),
    "unitree": lambda: build_quadruped("unitree", template_unitree_leg, "Unitree", stand_base_z=_stand_mit()),
    "mini_dog": lambda: build_quadruped("mini_dog", template_mini_dog_leg, "mini dog", stand_base_z=_stand_mini()),
    "humanoid": lambda: build_humanoid("humanoid", "humanoid_full", include_arms=True),
    "humanoid_biped": lambda: build_humanoid_biped("humanoid_biped"),
}

TEMPLATE_DISPLAY_NAMES = {
    "quadruped_12dof": "12-DOF Quadruped",
    "quadruped_8dof": "8-DOF Quadruped",
    "humanoid": "Humanoid (Full Body)",
    "humanoid_biped": "Humanoid Biped",
    "mit_cheetah": "MIT Cheetah Quadruped",
    "unitree": "Unitree Quadruped",
    "mini_dog": "Mini Dog Quadruped",
}

TEMPLATE_META = {
    "body_box": {"jointCount": 0, "category": "part", "description": "Single body box"},
    "single_leg_module": {"jointCount": 3, "category": "leg", "description": "3-DOF leg module"},
    "quadruped_leg": {
        "jointCount": 3,
        "category": "leg",
        "description": "Hip/thigh/knee chain: hip_link → thigh_link → calf_link → foot_link",
    },
    "mit_cheetah_leg": {"jointCount": 4, "category": "leg", "description": "MIT Cheetah style leg"},
    "unitree_leg": {"jointCount": 4, "category": "leg", "description": "Unitree style leg"},
    "mini_dog_leg": {"jointCount": 2, "category": "leg", "description": "Mini dog 2-DOF leg"},
    "humanoid_limb": {"jointCount": 3, "category": "leg", "description": "Generic humanoid limb"},
    "humanoid_arm": {"jointCount": 3, "category": "arm", "description": "Humanoid arm chain"},
    "humanoid_leg": {"jointCount": 3, "category": "leg", "description": "Humanoid biped leg"},
    "capsule_leg": {"jointCount": 1, "category": "leg", "description": "Single capsule leg"},
    "sphere_foot": {"jointCount": 0, "category": "part", "description": "Sphere foot only"},
    "quadruped_12dof": {
        "jointCount": 12,
        "category": "robot",
        "description": "12-DOF quadruped: base_link → hip/thigh/knee joints per leg",
    },
    "quadruped_8dof": {"jointCount": 8, "category": "robot", "description": "8-DOF quadruped with 4×2-DOF legs"},
    "quadruped": {"jointCount": 12, "category": "robot", "description": "Standard quadruped robot"},
    "mit_cheetah": {"jointCount": 16, "category": "robot", "description": "MIT Cheetah quadruped (16-DOF)"},
    "unitree": {"jointCount": 16, "category": "robot", "description": "Unitree-style quadruped (16-DOF)"},
    "mini_dog": {"jointCount": 8, "category": "robot", "description": "Small quadruped (8-DOF)"},
    "humanoid": {"jointCount": 14, "category": "robot", "description": "Full humanoid: torso, head, 2 arms, 2 legs"},
    "humanoid_biped": {"jointCount": 8, "category": "robot", "description": "Biped humanoid: torso, head, 2 legs (no arms)"},
}


def list_templates() -> list[dict]:
    return [
        {
            "id": k,
            "name": TEMPLATE_DISPLAY_NAMES.get(k, k.replace("_", " ").title()),
            **TEMPLATE_META.get(k, {"jointCount": 0, "category": "other", "description": ""}),
        }
        for k in TEMPLATE_BUILDERS
    ]


def insert_template(model: RobotModel, template_id: str) -> RobotModel:
    if template_id not in TEMPLATE_BUILDERS:
        raise ValueError(f"Unknown template: {template_id}")
    fragment = TEMPLATE_BUILDERS[template_id]()
    meta = TEMPLATE_META.get(template_id, {})
    if meta.get("category") == "robot":
        model.links = []
        model.joints = []
        model.poses = []
    id_map: dict[str, str] = {}
    for link in fragment.links:
        old = link.id
        link.id = new_id()
        id_map[old] = link.id
    for joint in fragment.joints:
        old = joint.id
        joint.id = new_id()
        if joint.parentLinkId in id_map:
            joint.parentLinkId = id_map[joint.parentLinkId]
        if joint.childLinkId in id_map:
            joint.childLinkId = id_map[joint.childLinkId]
        id_map[old] = joint.id
    for link in fragment.links:
        if link.parentJointId and link.parentJointId in id_map:
            link.parentJointId = id_map[link.parentJointId]
        if any(l.name == link.name for l in model.links):
            raise ValueError(f"Template would duplicate link name: {link.name}")
        model.links.append(link)
    for joint in fragment.joints:
        if any(j.name == joint.name for j in model.joints):
            raise ValueError(f"Template would duplicate joint name: {joint.name}")
        model.joints.append(joint)
    if template_id not in model.templates:
        model.templates.append(template_id)
    from domain.pose_utils import ensure_default_pose

    meta = TEMPLATE_META.get(template_id, {})
    if meta.get("category") == "robot":
        base = next((l for l in model.links if l.name == "base_link"), None)
        if base is not None:
            model.metadata["standSpawnZ"] = float(base.frame.position.z)
        ensure_default_pose(model, init_stand=True)
    else:
        ensure_default_pose(model)
    return model
