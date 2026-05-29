"""ProfileA — position control auto-generation."""
from __future__ import annotations

import re

from domain.models import (
    DEFAULT_SIM_CONTROLLER,
    ControlModel,
    JointControlConfig,
    TrainingProfile,
    apply_fortress_gazebo_defaults,
    utc_now_iso,
)
from importer.urdf_importer import ImportedJoint

# Joint name segment order for quadruped / leg naming (hip before thigh before calf)
_SEGMENT_ORDER = (
    ("hip", 0),
    ("thigh", 1),
    ("calf", 2),
    ("knee", 2),
    ("ankle", 3),
    ("foot", 4),
    ("abad", 0),
    ("hfe", 1),
    ("kfe", 2),
)


def _joint_sort_key(name: str) -> tuple:
    lower = name.lower()
    leg_match = re.match(r"^([a-z]{2,3})_", lower)
    leg_prefix = leg_match.group(1) if leg_match else ""
    segment_rank = 99
    for token, rank in _SEGMENT_ORDER:
        if token in lower:
            segment_rank = min(segment_rank, rank)
    return (leg_prefix, segment_rank, lower)


def _effective_inertia(j: ImportedJoint) -> float:
    ax = abs(j.axis[0])
    ay = abs(j.axis[1])
    az = abs(j.axis[2])
    if ax >= ay and ax >= az:
        return j.child_ixx
    if ay >= ax and ay >= az:
        return j.child_iyy
    return j.child_izz


def _default_position(j: ImportedJoint, physics: dict | None) -> float:
    if physics and "defaultValue" in physics:
        return float(physics["defaultValue"])
    if j.type == "continuous":
        return 0.0
    return (j.lower_limit + j.upper_limit) / 2.0


def _compute_gains(j: ImportedJoint, default_pos: float) -> tuple[float, float]:
    if j.type == "continuous":
        joint_range = 6.28
    else:
        joint_range = max(j.upper_limit - j.lower_limit, 0.1)
    kp = max(10.0, 0.5 * j.effort / joint_range)
    i_eff = max(_effective_inertia(j) * j.child_mass, 1e-4)
    kd = max(0.1, 2.0 * (kp * i_eff) ** 0.5)
    _ = default_pos  # reserved for future pose-dependent tuning
    return round(kp, 4), round(kd, 4)


def build_joint_config(j: ImportedJoint, physics: dict | None) -> JointControlConfig:
    effort = j.effort
    velocity = j.velocity
    lower = j.lower_limit
    upper = j.upper_limit
    jtype = j.type
    child_name = j.child_link
    if physics:
        effort = float(physics.get("effort", effort))
        velocity = float(physics.get("velocity", velocity))
        lower = float(physics.get("lowerLimit", lower))
        upper = float(physics.get("upperLimit", upper))
        jtype = str(physics.get("type", jtype))
        child_name = str(physics.get("childLinkName", child_name))

    default_pos = _default_position(j, physics)
    kp, kd = _compute_gains(j, default_pos)

    return JointControlConfig(
        name=j.name,
        type=jtype,
        childLinkName=child_name,
        lowerLimit=lower,
        upperLimit=upper,
        effort=effort,
        velocity=velocity,
        commandInterface="position",
        stateInterfaces=["position", "velocity", "effort"],
        kp=kp,
        kd=kd,
        defaultPosition=default_pos,
        actionScale=1.0,
        enabled=True,
        profileParams={"profile": "ProfileA"},
    )


def apply_profile_a(
    model: ControlModel,
    imported: list[ImportedJoint],
    physics_by_joint: dict[str, dict],
) -> ControlModel:
    sorted_joints = sorted(imported, key=lambda x: _joint_sort_key(x.name))
    model.actuatedJoints = [
        build_joint_config(j, physics_by_joint.get(j.name)) for j in sorted_joints
    ]
    model.trainingProfile = TrainingProfile.PROFILE_A
    model.controllerType = DEFAULT_SIM_CONTROLLER
    apply_fortress_gazebo_defaults(model)
    model.metadata["generatedAt"] = utc_now_iso()
    model.metadata["profileVersion"] = "ProfileA-1"
    return model
