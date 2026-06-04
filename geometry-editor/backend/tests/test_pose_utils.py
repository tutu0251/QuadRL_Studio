"""Tests for default pose utilities."""
from __future__ import annotations

import pytest

from domain.models import Joint, JointType, Link, Pose, PrimitiveShape, PrimitiveType, RobotModel
from domain.pose_utils import (
    DEFAULT_POSE_NAME,
    compute_grounded_spawn_z_for_model,
    ensure_default_pose,
    export_default_pose_yaml,
    suggest_stand_joint_value,
)


def test_ensure_default_pose_creates_stand_pose():
    j = Joint(name="fl_thigh_joint", type=JointType.REVOLUTE, parentLinkId="a", childLinkId="b")
    model = RobotModel(name="bot", joints=[j])
    ensure_default_pose(model, init_stand=True)
    assert model.poses
    assert model.defaultPoseId == model.poses[0].id
    assert model.poses[0].name == DEFAULT_POSE_NAME


def test_suggest_stand_joint_value_thigh():
    j = Joint(name="fl_thigh_joint", type=JointType.REVOLUTE, lowerLimit=-1.57, upperLimit=1.57)
    assert suggest_stand_joint_value(j) > 0.5


def test_export_default_pose_yaml_uses_joint_names():
    j = Joint(name="fl_hip_joint", type=JointType.REVOLUTE, defaultValue=0.1)
    model = RobotModel(name="bot", joints=[j])
    ensure_default_pose(model)
    doc = export_default_pose_yaml(model)
    assert "fl_hip_joint" in doc["joints"]
    grounded = compute_grounded_spawn_z_for_model(model)
    assert doc["spawn"]["z"] == grounded
    assert doc["height_policy"]["target_body_height"] == grounded
    assert doc["height_policy"]["fall_base_height_threshold"] < grounded


def test_compute_grounded_spawn_z_for_simple_leg():
    base = Link(
        name="base_link",
        shapes=[PrimitiveShape(type=PrimitiveType.BOX, dimensions=[0.2, 0.1, 0.05])],
    )
    foot = Link(
        name="foot",
        shapes=[PrimitiveShape(type=PrimitiveType.SPHERE, dimensions=[0.02])],
    )
    from domain.models import Vec3

    hip = Joint(
        name="hip",
        type=JointType.FIXED,
        parentLinkId=base.id,
        childLinkId=foot.id,
        originPosition=Vec3(z=-0.4),
    )
    foot.parentJointId = hip.id
    model = RobotModel(name="bot", links=[base, foot], joints=[hip])
    ensure_default_pose(model)
    assert compute_grounded_spawn_z_for_model(model) == pytest.approx(0.42, abs=1e-3)
